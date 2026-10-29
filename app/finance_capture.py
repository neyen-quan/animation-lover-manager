"""Inline natural-language input and compact review, with no mandatory form."""
import copy
import tempfile
import uuid
import wave
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from .finance import KINDS, usd, totals, validate
from .finance_ai import extract, proposals
from .theme import SURFACE, FG, LINE, MUTED
from .widgets import WrapBar

class FinanceCapture(ttk.Frame):
    def __init__(self, view):
        super().__init__(view,padding=(4,8))
        self.view=view;self.app=view.app;self.ledger=view.ledger
        self.columnconfigure(0,weight=1);self.rowconfigure(1,weight=1)
        self.paths=[];self.pending=[];self.snapshot=None;self.stream=None;self.chunks=[];self.timer=None
        self.hint=tk.StringVar(value='Automático')
        header=WrapBar(self);header.grid(row=0,column=0,sticky='ew',pady=(0,6))
        header.add(ttk.Label(header,text='Contame qué pasó',font=('Segoe UI',13,'bold')))
        header.add(ttk.Combobox(header,textvariable=self.hint,values=['Automático']+KINDS[:4]+['Insight'],state='readonly',width=13))
        header.add(ttk.Button(header,text='Volver al tablero',command=view.leave_capture))
        self.box=tk.Text(self,height=4,wrap='word',bg=SURFACE,fg=FG,insertbackground=FG,
                         relief='flat',highlightthickness=1,highlightbackground=LINE,padx=12,pady=10,font=('Segoe UI',11))
        self.box.grid(row=1,column=0,sticky='nsew')
        self.box.insert('1.0',self.ledger.store.setting('finance_draft') or '')
        self.box.bind('<<Modified>>',self.changed);self.hint.trace_add('write',self.invalidate)
        self.preview=tk.Text(self,height=4,wrap='word',bg=SURFACE,fg=FG,relief='flat',padx=12,pady=10,font=('Segoe UI',11))
        self.preview.tag_configure('title',font=('Segoe UI',12,'bold'),foreground='#b5bfff')
        self.preview.tag_configure('muted',foreground=MUTED)
        self.status=ttk.Label(self,text='Mandá un audio, escribí o pegá un comprobante. La IA completa los datos.',wraplength=650,foreground=MUTED)
        self.status.grid(row=2,column=0,sticky='ew',pady=(6,2))
        self.files_label=ttk.Label(self,foreground=MUTED,wraplength=650);self.files_label.grid(row=3,column=0,sticky='ew')
        tools=WrapBar(self);tools.grid(row=4,column=0,sticky='ew',pady=3)
        for title,cmd in [('Adjuntar',self.attach),('Pegar captura',self.paste),('Quitar adjuntos',self.clear_files),('Grabar',self.record),('Parar y transcribir',lambda:self.stop(False)),('Parar e interpretar',lambda:self.stop(True))]:
            tools.add(ttk.Button(tools,text=title,command=cmd))
        actions=WrapBar(self);actions.grid(row=5,column=0,sticky='ew')
        self.interpret_button=actions.add(ttk.Button(actions,text='Interpretar',style='Accent.TButton',command=self.process))
        self.save_button=actions.add(ttk.Button(actions,text='Confirmar registro',style='Accent.TButton',state='disabled',command=self.commit))
        self.correct_button=actions.add(ttk.Button(actions,text='Corregir con mensaje',command=self.correct))
        self.bind('<Configure>',lambda e:self.status.configure(wraplength=max(180,e.width-12)))
        self.show_files()
        for bar in (header,tools,actions):
            for child in bar.children_list:
                if isinstance(child,ttk.Button):child.configure(style='Finance.Accent.TButton' if 'Accent.' in str(child.cget('style')) else 'Finance.TButton')

    def start(self,hint=None):
        if not self.app.busy and self.hint.get()!=(hint or 'Automático'):
            self.correct();self.hint.set(hint or 'Automático')
        self.box.focus_set()

    def changed(self,event=None):
        if self.box.edit_modified():
            self.ledger.store.setting('finance_draft',self.box.get('1.0','end').strip())
            self.box.edit_modified(False)
            self.invalidate()

    def invalidate(self,*_):
        self.pending=[];self.snapshot=None
        self.save_button.configure(state='disabled')

    def show_files(self):
        self.files_label.configure(text=('Adjuntos: '+', '.join(Path(p).name for p in self.paths)) if self.paths else 'Los comprobantes quedan guardados con el registro.')

    def correct(self):
        if self.app.busy or self.stream:return
        self.preview.grid_remove();self.box.grid();self.invalidate();self.box.focus_set()
        self.status.configure(text='Agregá la corrección con tus palabras y volvé a interpretar.')

    def attach(self):
        if self.app.busy or self.stream:return
        added=filedialog.askopenfilenames(parent=self.app,title='Adjuntar audio o comprobante')
        if added:self.correct();self.paths.extend(added);self.show_files()

    def paste(self):
        if self.app.busy or self.stream:return
        try:self.paths.append(self.view.clipboard_image());self.correct();self.show_files()
        except Exception as e:messagebox.showerror('Pegar captura',str(e),parent=self.app)

    def clear_files(self):
        if self.app.busy or self.stream:return
        self.correct();self.paths.clear();self.show_files()

    def record(self):
        if self.app.busy or self.app.recording:return
        self.correct()
        try:
            import sounddevice as sd
            self.chunks=[]
            self.stream=sd.RawInputStream(samplerate=16000,channels=1,dtype='int16',callback=lambda data,frames,time,status:self.chunks.append(bytes(data)))
            self.stream.start();self.app.recording=self.stream
            self.timer=self.after(3600000,lambda:self.stop(False))
            self.status.configure(text='Grabando… Tocá Parar y transcribir o Parar e interpretar.')
        except Exception as e:
            if self.stream:self.stream.close()
            self.stream=None;self.app.recording=None;messagebox.showerror('Micrófono',str(e),parent=self.app)

    def stop(self,interpret=False):
        if not self.stream:return
        if self.timer:self.after_cancel(self.timer);self.timer=None
        self.stream.stop();self.stream.close();self.stream=None;self.app.recording=None
        path=Path(tempfile.gettempdir())/(str(uuid.uuid4())+'.wav');self.app.tempfiles.append(str(path))
        with wave.open(str(path),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b''.join(self.chunks))
        self.chunks=[]
        from .ai import transcribe
        self.status.configure(text='Transcribiendo el audio…')
        def done(text):
            self.box.insert('end','\n'+text);self.changed()
            self.status.configure(text='Audio transcripto. Podés interpretar o corregir el texto.')
            if interpret:self.process()
        self.app.run(lambda:transcribe(path),done,on_error=self.failed)

    def failed(self):self.status.configure(text='No se pudo interpretar. Tu mensaje y los adjuntos siguen disponibles.')

    def process(self):
        if self.app.busy or self.app.recording:return
        self.changed();self.invalidate()
        text=self.box.get('1.0','end').strip();paths=list(self.paths)
        if not text and not paths:return
        hint=None if self.hint.get()=='Automático' else self.hint.get()
        people=list(self.ledger.people());categories=list(self.ledger.categories());aliases=self.ledger.store.setting('aliases') or {}
        balances=totals(self.ledger.rows())['debt'];model=self.ledger.store.setting('model')
        project=self.app.projects.context(self.app.project_id);providers=self.ledger.providers();personal=bool(self.ledger.store.setting('personal'))
        self.status.configure(text='Interpretando… Voy a completar los datos con tu mensaje y los comprobantes.')
        snapshot=(text,paths,self.hint.get())
        def done(result):
            if snapshot!=(self.box.get('1.0','end').strip(),self.paths,self.hint.get()):
                self.status.configure(text='La entrada cambió durante la interpretación. Volvé a interpretar.');return
            if result.get('project_mismatch'):
                self.status.configure(text='Esta entrada corresponde a otro proyecto. Cambialo desde el botón de proyectos antes de registrar.');return
            rows,questions=proposals(result,people,categories,hint=hint,aliases=aliases,personal=personal,providers=providers,platforms=self.ledger.platforms())
            if questions:
                self.status.configure(text='Necesito aclarar: '+' · '.join(questions)+' Agregá la respuesta al mensaje.');return
            # Validate before showing the confirmation, so an incomplete AI reply
            # leads to a plain-language clarification instead of a blank form.
            try:
                rows=[validate(d,people,categories,**self.ledger.validation_options()) for d in rows]
            except (ValueError,KeyError) as e:
                self.status.configure(text='Falta aclarar un dato: '+str(e)+' Agregalo al mensaje y volvé a interpretar.');return
            self.pending=rows;self.snapshot=snapshot
            self.preview.configure(state='normal');self.preview.delete('1.0','end')
            for d in rows:
                self.preview.insert('end',d['kind']+' · '+usd(d['amount'])+'\n','title')
                self.preview.insert('end',d['description']+'\n')
                details=[d['date'],d['person'] or d['platform']]
                if d['kind']=='Gasto':details.extend([d['funding'],d['category'],d.get('provider_other') if d.get('provider')=='Otras' else d.get('provider','')])
                if d['kind']=='Retiro':details.extend(['Bruto '+usd(d['gross']),'Comisión '+usd(d['fee']),'Recibido' if d['received'] else 'En tránsito · incluido en caja' if d['include_pending'] else 'Pendiente de ingreso'])
                if d['kind']=='Insight':details.append('Mes '+d['period'])
                self.preview.insert('end',' · '.join(x for x in details if x)+'\n\n','muted')
            self.preview.configure(state='disabled');self.box.grid_remove();self.preview.grid(row=1,column=0,sticky='nsew')
            self.status.configure(text='Datos completados. Revisá el resumen y confirmá; para cambiar algo, usá Corregir con mensaje.')
            self.save_button.configure(state='normal')
        self.app.run(lambda:extract(text,paths,model,people,categories,hint=hint,aliases=aliases,balances=balances,project=project,providers=providers),done,on_error=self.failed)

    def commit(self):
        if self.app.busy or self.app.recording or not self.pending:return
        if self.snapshot!=(self.box.get('1.0','end').strip(),self.paths,self.hint.get()):self.correct();return
        try:
            rows=copy.deepcopy(self.pending)
            # A shared screenshot may contain several movements; ask about existing
            # entries only, not about the intentional batch sharing its receipt.
            attachments=[self.ledger.attachment(p) for p in self.paths]
            for d in rows:d['attachments']=copy.deepcopy(attachments)
            duplicates={x['id']:x for d in rows for x in self.ledger.duplicates(d)}
            if duplicates and not messagebox.askyesno('Posible duplicado','Hay registros parecidos:\n'+'\n'.join(x['description']+' · '+usd(x['amount']) for x in list(duplicates.values())[:5])+'\n\n¿Registrar estos movimientos como nuevos?',parent=self.app):return
            self.ledger.save(rows)
            self.invalidate();self.box.delete('1.0','end');self.changed();self.paths.clear();self.show_files()
            self.preview.grid_remove();self.box.grid();self.status.configure(text='Registro guardado. Podés contarme otro movimiento.')
            self.view.leave_capture();self.view.report_saved()
        except Exception as e:messagebox.showerror('Revisar registro',str(e),parent=self.app)
