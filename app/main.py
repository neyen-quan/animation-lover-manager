import base64, copy, datetime as dt, json, queue, shutil, tempfile, threading, uuid, wave, webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from .core import Store, PEOPLE, KINDS, STATES, ALIASES, fresh, today, urgency
from .ai import interpret, transcribe

BG='#10131d'; CARD='#1b2131'; FG='#e9ecf5'; MUTED='#a6b0c7'; ACCENT='#9d8cff'
class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('Animation Lover · Gestión'); self.geometry('1280x850'); self.configure(bg=BG)
        self.store=Store(); PEOPLE[:]=self.store.setting('people') or PEOPLE; ALIASES.update(self.store.setting('aliases') or {}); self.jobs=queue.Queue(); self.files=[]; self.tempfiles=[]; self.recording=None; self.busy=False
        self.protocol('WM_DELETE_WINDOW',self.close)
        style=ttk.Style(self); style.theme_use('clam')
        style.configure('.',background=BG,foreground=FG,font=('Segoe UI',11))
        style.configure('TButton',padding=9,background=CARD,foreground=FG)
        style.map('TButton',background=[('active','#353d59')])
        style.configure('Treeview',background=CARD,fieldbackground=CARD,foreground=FG,rowheight=38,borderwidth=0)
        style.configure('Treeview.Heading',background=BG,foreground=MUTED,padding=9)
        style.configure('TCombobox',fieldbackground=CARD,foreground=FG)
        self.view=tk.StringVar(value='Hoy'); self.author=tk.StringVar(value=PEOPLE[0]); self.filter_person=tk.StringVar(value='Todos'); self.keep=tk.BooleanVar(); self.search=tk.StringVar()
        header=ttk.Frame(self,padding=20); header.pack(fill='x')
        ttk.Label(header,text='ANIMATION LOVER',font=('Segoe UI',20,'bold')).pack(side='left')
        for title,cmd in [('Ajustes',self.settings),('Finanzas',self.finance),('Versiones',self.updates),('Deshacer',self.undo)]: ttk.Button(header,text=title,command=cmd).pack(side='right',padx=4)
        self.summary=ttk.Label(self,font=('Segoe UI',13)); self.summary.pack(anchor='w',padx=24,pady=8)
        bar=ttk.Frame(self,padding=12); bar.pack(fill='x')
        for v in ['Hoy','Todas','Por persona','Recientes','Idea','Roadmap','Nota','Papelera']:
            ttk.Button(bar,text=v,command=lambda x=v:self.change_view(x)).pack(side='left',padx=2)
        filters=ttk.Frame(self,padding=12); filters.pack(fill='x')
        ttk.Label(filters,text='Buscar').pack(side='left'); ttk.Entry(filters,textvariable=self.search,width=40).pack(side='left',padx=8)
        box=ttk.Combobox(filters,textvariable=self.filter_person,values=['Todos']+PEOPLE,state='readonly',width=12); box.pack(side='left'); box.bind('<<ComboboxSelected>>',lambda e:self.refresh())
        self.search.trace_add('write',lambda *a:self.refresh())
        ttk.Button(filters,text='Nueva tarjeta',command=lambda:self.editor(fresh())).pack(side='right')
        ttk.Button(filters,text='Reunión del martes',command=self.meeting).pack(side='right',padx=5)
        cols=('title','kind','owners','status','deadline','priority')
        self.tree=ttk.Treeview(self,columns=cols,show='headings',selectmode='browse')
        for key,label,width in zip(cols,['Pendiente / idea','Tipo','Responsables actuales','Estado','Límite','Prioridad'],[400,95,170,120,110,100]):
            self.tree.heading(key,text=label); self.tree.column(key,width=width,minwidth=70)
        self.tree.tag_configure('late',foreground='#ff879a'); self.tree.tag_configure('warning',foreground='#f4c77d')
        self.tree.pack(fill='both',expand=True,padx=20,pady=10); self.tree.bind('<Double-1>',lambda e:self.open_selected())
        actions=ttk.Frame(self,padding=10); actions.pack(fill='x')
        for title,cmd in [('Abrir / editar',self.open_selected),('Notificar',self.notify),('Eliminar / restaurar',self.delete),('Historial',self.history)]:ttk.Button(actions,text=title,command=cmd).pack(side='left',padx=5)
        capture=ttk.Frame(self,padding=16); capture.pack(fill='x')
        ttk.Label(capture,text='Soltá una idea o contá qué avanzó',font=('Segoe UI',14,'bold')).pack(anchor='w')
        self.input=tk.Text(capture,height=5,bg=CARD,fg=FG,insertbackground=FG,relief='flat',font=('Segoe UI',12),wrap='word'); self.input.pack(fill='x',pady=8)
        toolbar=ttk.Frame(capture); toolbar.pack(fill='x')
        ttk.Label(toolbar,text='Idea de').pack(side='left'); ttk.Combobox(toolbar,textvariable=self.author,values=PEOPLE,state='readonly',width=10).pack(side='left',padx=5)
        ttk.Checkbutton(toolbar,text='Conservar adjuntos',variable=self.keep).pack(side='left',padx=5)
        for title,cmd in [('Adjuntar',self.attach),('Pegar imagen',self.paste_image),('Grabar',self.record),('Parar y transcribir',lambda:self.stop(False)),('Parar y ejecutar',lambda:self.stop(True))]:ttk.Button(toolbar,text=title,command=cmd).pack(side='left',padx=2)
        ttk.Button(capture,text='Interpretar entrada',command=self.process).pack(side='right',pady=8)
        ttk.Button(capture,text='Actualizar seleccionada',command=lambda:self.process(self.selected())).pack(side='right',pady=8,padx=8)
        self.status=ttk.Label(capture,text='Listo. Doble clic en una tarjeta para expandirla.'); self.status.pack(side='left')
        self.input.insert('1.0',self.store.setting('draft') or '')
        self.input.bind('<<Modified>>',self.save_draft)
        self.refresh(); self.after(100,self.poll)
    def save_draft(self,event=None):
        if self.input.edit_modified():
            self.store.setting('draft',self.input.get('1.0','end').strip())
            self.input.edit_modified(False)
    def close(self):
        if self.busy or self.recording:
            messagebox.showinfo('Operación en curso','Esperá a que termine el procesamiento o detené la grabación.'); return
        for p in self.tempfiles: Path(p).unlink(missing_ok=True)
        self.store.db.close(); self.destroy()
    def change_view(self,v): self.view.set(v); self.refresh()
    def selected(self): return self.tree.selection()[0] if self.tree.selection() else None
    def refresh(self):
        items=self.store.items(self.view.get()=='Papelera'); q=self.search.get().casefold(); who=self.filter_person.get(); view=self.view.get()
        active=[d for d in self.store.items() if d['status']!='Terminado']
        self.summary.configure(text=f"Hoy, {today().strftime('%d/%m/%Y')}  ·  {len(active)} pendientes  ·  {sum(urgency(d)==3 for d in active)} vencidos  ·  {sum(bool(d.get('questions')) for d in active)} por aclarar")
        self.tree.delete(*self.tree.get_children())
        for d in sorted(items,key=lambda d:(-urgency(d),d['deadline'])) if view!='Recientes' else sorted(items,key=lambda d:d['updated'],reverse=True):
            if view=='Hoy' and (d['status']=='Terminado' or d['planned']>today().isoformat()):continue
            if view in KINDS and d['kind']!=view:continue
            if who!='Todos' and who not in d['owners']:continue
            if q and q not in json.dumps(d,ensure_ascii=False).casefold():continue
            u=urgency(d); title=('⚠ ' if d.get('questions') else '')+d['title']
            self.tree.insert('', 'end',iid=d['id'],values=(title,d['kind'],', '.join(d['owners']) or 'Por asignar',d['status'],d['deadline'],'MÁXIMA' if u==3 else d['priority']),tags=('late' if u==3 else 'warning' if u==2 else '',))
    def run(self,work,done):
        if self.busy:return
        self.busy=True; self.status.configure(text='Procesando…')
        def worker():
            try:self.jobs.put((done,work(),None))
            except Exception as e:self.jobs.put((done,None,str(e)))
        threading.Thread(target=worker,daemon=True).start()
    def poll(self):
        try:
            done,result,error=self.jobs.get_nowait(); self.busy=False
            if error:self.status.configure(text='No se pudo completar. Tu entrada sigue disponible.'); messagebox.showerror('No se pudo completar',error)
            else:
                try:done(result); self.status.configure(text='Listo · Podés deshacer el último cambio.')
                except Exception as e:messagebox.showerror('Revisar',str(e))
        except queue.Empty:pass
        self.after(100,self.poll)
    def save(self,items):
        try:self.store.apply(items)
        except Exception as e:messagebox.showerror('Guardar',str(e))
        self.refresh()
    def undo(self):self.store.undo(); self.refresh()
    def open_selected(self):
        id=self.selected()
        if id:self.editor(self.store.get(id))
    def editor(self,data):
        w=tk.Toplevel(self); w.title('Detalle de tarjeta'); w.geometry('720x740'); w.configure(bg=BG); fields={}
        for key,label,values in [('title','Título',None),('kind','Tipo',KINDS),('status','Estado',STATES),('author','Idea de',PEOPLE),('owners','Responsables (separados por coma)',None),('priority','Prioridad',['Baja','Media','Alta','Máxima']),('planned','Fecha prevista · AAAA-MM-DD',None),('deadline','Fecha límite · AAAA-MM-DD o AAAA-MM',None)]:
            ttk.Label(w,text=label).pack(anchor='w',padx=18)
            var=tk.StringVar(value=', '.join(data[key]) if key=='owners' else data[key]); fields[key]=var
            widget=ttk.Combobox(w,textvariable=var,values=values,state='readonly') if values else ttk.Entry(w,textvariable=var)
            widget.pack(fill='x',padx=18,pady=3)
        ttk.Label(w,text='Resumen').pack(anchor='w',padx=18)
        summary=tk.Text(w,height=4,bg=CARD,fg=FG,insertbackground=FG,wrap='word'); summary.insert('1.0',data['summary']); summary.pack(fill='x',padx=18)
        ttk.Label(w,text='Pendientes (uno por línea)').pack(anchor='w',padx=18)
        pending=tk.Text(w,height=3,bg=CARD,fg=FG,insertbackground=FG); pending.insert('1.0','\n'.join(data.get('pending',[]))); pending.pack(fill='x',padx=18)
        if data.get('questions'):ttk.Label(w,text='Por aclarar: '+' / '.join(data['questions']),wraplength=680).pack(padx=18,pady=8)
        def commit():
            d=copy.deepcopy(data); d.update({k:v.get() for k,v in fields.items()}); d['owners']=[p.strip() for p in d['owners'].split(',') if p.strip()]; d['summary']=summary.get('1.0','end').strip(); d['pending']=pending.get('1.0','end').strip().splitlines()
            try:self.store.apply([d]); self.refresh(); w.destroy()
            except Exception as e:messagebox.showerror('Revisar tarjeta',str(e),parent=w)
        ttk.Button(w,text='Guardar',command=commit).pack(pady=12)
    def process(self,target=None):
        if self.busy:return
        text=self.input.get('1.0','end').strip(); author=self.author.get(); items=self.store.items(); model=self.store.setting('model'); paths=list(self.files); keep=self.keep.get()
        if not text and not paths:return
        def work():
            combined=text; images=[]
            for path in paths:
                p=Path(path); ext=p.suffix.lower()
                if ext in ['.png','.jpg','.jpeg','.webp']:images.append(base64.b64encode(p.read_bytes()).decode())
                elif ext in ['.ogg','.opus','.wav','.mp3','.m4a','.mp4']:
                    if str(p) not in getattr(self,'already_transcribed',set()):combined+='\n'+transcribe(p)
                elif ext in ['.txt','.md','.csv']:combined+='\n'+p.read_text(encoding='utf-8')
                else:raise ValueError(f'Formato aún no interpretable: {ext}. Pegá el texto o una captura.')
            return interpret(combined,author,items,model,target,images)
        def done(result):
            if not isinstance(result.get('creates',[]),list) or not isinstance(result.get('updates',[]),list):raise ValueError('Respuesta de IA inválida.')
            if result.get('questions'):
                messagebox.showinfo('Necesito aclarar','\n'.join(result['questions'])+'\n\nAgregá tu respuesta a la entrada y volvé a interpretar.');return
            changes=[]
            for patch in result.get('creates',[]):
                d=fresh(author=author); allowed={'title','summary','kind','owners','priority','planned','deadline','pending','questions'}; d.update({k:v for k,v in patch.items() if k in allowed})
                similar=next((x for x in items if x['title'].casefold()==d['title'].casefold()),None)
                if similar:
                    messagebox.showinfo('Posible duplicado',f"Ya existe: {similar['title']}. Seleccionala y usá Actualizar seleccionada para unir el avance.");return
                changes.append(d)
            for update in result.get('updates',[]):
                id=update.get('id'); old=next((x for x in items if x['id']==id),None)
                if not old or (target and id!=target):raise ValueError('La IA indicó una tarjeta incorrecta; no se aplicaron cambios.')
                if self.store.get(id)!=old:raise ValueError('La tarjeta cambió durante el procesamiento. Reintentá.')
                d=copy.deepcopy(old); allowed={'title','summary','status','owners','priority','planned','deadline','pending','completed','questions'}
                d.update({k:v for k,v in update.get('patch',{}).items() if k in allowed}); changes.append(d)
            if not changes:raise ValueError('No se identificaron cambios. Aclaralos en la entrada.')
            if keep:
                folder=self.store.path.parent/'attachments'; folder.mkdir(exist_ok=True)
                for p in paths:
                    dest=folder/(str(uuid.uuid4())+Path(p).suffix); shutil.copy2(p,dest)
                    for d in changes:d.setdefault('attachments',[]).append(str(dest))
            self.store.apply(changes); self.input.delete('1.0','end'); self.files=[]; self.keep.set(False); self.refresh()
            for d in changes:
                if d.get('questions'):self.editor(d)
        self.run(work,done)
    def attach(self):
        paths=filedialog.askopenfilenames()
        self.files.extend(paths); self.status.configure(text=f'{len(self.files)} adjuntos · se procesarán con la entrada')
    def paste_image(self):
        try:
            from PIL import ImageGrab
            img=ImageGrab.grabclipboard()
            if not hasattr(img,'save'):raise ValueError('El portapapeles no contiene una imagen.')
            path=Path(tempfile.gettempdir())/(str(uuid.uuid4())+'.png');img.save(path);self.files.append(str(path));self.tempfiles.append(str(path));self.status.configure(text='Captura agregada')
        except Exception as e:messagebox.showerror('Pegar captura',str(e))
    def record(self):
        if self.recording or self.busy:return
        try:
            import sounddevice as sd
            self.chunks=[]
            self.recording=sd.RawInputStream(samplerate=16000,channels=1,dtype='int16',callback=lambda data,frames,time,status:self.chunks.append(bytes(data)))
            self.recording.start();self.status.configure(text='Grabando…');self.record_timer=self.after(3600000,lambda:self.stop(False))
        except Exception as e:self.recording=None;messagebox.showerror('Micrófono',str(e))
    def stop(self,execute):
        if not self.recording:return
        self.after_cancel(self.record_timer);self.recording.stop();self.recording.close();self.recording=None
        path=Path(tempfile.gettempdir())/(str(uuid.uuid4())+'.wav');self.tempfiles.append(str(path))
        with wave.open(str(path),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b''.join(self.chunks))
        self.chunks=[]
        if self.keep.get():self.files.append(str(path))
        def done(text):
            self.input.insert('end','\n'+text)
            if not hasattr(self,'already_transcribed'):self.already_transcribed=set()
            self.already_transcribed.add(str(path))
            if not self.keep.get():path.unlink(missing_ok=True)
            if execute:self.process()
        self.run(lambda:transcribe(path),done)
    def delete(self):
        id=self.selected()
        if id:
            d=self.store.get(id);d['deleted']=not d.get('deleted');self.save([d])
    def meeting(self):
        if any(d.get('recurrence')=='tuesday' and d['status']!='Terminado' for d in self.store.items()):messagebox.showinfo('Reunión','Ya hay una reunión pendiente.');return
        date=today()+dt.timedelta(days=(1-today().weekday())%7); d=fresh('Reunión semanal');d.update(recurrence='tuesday',owners=[PEOPLE[0]],planned=date.isoformat(),deadline=date.isoformat());self.save([d])
    def notify(self):
        id=self.selected()
        if not id:return
        d=self.store.get(id);w=tk.Toplevel(self);w.title('Notificar · editar y copiar');w.geometry('650x380')
        box=tk.Text(w,wrap='word',bg=CARD,fg=FG,insertbackground=FG,font=('Segoe UI',12));box.pack(fill='both',expand=True)
        box.insert('1.0',f"{', '.join(d['owners']) or 'Equipo'}, ¿cómo vienen con esto?\n\n{d['title']}\n{d['summary']}\n\nPendiente: {', '.join(d.get('pending',[]))}\nFecha límite: {d['deadline']}")
        def copy_text():
            text=box.get('1.0','end').strip();self.clipboard_clear();self.clipboard_append(text)
            samples=self.store.setting('writing_samples') or [];self.store.setting('writing_samples',(samples+[text])[-20:]);w.destroy()
        ttk.Button(w,text='Copiar mensaje',command=copy_text).pack(pady=10)
    def history(self):
        w=tk.Toplevel(self);w.title('Historial');w.geometry('700x450');box=tk.Text(w,bg=CARD,fg=FG,wrap='word');box.pack(fill='both',expand=True)
        for stamp,after,undone in self.store.db.execute('SELECT stamp,after,undone FROM history ORDER BY seq DESC LIMIT 100'):
            box.insert('end',stamp+(' · Deshecho' if undone else '')+'\n'+'\n'.join(d['title'] for d in json.loads(after))+'\n\n')
        box.configure(state='disabled')
    def settings(self):
        w=tk.Toplevel(self);w.title('Ajustes');w.geometry('650x470');w.configure(bg=BG)
        ttk.Label(w,text='Personas del equipo (una por línea). Guardar y reiniciar.').pack(pady=8)
        roster=tk.Text(w,height=5);roster.insert('1.0','\n'.join(PEOPLE));roster.pack(fill='x',padx=12)
        def save_people():
            names=[n.strip() for n in roster.get('1.0','end').splitlines() if n.strip()]
            if not names or len(names)!=len(set(names)):messagebox.showerror('Equipo','Ingresá nombres distintos.');return
            if self.store.items():messagebox.showinfo('Equipo','Para renombrar personas con tareas existentes se necesita una migración.');return
            self.store.setting('people',names);messagebox.showinfo('Equipo','Guardado. Cerrá y volvé a abrir la aplicación.')
        ttk.Button(w,text='Guardar equipo local',command=save_people).pack()
        ttk.Label(w,text='Modelo local instalado en Ollama').pack(pady=12);var=tk.StringVar(value=self.store.setting('model') or '');ttk.Entry(w,textvariable=var,width=45).pack()
        ttk.Label(w,text='La IA requiere Ollama en esta PC. No se conectan APIs pagas.\nLa transcripción descarga un modelo local la primera vez.',wraplength=590).pack(pady=12)
        ttk.Button(w,text='Guardar modelo',command=lambda:(self.store.setting('model',var.get().strip()),w.destroy())).pack()
        def backup_folder():
            path=filedialog.askdirectory()
            if path:self.store.setting('backup_folder',path);self.store.backup()
        ttk.Button(w,text='Carpeta de respaldo (puede ser Google Drive sincronizado)',command=backup_folder).pack(pady=12)
        ttk.Label(w,text=f'Datos locales: {self.store.path}',wraplength=600).pack()
    def finance(self):messagebox.showinfo('Finanzas · Próximamente','Módulo previsto: gastos, ganancias y repartos. Se definirá e implementará más adelante.')
    def updates(self):
        # Primera entrega: acceso explícito a Releases. Sin ejecutar binarios no verificados.
        webbrowser.open('https://github.com/neyen-quan/animation-lover-manager/releases')
if __name__=='__main__':App().mainloop()
