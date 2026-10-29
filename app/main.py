import base64, copy, datetime as dt, json, queue, shutil, tempfile, threading, uuid, wave, webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from .core import Store, PEOPLE, KINDS, STATES, ALIASES, fresh, today, urgency
from .ai import interpret, transcribe

from . import __version__
from .theme import BG, CARD, FG, MUTED, ACCENT, SURFACE, LINE, SHELL, apply_theme
from .widgets import ScrollArea, WrapBar, NavItem
from .board import TaskBoard
from .windowing import place_window
from .projects import Projects
from .project_picker import ProjectTabs
from .theme import apply_project_theme,recolor_widgets

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('Animation Lover · Gestión · '+__version__)
        self.withdraw();self.minsize(780,520)
        apply_theme(self)
        import sys
        icon=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))/'assets/icon.png'
        if icon.exists():self._icon=tk.PhotoImage(file=icon);self.iconphoto(True,self._icon)
        self.root_store=Store();self.projects=Projects(self.root_store);self.project_id='main';self.store=self.root_store
        self.project_states={};self.finance_views={};self._switching_project=False
        PEOPLE[:]=self.store.people();ALIASES.clear();ALIASES.update(self.store.setting('aliases') or {})
        self.jobs=queue.Queue();self.files=[];self.tempfiles=[];self.recording=None;self.busy=False
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.view=tk.StringVar(value='Hoy');self.author=tk.StringVar(value=PEOPLE[0]);self.filter_person=tk.StringVar(value='Todos');self.keep=tk.BooleanVar();self.search=tk.StringVar()
        self.columnconfigure(1,weight=1);self.rowconfigure(1,weight=1)
        header=ttk.Frame(self,padding=(20,12),style='Shell.TFrame');self.header=header;self._header_stacked=None;header.grid(row=0,column=0,columnspan=2,sticky='ew');header.columnconfigure(0,weight=1)
        self.project_name=tk.StringVar(value='Animation Lover')
        self.project_selector=ProjectTabs(header,self.projects.list(),self.project_id,self.switch_project)
        self.project_selector.grid(row=0,column=0,sticky='ew',padx=(0,10))
        self.capture_button=ttk.Button(header,text='+ Soltar idea',command=self.toggle_capture);self.capture_button.grid(row=0,column=1,padx=5)
        self.update_button=ttk.Button(header,text='Actualizar programa',style='Accent.TButton',command=self.updates);self.update_button.grid(row=0,column=2,padx=5)
        self.settings_button=ttk.Button(header,text='Ajustes',command=self.settings);self.settings_button.grid(row=0,column=3,padx=(5,0))
        self.header.bind('<Configure>',self.layout_header)
        sidebar=tk.Frame(self,bg=BG,width=round(190*max(.85,float(self.tk.call('tk','scaling'))/1.333)));sidebar.grid(row=1,column=0,sticky='ns');sidebar.grid_propagate(False);sidebar.rowconfigure(0,weight=1);sidebar.columnconfigure(0,weight=1)
        nav=ttk.Frame(sidebar,padding=(14,12));nav.grid(row=0,column=0,sticky='nsew')
        ttk.Label(nav,text='ESPACIO PERSONAL',foreground=MUTED,font=('Segoe UI',8,'bold')).pack(anchor='w',padx=10,pady=(0,8))
        self.nav_buttons={}
        for v,label in [('Hoy','Mi día'),('Todas','Mi tablero'),('Por persona','Por persona'),('Recientes','Recientes')]:
            button=NavItem(nav,text=label,key=v,command=lambda x=v:self.change_view(x));button.pack(fill='x',pady=2);self.nav_buttons[v]=button
        ttk.Label(nav,text='ORGANIZACIÓN',foreground=MUTED,font=('Segoe UI',8,'bold')).pack(anchor='w',padx=10,pady=(15,6))
        for v,label in [('Idea','Ideas'),('Roadmap','Roadmap'),('Nota','Notas'),('Papelera','Papelera')]:
            button=NavItem(nav,text=label,key=v,command=lambda x=v:self.change_view(x));button.pack(fill='x',pady=2);self.nav_buttons[v]=button
        ttk.Separator(nav).pack(fill='x',pady=12)
        self.finance_button=NavItem(nav,text='Finanzas',key='Finanzas',command=self.finance);self.finance_button.pack(fill='x');self.finance_view=None
        self.project_caption=ttk.Label(nav,text='Animation Lover  '+__version__,foreground=MUTED,font=('Segoe UI',8),wraplength=150);self.project_caption.pack(anchor='w',padx=10,pady=12)
        content=ttk.Frame(self,padding=(22,16,24,12));content.grid(row=1,column=1,sticky='nsew');self.content=content
        content.columnconfigure(0,weight=1);content.rowconfigure(5,weight=1)
        self.page_title=ttk.Label(content,text='Mi día',font=('Segoe UI',25,'bold'));self.page_title.grid(row=0,column=0,sticky='w')
        self.summary=ttk.Label(content,foreground=MUTED);self.summary.grid(row=1,column=0,sticky='ew',pady=(4,12))
        stats=ttk.Frame(content);stats.grid(row=2,column=0,sticky='ew',pady=(0,12));self.metrics={}
        for index,(key,label,color) in enumerate([('pending','POR HACER','#a7afff'),('running','EN CURSO','#fdab3d'),('overdue','VENCIDAS','#f07188')]):
            stats.columnconfigure(index,weight=1,uniform='metric')
            tile=tk.Frame(stats,bg='#232c43',highlightthickness=1,highlightbackground='#46516e',padx=16,pady=9);tile.grid(row=0,column=index,sticky='ew',padx=(0,10 if index<2 else 0))
            tk.Frame(tile,height=2,bg=color).pack(fill='x',pady=(0,5))
            number=tk.Label(tile,text='0',font=('Segoe UI',21,'bold'),bg='#232c43',fg=color);number.pack(anchor='w')
            caption=tk.Label(tile,text=label,font=('Segoe UI',9,'bold'),bg='#232c43',fg=color,justify='left');caption.pack(anchor='w',pady=(3,0))
            tile.bind('<Configure>',lambda e,c=caption:c.configure(wraplength=max(50,e.width-32)));self.metrics[key]=number
        tabs=WrapBar(content);tabs.grid(row=3,column=0,sticky='ew',pady=(0,8));self.layout_buttons={}
        for mode,label in [('table','Tabla principal'),('cards','Tarjetas')]:self.layout_buttons[mode]=tabs.add(ttk.Button(tabs,text=label,style='Tab.TButton',command=lambda m=mode:self.set_layout(m)))
        filters=WrapBar(content,style='Toolbar.TFrame');filters.inset=5;filters.grid(row=4,column=0,sticky='ew',pady=(0,12))
        filters.add(ttk.Button(filters,text='+ Nueva tarjeta',style='Accent.TButton',command=lambda:self.editor(self.new_item())))
        filters.add(ttk.Label(filters,text='Buscar',style='Toolbar.TLabel'))
        filters.add(ttk.Entry(filters,textvariable=self.search,width=18))
        box=filters.add(ttk.Combobox(filters,textvariable=self.filter_person,values=['Todos']+PEOPLE,state='readonly',width=12));box.bind('<<ComboboxSelected>>',lambda e:self.refresh());self.people_filter=box
        self.task_filters=filters;self.meeting_button=filters.add(ttk.Button(filters,text='Reunión semanal',command=self.meeting))
        self.board=TaskBoard(content,self.open_selected,lambda:self.editor(self.new_item()),self.board_action);self.board.grid(row=5,column=0,sticky='nsew')
        self.tree=self.board
        actions=WrapBar(content);actions.grid(row=6,column=0,sticky='ew',pady=(6,0));self.task_actions=actions
        for title,cmd in [('Abrir tarjeta',self.open_selected),('Preparar mensaje',self.notify),('Historial',self.history),('Deshacer',self.undo)]:actions.add(ttk.Button(actions,text=title,command=cmd))
        self.capture_visible=False
        self.capture_window=tk.Toplevel(self);self.capture_window.withdraw();self.capture_window.title('Soltar idea · Animation Lover');self.capture_window.configure(bg=BG);self.capture_window.transient(self);self.capture_window.protocol('WM_DELETE_WINDOW',self.hide_capture)
        self.capture_window.minsize(620,440);self.capture_window.rowconfigure(0,weight=1);self.capture_window.columnconfigure(0,weight=1)
        self.capture=ttk.Frame(self.capture_window,padding=22);capture=self.capture;capture.grid(row=0,column=0,sticky='nsew');capture.columnconfigure(0,weight=1);capture.rowconfigure(2,weight=1)
        capture_header=ttk.Frame(capture);capture_header.grid(row=0,column=0,sticky='ew');capture_header.columnconfigure(0,weight=1)
        ttk.Label(capture_header,text='Soltá una idea',font=('Segoe UI',17,'bold')).grid(row=0,column=0,sticky='w')
        ttk.Button(capture_header,text='Cerrar',command=self.hide_capture).grid(row=0,column=1)
        ttk.Label(capture,text='Texto, voz o capturas. Contalo con tus palabras.',foreground=MUTED).grid(row=1,column=0,sticky='w',pady=(4,10))
        self.input=tk.Text(capture,height=4,bg=SURFACE,fg=FG,insertbackground=FG,relief='flat',highlightthickness=1,highlightbackground=LINE,highlightcolor=ACCENT,font=('Segoe UI',11),wrap='word',padx=14,pady=12)
        self.input.grid(row=2,column=0,sticky='nsew')
        toolbar=WrapBar(capture);toolbar.grid(row=3,column=0,sticky='ew',pady=7)
        self.capture_toolbar=toolbar;self.author_label=toolbar.add(ttk.Label(toolbar,text='Idea de'))
        self.author_box=toolbar.add(ttk.Combobox(toolbar,textvariable=self.author,values=PEOPLE,state='readonly',width=12))
        toolbar.add(ttk.Checkbutton(toolbar,text='Conservar adjuntos',variable=self.keep))
        for title,cmd in [('Adjuntar',self.attach),('Pegar imagen',self.paste_image)]:toolbar.add(ttk.Button(toolbar,text=title,command=cmd))
        voice=WrapBar(capture);voice.grid(row=4,column=0,sticky='ew',pady=(0,7))
        for title,cmd in [('Grabar',self.record),('Parar y transcribir',lambda:self.stop(False)),('Parar y ejecutar',lambda:self.stop(True))]:voice.add(ttk.Button(voice,text=title,command=cmd))
        self.capture_status=ttk.Label(capture,text='Tu entrada se conserva si cerrás esta ventana.',foreground=MUTED,wraplength=650);self.capture_status.grid(row=6,column=0,sticky='ew',pady=(10,0))
        submit=WrapBar(capture);submit.grid(row=5,column=0,sticky='ew')
        self.interpret_button=submit.add(ttk.Button(submit,text='Interpretar entrada',style='Accent.TButton',command=self.process))
        self.selected_button=submit.add(ttk.Button(submit,text='Actualizar seleccionada',command=self.process_selected))
        self.status=ttk.Label(self,text='Listo · Seleccioná una tarea o tocá Soltar idea.',foreground=MUTED,padding=(20,8),wraplength=700);self.status.grid(row=2,column=0,columnspan=2,sticky='ew')
        self.input.insert('1.0',self.store.setting('draft') or '');self.input.bind('<<Modified>>',self.save_draft)
        self.search.trace_add('write',lambda *a:self.refresh())
        self.set_layout(self.store.setting('board_layout') or 'table');self.refresh();self._poll_job=self.after(100,self.poll);self._result_job=self.after(1500,self.show_update_result)
        self.configure_project_controls();self.start_area=place_window(self)
    @property
    def personal(self):return bool(self.store.setting('personal'))
    def new_item(self):
        d=fresh(author=PEOPLE[0])
        if self.personal:d['owners']=[PEOPLE[0]]
        return d
    def configure_project_controls(self):
        personal=self.personal
        button=self.nav_buttons['Por persona']
        if personal:button.pack_forget()
        else:button.pack(fill='x',pady=2,before=self.nav_buttons['Recientes'])
        self.task_filters.set_visible(self.people_filter,not personal)
        self.task_filters.set_visible(self.meeting_button,not personal)
        self.capture_toolbar.set_visible(self.author_label,not personal)
        self.capture_toolbar.set_visible(self.author_box,not personal)
        for child in self.task_actions.children_list:
            if isinstance(child,ttk.Button) and str(child.cget('text'))=='Preparar mensaje':self.task_actions.set_visible(child,not personal)
        self.board.personal=personal
        name=self.projects.descriptor(self.project_id)['name']
        self.project_caption.configure(text=name+'  '+__version__)
        self.capture_window.title('Soltar idea · '+name)
        self.title(name+' · Gestión · '+__version__)
        self.project_selector.refresh(self.projects.list(),self.project_id)
        self.restyle_project()
    def restyle_project(self):
        apply_project_theme(self,self.personal)
        self.project_selector.redraw();self.layout_header()
        for button in list(self.nav_buttons.values())+[self.finance_button]:button.draw()
        self.board.render()
        for view in self.finance_views.values():view.draw_metrics();view.draw_chart()
    def layout_header(self,event=None):
        buttons=(self.capture_button,self.update_button,self.settings_button)
        project_width=sum(t.winfo_reqwidth()+6 for t in self.project_selector.tabs.values())
        needed=project_width+sum(b.winfo_reqwidth()+10 for b in buttons)+50
        stacked=self.header.winfo_width()<needed
        if stacked==self._header_stacked:return
        self._header_stacked=stacked
        self.project_selector.grid_configure(row=0,column=0,columnspan=4 if stacked else 1,pady=(0,4 if stacked else 0))
        for i,button in enumerate(buttons,1):button.grid_configure(row=1 if stacked else 0,column=i)

    def switch_project(self,id):
        previous=self.projects.descriptor(self.project_id)
        if id==self.project_id:return True
        if self.busy or self.recording:
            self.project_name.set(previous['name']);messagebox.showinfo('Operación en curso','Terminá la grabación o el procesamiento antes de cambiar de proyecto.',parent=self);return False
        visible=[w for w in self.winfo_children() if isinstance(w,tk.Toplevel) and w is not self.capture_window and w.state()!='withdrawn']
        if visible:
            self.project_name.set(previous['name']);messagebox.showinfo('Cerrar ventana','Cerrá el detalle o ajuste abierto antes de cambiar de proyecto.',parent=visible[0]);return False
        try:target=self.projects.open(id)
        except Exception as e:
            self.project_name.set(previous['name']);messagebox.showerror('Proyecto',str(e),parent=self);return False
        self.save_draft();self.hide_capture()
        self.project_states[self.project_id]=dict(files=list(self.files),keep=self.keep.get(),author=self.author.get(),transcribed=set(getattr(self,'already_transcribed',set())))
        if self.finance_view:self.finance_view.grid_remove()
        self._switching_project=True
        try:
            self.project_id=id;self.store=target
            PEOPLE[:]=target.people();ALIASES.clear();ALIASES.update(target.setting('aliases') or {})
            state=self.project_states.get(id,{})
            self.author.set(state.get('author',PEOPLE[0]));self.author_box.configure(values=PEOPLE)
            self.files=list(state.get('files',[]));self.keep.set(state.get('keep',False));self.already_transcribed=set(state.get('transcribed',set()))
            self.people_filter.configure(values=['Todos']+PEOPLE);self.filter_person.set('Todos')
            self.input.delete('1.0','end');self.input.insert('1.0',target.setting('draft') or '');self.input.edit_modified(False)
            self.finance_view=self.finance_views.get(id)
            self.board.selected_id=None;self.board.page=0;self.board.collapsed.clear();self.search.set('')
            self.set_layout(target.setting('board_layout') or 'table');self.change_view('Hoy')
            self.project_name.set(self.projects.descriptor(id)['name']);self.configure_project_controls()
            self.status.configure(text='Proyecto: '+self.project_name.get()+' · Listo')
        finally:self._switching_project=False
        return True
    def import_project(self,parent):
        path=filedialog.askopenfilename(parent=parent,title='Configuración privada de proyecto',filetypes=[('Proyecto','*.almproject')])
        if not path:return
        try:
            data=self.projects.preview_import(path)
            from .finance import totals,usd
            t=totals(data['entries'])
            message=data['project']['name']+'\nProyecto personal · USD\nGastos iniciales: '+usd(t['expenses'])+'\nDinero propio por recuperar: '+usd(t['debt_total'])+'\n\n¿Cargar este proyecto?'
            if not messagebox.askyesno('Revisar proyecto',message,parent=parent):return
            self.projects.import_project(data)
            self.project_selector.refresh(self.projects.list(),self.project_id)
            messagebox.showinfo('Proyecto cargado','Ya podés elegirlo con su botón de arriba a la izquierda.'+('\n'+self.projects.backup_warning if self.projects.backup_warning else ''),parent=parent)
        except Exception as e:messagebox.showerror('Importar proyecto',str(e),parent=parent)

    def toggle_capture(self):
        self.show_capture()
    def show_capture(self):
        finance_view=getattr(self,'finance_view',None)
        composer=getattr(finance_view,'composer',None)
        if composer is not None and composer.stream:
            self.finance();return
        finance_capture=getattr(self,'finance_capture',None)
        if finance_capture is not None and finance_capture.winfo_exists():
            finance_capture.lift();messagebox.showinfo('Registro abierto','Cerrá el registro de Finanzas para abrir una entrada de tareas.',parent=finance_capture);return
        if self.busy and getattr(self,'_processing_capture',False):
            messagebox.showinfo('Procesando','Estoy organizando la entrada. La tarjeta aparecerá al terminar.',parent=self);return
        if not self.capture_visible:
            self.capture_visible=True;place_window(self.capture_window,840,540,parent=self)
        self.capture_window.lift();self.input.focus_set()
    def hide_capture(self,force=False):
        if not force and (self.recording or self.busy):
            messagebox.showinfo('Operación en curso','Terminá la grabación o el procesamiento antes de cerrar.',parent=self.capture_window);return
        self.save_draft();self.capture_visible=False;self.capture_window.withdraw()
    def set_layout(self,mode):
        mode=mode if mode in ('table','cards') else 'table'
        self.board.set_mode(mode);self.store.setting('board_layout',mode)
        for key,button in self.layout_buttons.items():button.configure(style='Active.Tab.TButton' if key==mode else 'Tab.TButton')
    def board_action(self,action):
        if action=='open':self.open_selected()
        elif action=='notify':self.notify()
        elif action=='delete':self.delete()
    def show_update_result(self):
        receipt=self.root_store.path.parent/'last-update.json'
        if not receipt.exists():return
        try:
            result=json.loads(receipt.read_text());key=result.get('id') or str(receipt.stat().st_mtime_ns)
            if self.store.setting('update_result_seen')==key:return
            self.store.setting('update_result_seen',key)
            if result.get('success'):self.status.configure(text='Actualización instalada · Versión '+str(result.get('to')))
            else:messagebox.showwarning('Actualización revertida',result.get('error','No se pudo actualizar. Se conservó la versión anterior.'),parent=self)
        except (OSError,ValueError):pass
    def process_selected(self):
        target=self.selected()
        if not target:messagebox.showinfo('Elegí una tarjeta','Seleccioná la tarjeta que querés actualizar.',parent=self);return
        self.process(target)
    def save_draft(self,event=None):
        if self._switching_project:return
        if self.input.edit_modified():
            self.store.setting('draft',self.input.get('1.0','end').strip())
            self.input.edit_modified(False)
    def destroy(self):
        for name in ('_poll_job','_result_job','record_timer'):
            job=getattr(self,name,None)
            if job:
                try:self.after_cancel(job)
                except tk.TclError:pass
        super().destroy()
    def close(self):
        if self.busy or self.recording:
            messagebox.showinfo('Operación en curso','Esperá a que termine el procesamiento o detené la grabación.',parent=self); return
        for p in self.tempfiles: Path(p).unlink(missing_ok=True)
        self.projects.close(); self.destroy()
    def change_view(self,v):
        if self.finance_view:self.finance_view.grid_remove()
        self.content.grid();self.finance_button.set_active(False);self.view.set(v);self.refresh()
    def selected(self): return self.tree.selection()[0] if self.tree.selection() else None
    def refresh(self):
        view=self.view.get();items=self.store.items(view=='Papelera');q=self.search.get().casefold();who=self.filter_person.get()
        active=[d for d in self.store.items() if d['status']!='Terminado']
        self.metrics['pending'].configure(text=str(sum(d['status']=='Pendiente' for d in active)))
        self.metrics['running'].configure(text=str(sum(d['status']=='En curso' for d in active)))
        self.metrics['overdue'].configure(text=str(sum(urgency(d)==3 for d in active)))
        labels={'Hoy':'Mi día','Todas':'Mi tablero','Idea':'Ideas','Nota':'Notas'}
        self.page_title.configure(text=labels.get(view,view))
        for key,button in self.nav_buttons.items():button.set_active(key==view)
        filtered=[]
        for d in sorted(items,key=lambda d:d['updated'],reverse=True) if view=='Recientes' else sorted(items,key=lambda d:(-urgency(d),d['deadline'])):
            if view=='Hoy' and (d['status']=='Terminado' or d['planned']>today().isoformat()):continue
            if view in KINDS and d['kind']!=view:continue
            if who!='Todos' and who not in d['owners']:continue
            if q and q not in json.dumps(d,ensure_ascii=False).casefold():continue
            filtered.append(d)
        self.summary.configure(text=f"{today().strftime('%d/%m/%Y')}   ·   {len(filtered)} elementos en esta vista   ·   {sum(bool(d.get('questions')) for d in active)} por aclarar")
        self.board.group_mode='recent' if view=='Recientes' else 'status'
        self.board.set_items(filtered)
    def run(self,work,done,on_error=None):
        if self.busy:return
        self.busy=True; self.status.configure(text='Procesando…');self.capture_status.configure(text='Procesando…')
        def worker():
            try:self.jobs.put((done,work(),None,on_error))
            except Exception as e:self.jobs.put((done,None,str(e),on_error))
        threading.Thread(target=worker,daemon=True).start()
    def poll(self):
        try:
            done,result,error,on_error=self.jobs.get_nowait();self.busy=False;self._processing_capture=False
            if error:
                if on_error:on_error()
                self.status.configure(text='No se pudo completar. Tu entrada sigue disponible.');self.capture_status.configure(text='No se pudo completar. Podés corregir y reintentar.')
                messagebox.showerror('No se pudo completar',error,parent=self.capture_window if self.capture_visible else self)
            else:
                try:
                    done(result)
                    if not self.busy:self.status.configure(text='Listo · Podés deshacer el último cambio.');self.capture_status.configure(text='Listo · Podés revisar el texto y enviarlo.')
                except Exception as e:
                    if on_error:on_error()
                    messagebox.showerror('Revisar',str(e),parent=self.capture_window if self.capture_visible else self)
        except queue.Empty:pass
        self._poll_job=self.after(100,self.poll)
    def save(self,items):
        try:self.store.apply(items)
        except Exception as e:messagebox.showerror('Guardar',str(e),parent=self)
        self.refresh()
    def undo(self):self.store.undo(); self.refresh()
    def open_selected(self):
        id=self.selected()
        if id:self.editor(self.store.get(id))
    def editor(self,data):
        window=tk.Toplevel(self);window.withdraw();window.transient(self);window.title('Detalle de tarjeta');window.configure(bg=BG)
        window.minsize(480,400)
        header=ttk.Frame(window,padding=(24,20));header.pack(fill='x')
        ttk.Label(header,text='Detalle de tarjeta',font=('Segoe UI',20,'bold')).pack(anchor='w')
        ttk.Label(header,text='Organizá el trabajo y lo que falta hacer.',foreground=MUTED).pack(anchor='w',pady=(5,0))
        footer=ttk.Frame(window,padding=(24,14));footer.pack(side='bottom',fill='x')
        area=ScrollArea(window);area.pack(fill='both',expand=True)
        body=ttk.Frame(area.body,padding=(24,4,24,20));body.pack(fill='both',expand=True)
        fields={}
        ttk.Label(body,text='TÍTULO',foreground=MUTED,font=('Segoe UI',9,'bold')).pack(anchor='w',pady=(0,7))
        fields['title']=tk.StringVar(value=data['title']);ttk.Entry(body,textvariable=fields['title'],font=('Segoe UI',13,'bold')).pack(fill='x')
        ttk.Label(body,text='RESUMEN',foreground=MUTED,font=('Segoe UI',9,'bold')).pack(anchor='w',pady=(22,7))
        summary=tk.Text(body,height=4,bg=SURFACE,fg=FG,insertbackground=FG,highlightthickness=1,highlightbackground=LINE,highlightcolor=ACCENT,relief='flat',font=('Segoe UI',11),wrap='word',padx=12,pady=10)
        summary.insert('1.0',data['summary']);summary.pack(fill='x')
        ttk.Label(body,text='Organización',font=('Segoe UI',13,'bold')).pack(anchor='w',pady=(24,12))
        props=ttk.Frame(body);props.pack(fill='x');props.columnconfigure(0,weight=1,uniform='field');props.columnconfigure(1,weight=1,uniform='field')
        for index,(key,label,values) in enumerate([('kind','Tipo',KINDS),('status','Estado',STATES),('author','Idea de',PEOPLE),('owners','Responsables · separados por coma',None),('priority','Prioridad',['Baja','Media','Alta','Máxima']),('planned','Fecha prevista · AAAA-MM-DD',None),('deadline','Fecha límite · AAAA-MM-DD o AAAA-MM',None)]):
            if self.personal and key in ('author','owners'):continue
            field=ttk.Frame(props,padding=(0,0,12,12));field.grid(row=index//2,column=index%2,sticky='ew');field.columnconfigure(0,weight=1)
            ttk.Label(field,text=label,foreground=MUTED,wraplength=280).grid(row=0,column=0,sticky='w',pady=(0,6))
            var=tk.StringVar(value=', '.join(data[key]) if key=='owners' else data[key]);fields[key]=var
            widget=ttk.Combobox(field,textvariable=var,values=values,state='readonly') if values else ttk.Entry(field,textvariable=var)
            widget.grid(row=1,column=0,sticky='ew')
        ttk.Label(body,text='PENDIENTES',foreground=MUTED,font=('Segoe UI',9,'bold')).pack(anchor='w',pady=(15,7))
        pending=tk.Text(body,height=4,bg=SURFACE,fg=FG,insertbackground=FG,highlightthickness=1,highlightbackground=LINE,highlightcolor=ACCENT,relief='flat',font=('Segoe UI',11),wrap='word',padx=12,pady=10)
        pending.insert('1.0','\n'.join(data.get('pending',[])));pending.pack(fill='x')
        if data.get('questions'):ttk.Label(body,text='Por aclarar: '+' / '.join(data['questions']),foreground='#fdab3d',wraplength=580).pack(fill='x',pady=15)
        def commit():
            d=copy.deepcopy(data);d.update({k:v.get() for k,v in fields.items()});d['owners']=([PEOPLE[0]] if self.personal else [p.strip() for p in d['owners'].split(',') if p.strip()]);d['summary']=summary.get('1.0','end').strip();d['pending']=pending.get('1.0','end').strip().splitlines()
            try:self.store.apply([d]);self.refresh();window.destroy()
            except Exception as e:messagebox.showerror('Revisar tarjeta',str(e),parent=window)
        ttk.Button(footer,text='Guardar cambios',style='Accent.TButton',command=commit).pack(side='right')
        ttk.Button(footer,text='Cancelar',command=window.destroy).pack(side='right',padx=8)
        place_window(window,760,780,parent=self)
    def process(self,target=None):
        if self.busy:return
        text=self.input.get('1.0','end').strip(); author=self.author.get(); items=self.store.items(); model=self.store.setting('model'); paths=list(self.files); keep=self.keep.get()
        if not text and not paths:return
        project_context=self.projects.context(self.project_id)
        def work():
            combined=text; images=[]
            for path in paths:
                p=Path(path); ext=p.suffix.lower()
                if ext in ['.png','.jpg','.jpeg','.webp']:images.append(base64.b64encode(p.read_bytes()).decode())
                elif ext in ['.ogg','.opus','.wav','.mp3','.m4a','.mp4']:
                    if str(p) not in getattr(self,'already_transcribed',set()):combined+='\n'+transcribe(p)
                elif ext in ['.txt','.md','.csv']:combined+='\n'+p.read_text(encoding='utf-8')
                else:raise ValueError(f'Formato aún no interpretable: {ext}. Pegá el texto o una captura.')
            return interpret(combined,author,items,model,target,images,project=project_context)
        def done(result):
            if not isinstance(result.get('creates',[]),list) or not isinstance(result.get('updates',[]),list):raise ValueError('Respuesta de IA inválida.')
            if result.get('project_mismatch'):
                self.show_capture();messagebox.showinfo('Revisar proyecto','La entrada parece corresponder a otro proyecto. Seleccionalo arriba antes de enviarla. No se guardaron cambios.',parent=self);return
            if result.get('questions'):
                self.show_capture()
                messagebox.showinfo('Necesito aclarar','\n'.join(result['questions'])+'\n\nAgregá tu respuesta a la entrada y volvé a interpretar.',parent=self);return
            changes=[]
            for patch in result.get('creates',[]):
                d=fresh(author=author); allowed={'title','summary','kind','owners','priority','planned','deadline','pending','questions'}; d.update({k:v for k,v in patch.items() if k in allowed})
                similar=next((x for x in items if x['title'].casefold()==d['title'].casefold()),None)
                if similar:
                    self.show_capture()
                    messagebox.showinfo('Posible duplicado',f"Ya existe: {similar['title']}. Seleccionala y usá Actualizar seleccionada para unir el avance.",parent=self);return
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
            self.store.apply(changes); self.input.delete('1.0','end');self.store.setting('draft',''); self.files=[]; self.keep.set(False); self.change_view('Recientes')
            for d in changes:
                if d.get('questions'):self.editor(d)
        self._processing_capture=True;self.run(work,done,on_error=self.show_capture);self.hide_capture(force=True)
    def attach(self):
        paths=filedialog.askopenfilenames(parent=self.capture_window)
        self.files.extend(paths); self.status.configure(text=f'{len(self.files)} adjuntos · se procesarán con la entrada')
    def paste_image(self):
        try:
            from PIL import ImageGrab
            img=ImageGrab.grabclipboard()
            if not hasattr(img,'save'):raise ValueError('El portapapeles no contiene una imagen.')
            path=Path(tempfile.gettempdir())/(str(uuid.uuid4())+'.png');img.save(path);self.files.append(str(path));self.tempfiles.append(str(path));self.status.configure(text='Captura agregada')
        except Exception as e:messagebox.showerror('Pegar captura',str(e),parent=self)
    def record(self):
        if self.recording or self.busy:return
        try:
            import sounddevice as sd
            self.chunks=[]
            self.recording=sd.RawInputStream(samplerate=16000,channels=1,dtype='int16',callback=lambda data,frames,time,status:self.chunks.append(bytes(data)))
            self.recording.start();self.status.configure(text='Grabando…');self.capture_status.configure(text='Grabando… elegí transcribir o ejecutar al terminar.');self.record_timer=self.after(3600000,lambda:self.stop(False))
        except Exception as e:self.recording=None;messagebox.showerror('Micrófono',str(e),parent=self)
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
        self.run(lambda:transcribe(path),done,on_error=self.show_capture)
    def delete(self):
        id=self.selected()
        if id:
            d=self.store.get(id);d['deleted']=not d.get('deleted');self.save([d])
    def meeting(self):
        if any(d.get('recurrence')=='tuesday' and d['status']!='Terminado' for d in self.store.items()):messagebox.showinfo('Reunión','Ya hay una reunión pendiente.',parent=self);return
        date=today()+dt.timedelta(days=(1-today().weekday())%7); d=fresh('Reunión semanal');d.update(recurrence='tuesday',owners=[PEOPLE[0]],planned=date.isoformat(),deadline=date.isoformat());self.save([d])
    def notify(self):
        if self.personal:return
        id=self.selected()
        if not id:return
        d=self.store.get(id);w=tk.Toplevel(self);w.withdraw();w.transient(self);w.title('Notificar · editar y copiar')
        box=tk.Text(w,wrap='word',bg=CARD,fg=FG,insertbackground=FG,font=('Segoe UI',12));box.pack(fill='both',expand=True)
        box.insert('1.0',f"{', '.join(d['owners']) or 'Equipo'}, ¿cómo vienen con esto?\n\n{d['title']}\n{d['summary']}\n\nPendiente: {', '.join(d.get('pending',[]))}\nFecha límite: {d['deadline']}")
        def copy_text():
            text=box.get('1.0','end').strip();self.clipboard_clear();self.clipboard_append(text)
            samples=self.store.setting('writing_samples') or [];self.store.setting('writing_samples',(samples+[text])[-20:]);w.destroy()
        ttk.Button(w,text='Copiar mensaje',command=copy_text).pack(pady=10)
        place_window(w,650,380,parent=self)
    def history(self):
        w=tk.Toplevel(self);w.withdraw();w.transient(self);w.title('Historial');box=tk.Text(w,bg=CARD,fg=FG,wrap='word');box.pack(fill='both',expand=True)
        for stamp,after,undone in self.store.db.execute('SELECT stamp,after,undone FROM history ORDER BY seq DESC LIMIT 100'):
            box.insert('end',stamp+(' · Deshecho' if undone else '')+'\n'+'\n'.join(d['title'] for d in json.loads(after))+'\n\n')
        box.configure(state='disabled');place_window(w,700,450,parent=self)
    def settings(self):
        if self.busy or self.recording:messagebox.showinfo('Esperá','Terminá el procesamiento o la grabación antes de cambiar los ajustes.',parent=self);return
        window=tk.Toplevel(self);window.withdraw();window.transient(self);window.title('Ajustes');window.minsize(480,360);window.configure(bg=BG)
        area=ScrollArea(window);area.pack(fill='both',expand=True);w=area.body
        ttk.Label(w,text='Tu nombre' if self.personal else 'Personas del equipo · una por línea').pack(pady=8)
        ttk.Label(w,text='Reemplazá cada nombre en su misma línea. Las tareas y el historial conservarán a la persona correspondiente.',wraplength=570,foreground=MUTED).pack(padx=12,pady=(0,8))
        roster=tk.Text(w,height=1 if self.personal else 5,bg=CARD,fg=FG,insertbackground=FG,font=('Segoe UI',11),padx=10,pady=8);roster.insert('1.0','\n'.join(PEOPLE));roster.pack(fill='x',padx=12)
        def save_people():
            names=[n.strip() for n in roster.get('1.0','end').splitlines() if n.strip()]
            if names==PEOPLE:return
            if self.personal and len(names)!=1:messagebox.showinfo('Proyecto personal','Este proyecto tiene una sola persona.',parent=window);return
            if self.busy or self.recording:messagebox.showinfo('Esperá','Terminá el procesamiento o la grabación antes de cambiar el equipo.',parent=window);return
            if any(isinstance(child,tk.Toplevel) and child!=window and child.state()!='withdrawn' for child in self.winfo_children()):
                messagebox.showinfo('Equipo','Cerrá las otras ventanas del programa antes de cambiar los nombres.',parent=window);return
            preview='\n'.join(f'{old} → {new}' for old,new in zip(PEOPLE,names))
            if not messagebox.askyesno('Confirmar equipo','Se actualizarán los nombres en las tareas y el historial:\n\n'+preview+'\n\n¿Guardar estos cambios?',parent=window):return
            try:
                mapping=self.store.rename_people(names)
            except Exception as error:messagebox.showerror('Equipo',str(error),parent=window);return
            PEOPLE[:]=names;ALIASES.clear();ALIASES.update(self.store.setting('aliases') or {})
            self.author.set(mapping.get(self.author.get(),PEOPLE[0]));self.filter_person.set(mapping.get(self.filter_person.get(),'Todos'))
            self.author_box.configure(values=PEOPLE);self.people_filter.configure(values=['Todos']+PEOPLE);self.refresh()
            try:self.store.backup()
            except Exception as error:
                messagebox.showwarning('Equipo guardado','Los nombres ya se actualizaron y hay una copia local previa. No se pudo crear el respaldo en la carpeta elegida:\n'+str(error),parent=window);return
            messagebox.showinfo('Equipo','Nombres actualizados. Se conservaron las tareas y el historial. No hace falta reiniciar.',parent=window)
        ttk.Button(w,text='Guardar equipo local',command=save_people).pack()
        ttk.Label(w,text='Modelo local instalado en Ollama').pack(pady=12);var=tk.StringVar(value=self.store.setting('model') or '');ttk.Entry(w,textvariable=var,width=45).pack()
        ttk.Label(w,text='La IA requiere Ollama en esta PC. No se conectan APIs pagas.\nLa transcripción descarga un modelo local la primera vez.',wraplength=590).pack(pady=12)
        ttk.Button(w,text='Guardar modelo',command=lambda:(self.store.setting('model',var.get().strip()),window.destroy())).pack()
        backup_label=ttk.Label(w,text='',wraplength=570,foreground=MUTED)
        def show_backup_folder():backup_label.configure(text='Carpeta actual: '+str(self.store.setting('backup_folder') or self.store.path.parent/'backups'))
        def backup_folder():
            path=filedialog.askdirectory(parent=window,title='Elegí una carpeta exclusiva para los respaldos de Animation Lover')
            if not path:return
            previous=self.store.setting('backup_folder')
            try:
                self.store.setting('backup_folder',path);created=self.store.backup()
            except Exception as error:
                with self.root_store.db:
                    if previous is None:self.root_store.db.execute("DELETE FROM settings WHERE key='backup_folder'")
                    else:self.root_store.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',('backup_folder',json.dumps(previous)))
                messagebox.showerror('Respaldo','No se pudo crear la copia. Se conserva la carpeta anterior.\n\n'+str(error),parent=window);return
            show_backup_folder();messagebox.showinfo('Respaldo creado','Se guardó una copia en:\n'+str(created)+'\n\nSi elegiste una carpeta sincronizada, Google Drive se encarga de subirla cuando esté activo y tenga conexión.',parent=window)
        ttk.Button(w,text='Carpeta de respaldo (puede ser Google Drive sincronizado)',command=backup_folder).pack(pady=12)
        backup_label.pack(padx=12);show_backup_folder()
        ttk.Label(w,text='Se conservan las últimas 30 copias de la base de datos. Usá una carpeta exclusiva. Los respaldos incluyen todos los proyectos y sus comprobantes financieros. Los proyectos adicionales se guardan en Proyectos; los adjuntos de tareas no se incluyen.',wraplength=570,foreground=MUTED).pack(padx=12,pady=8)
        ttk.Label(w,text='Contexto de este proyecto para la IA (opcional)').pack(pady=(12,4))
        context=tk.Text(w,height=4,wrap='word',bg=CARD,fg=FG,insertbackground=FG);context.insert('1.0',self.store.setting('project_context') or '');context.pack(fill='x',padx=12)
        ttk.Button(w,text='Guardar contexto',command=lambda:self.store.setting('project_context',context.get('1.0','end').strip())).pack(pady=6)
        ttk.Button(w,text='Importar configuración de proyecto',command=lambda:self.import_project(window)).pack(pady=10)
        ttk.Label(w,text=f'Datos de este proyecto: {self.store.path}',wraplength=600).pack()
        place_window(window,650,600,parent=self)
    def finance(self):
        from .finance_ui import FinanceView
        if self.finance_view is None:
            self.finance_view=FinanceView(self);self.finance_views[self.project_id]=self.finance_view
        self.content.grid_remove();self.finance_view.grid(row=1,column=1,sticky='nsew');self.finance_view.refresh();self.restyle_project()
        self.finance_button.set_active(True)
        for button in self.nav_buttons.values():button.set_active(False)
    def updates(self):
        if self.busy or self.recording:messagebox.showinfo('Esperá','Terminá el procesamiento o la grabación antes de actualizar.',parent=self);return
        import sys
        from .update_dialog import UpdateDialog
        root=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]
        UpdateDialog(self,self.root_store,__version__,root,app=self)
if __name__=='__main__':App().mainloop()
