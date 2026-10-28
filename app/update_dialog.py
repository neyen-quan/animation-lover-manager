"""Interfaz compartida por el programa y la transición desde 0.1.0."""
import json, os, queue, sys, tempfile, threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from . import __version__
from .core import Store
from . import updater as u

class UpdateDialog(tk.Toplevel):
    def __init__(self,parent,store,installed,root,app=None,transition=False):
        super().__init__(parent);self.withdraw()
        from .theme import apply_theme
        if ttk.Style(self).theme_use()!='clam':apply_theme(parent)
        self.title('Actualizar programa');self.minsize(540,360)
        self.store=store;self.installed=installed;self.root_path=Path(root);self.app=app;self.transition=transition;self.info=None;self.q=queue.Queue();self.working=False
        self.channel=tk.StringVar(value=(f'https://github.com/neyen-quan/animation-lover-manager/releases/download/v{__version__}/latest.json' if transition else store.setting('update_channel') or u.CHANNEL))
        self.progress_text=tk.StringVar(value='Buscá una versión nueva en el canal de GitHub.')
        self.available=tk.StringVar(value='Disponible: sin consultar')
        from .widgets import ScrollArea,WrapBar
        self.area=ScrollArea(self);self.area.pack(fill='both',expand=True)
        body=ttk.Frame(self.area.body,padding=20);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Actualizaciones',font=('Segoe UI',18,'bold')).pack(anchor='w')
        ttk.Label(body,text='Instalada: '+installed).pack(anchor='w',pady=(10,0))
        ttk.Label(body,textvariable=self.available).pack(anchor='w',pady=(0,12))
        ttk.Label(body,text='Canal de GitHub').pack(anchor='w')
        ttk.Entry(body,textvariable=self.channel).pack(fill='x',pady=6)
        description=ttk.Label(body,textvariable=self.progress_text,wraplength=580);description.pack(fill='x',pady=12)
        body.bind('<Configure>',lambda e:description.configure(wraplength=max(200,e.width-40)))
        self.progress=ttk.Progressbar(body,mode='indeterminate');self.progress.pack(fill='x')
        row=WrapBar(body);row.pack(fill='x',pady=15)
        self.check_btn=row.add(ttk.Button(row,text='Buscar actualizaciones',command=self.check))
        self.install_btn=row.add(ttk.Button(row,text='Descargar e instalar',command=self.install,state='disabled'))
        self.local_btn=ttk.Button(body,text='Instalar ZIP local…',command=self.local);self.local_btn.pack(anchor='w')
        self.protocol('WM_DELETE_WINDOW',self.close)
        if parent.winfo_viewable():self.transient(parent)
        from .windowing import place_window
        place_window(self,680,440,parent=parent)
        self.grab_set();self._poll_job=self.after(100,self.poll)
    def destroy(self):
        if getattr(self,'_poll_job',None):
            self.after_cancel(self._poll_job);self._poll_job=None
        super().destroy()
    def close(self):
        if not self.working:self.destroy()
    def task(self,work,done):
        if self.working:return
        self.working=True;self.progress.start();self.check_btn.configure(state='disabled');self.local_btn.configure(state='disabled');self.install_btn.configure(state='disabled')
        def run():
            try:self.q.put(('done',done,work()))
            except Exception as e:self.q.put(('error',None,str(e)))
        threading.Thread(target=run,daemon=True).start()
    def poll(self):
        if not self.winfo_exists():return
        try:
            while True:
                kind,done,value=self.q.get_nowait()
                if kind=='progress':self.progress_text.set(value);continue
                self.working=False;self.progress.stop();self.check_btn.configure(state='normal');self.local_btn.configure(state='normal')
                if kind=='error':self.progress_text.set('No se aplicaron cambios.');messagebox.showerror('Actualización',value,parent=self)
                else:
                    try:done(value)
                    except Exception as e:messagebox.showerror('Actualización',str(e),parent=self)
        except queue.Empty:pass
        try:
            if self.winfo_exists():self._poll_job=self.after(100,self.poll)
        except tk.TclError:pass
    def check(self):
        channel=self.channel.get().strip()
        if not u.valid_url(channel) or not channel.endswith('/latest.json'):messagebox.showerror('Canal','Usá HTTPS de GitHub terminado en /latest.json.',parent=self);return
        if not self.transition:self.store.setting('update_channel',channel)
        self.progress_text.set('Consultando GitHub…')
        def done(info):
            self.info=info;self.available.set('Disponible: '+info['version'])
            if info['current']:self.progress_text.set('Ya tenés la última versión disponible.')
            else:
                kind='parche incremental' if info['asset'].get('from') else 'paquete completo compatible'
                self.progress_text.set('Disponible '+info['version']+' · '+kind+'. '+info.get('notes',''))
                self.install_btn.configure(state='normal')
        self.task(lambda:u.check(channel,self.installed),done)
    def install(self):
        info=self.info
        if not info or info.get('current'):return
        def work():
            folder=Path(self.store.path.parent)/'updates'/'downloads';folder.mkdir(parents=True,exist_ok=True)
            import uuid
            path=folder/(str(uuid.uuid4())+'.zip')
            last=[0]
            def progress(n,total):
                if n-last[0]>=1024**2:
                    self.q.put(('progress',None,f'Descargando {n//1024**2} MB'+(f' de {total//1024**2} MB' if total else '')+'…'));last[0]=n
            u.download(info['asset']['url'],path,progress=progress)
            m=u.validate_package(path,self.installed,info['asset']['sha256'],info['version'])
            return path,m,info['asset']['sha256']
        self.task(work,self.confirm)
    def local(self):
        path=filedialog.askopenfilename(parent=self,title='Paquete de actualización',filetypes=[('Paquete ZIP','*.zip')])
        if path:self.task(lambda:(Path(path),u.validate_package(path,self.installed),u.digest(path)),self.confirm)
    def confirm(self,result):
        path,m,sha=result
        if not messagebox.askyesno('Instalar actualización',f"Instalar {self.installed} → {m['to']}\n\nEl paquete ya está descargado y verificado. Se respaldarán los archivos reemplazados y se reiniciará el programa. Tus datos se conservan.\n\n¿Instalar ahora?",parent=self):return
        if not getattr(sys,'frozen',False):messagebox.showinfo('Desarrollo','La instalación se prueba desde el ejecutable de Windows.',parent=self);return
        if self.app and (self.app.busy or self.app.recording):messagebox.showinfo('Esperá','Terminá el procesamiento o la grabación antes de actualizar.',parent=self);return
        self.store.backup()
        data=self.store.path.parent
        def done(base):
            if self.app:self.app.save_draft()
            if self.transition:self.store.setting('update_channel',u.CHANNEL)
            self.store.db.close()
            (base/'go').write_text('go')
            self.master.destroy()
        self.task(lambda:u.prepare_job(path,self.root_path,self.installed,data,sha,m['to'],os.getpid()),done)

def bootstrap():
    parent=tk.Tk();parent.withdraw()
    messagebox.showinfo('Activar actualizaciones','Esta transición se hace una sola vez. Cerrá Animation Lover y seleccioná el AnimationLoverManager.exe que usás actualmente. Se conservará la misma ubicación y tus datos.')
    exe=filedialog.askopenfilename(title='Seleccioná tu programa instalado',filetypes=[('Animation Lover','AnimationLoverManager.exe')])
    if not exe:parent.destroy();return
    root=Path(exe).parent
    if Path(exe).name!=u.EXE:messagebox.showerror('Programa incorrecto','Seleccioná AnimationLoverManager.exe.');parent.destroy();return
    store=Store()
    try:installed=u.installed_version(root,'0.1.0')
    except Exception as e:messagebox.showerror('Instalación',str(e));parent.destroy();return
    dialog=UpdateDialog(parent,store,installed,root,transition=u.version(installed)<u.version(__version__))
    dialog.protocol('WM_DELETE_WINDOW',lambda:parent.destroy() if not dialog.working else None)
    dialog.after(300,dialog.check);parent.mainloop()
