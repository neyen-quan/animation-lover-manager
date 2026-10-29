"""Independent crypto and Kast details for each team member."""
import tkinter as tk
from tkinter import ttk,messagebox,filedialog
from .wallets import WalletBook,empty_profile
from .theme import MUTED
from .widgets import WrapBar


class WalletsView(ttk.Frame):
    def __init__(self,view):
        super().__init__(view)
        self.view=view;self.book=WalletBook(view.ledger.store);self.current=None;self.loading=False
        self.fields={key:tk.StringVar() for key in ('asset','network','address','kast')}
        self.copies={};self.controls=[];self.person_buttons={};self.columnconfigure(0,weight=1)
        ttk.Style(self).configure('Wallet.TEntry',padding=(6,4))
        self.people_bar=WrapBar(self);self.people_bar.grid(row=0,column=0,sticky='ew',pady=(0,4))
        self.panel=ttk.Frame(self);self.panel.grid(row=1,column=0,sticky='nsew');self.rowconfigure(1,weight=1);self.panel.columnconfigure(0,weight=1)
        label=ttk.Label(self.panel,text='Cripto',font=('Segoe UI',-14,'bold'));label.grid(row=0,column=0,sticky='w',pady=(0,4));self.controls.append(label)
        meta=ttk.Frame(self.panel);meta.grid(row=1,column=0,sticky='ew',pady=(0,4));meta.columnconfigure(0,weight=1);meta.columnconfigure(1,weight=2)
        for col,key,title in [(0,'asset','Moneda'),(1,'network','Red')]:
            label=ttk.Label(meta,text=title,font=('Segoe UI',-11),foreground=MUTED);label.grid(row=0,column=col,sticky='w')
            field=ttk.Entry(meta,textvariable=self.fields[key],font=('Segoe UI',-13),style='Wallet.TEntry',width=10)
            field.grid(row=1,column=col,sticky='ew',padx=(0,8 if col==0 else 0));self.controls.extend([label,field])
        line=ttk.Frame(self.panel);line.grid(row=2,column=0,sticky='ew');line.columnconfigure(0,weight=1)
        label=ttk.Label(line,text='Billetera',font=('Segoe UI',-11),foreground=MUTED);label.grid(row=0,column=0,sticky='w');self.controls.append(label)
        self.add_field(line,'address',1,'Copiar billetera')
        label=ttk.Label(self.panel,text='Kast · Usuario',font=('Segoe UI',-14,'bold'));label.grid(row=3,column=0,sticky='w',pady=(8,4));self.controls.append(label)
        line=ttk.Frame(self.panel);line.grid(row=4,column=0,sticky='ew');line.columnconfigure(0,weight=1);self.add_field(line,'kast',0,'Copiar usuario')
        footer=WrapBar(self);footer.grid(row=2,column=0,sticky='ew',pady=(6,0))
        self.save_button=footer.add(ttk.Button(footer,text='Guardar perfil',command=self.save,style='Finance.TButton'))
        self.import_button=footer.add(ttk.Button(footer,text='Cargar archivo de billeteras',command=self.import_file,style='Finance.TButton'))
        self.note=ttk.Label(self,text='Podés completar Cripto, Kast o ambos.',font=('Segoe UI',-11),foreground=MUTED,wraplength=500)
        self.note.grid(row=3,column=0,sticky='ew',pady=(4,0))
        self.bind('<Configure>',lambda e:self.note.configure(wraplength=max(160,e.width-6)))
        for var in self.fields.values():var.trace_add('write',self.changed)
        self.refresh()
    def add_field(self,parent,key,row,text):
        field=ttk.Entry(parent,textvariable=self.fields[key],font=('Consolas',-13),style='Wallet.TEntry',width=12)
        field.grid(row=row,column=0,sticky='ew')
        button=ttk.Button(parent,text=text,command=lambda:self.copy(key),style='Finance.TButton',padding=(6,4));button.grid(row=row,column=1,padx=(6,0))
        self.copies[key]=button;self.controls.extend([field,button])
        field.bind('<Return>',lambda e:self.save())
    def refresh(self):
        people=self.book.people()
        if list(self.person_buttons)!=people:
            for button in self.person_buttons.values():button.destroy()
            self.person_buttons={};self.people_bar.children_list.clear();self.people_bar.hidden.clear()
            for person in people:
                self.person_buttons[person]=self.people_bar.add(ttk.Button(self.people_bar,text=person,command=lambda p=person:self.select(p),style='Finance.Tab.TButton'))
        self.select(self.current if self.current in people else people[0])
    def select(self,person):
        self.current=person;self.loading=True
        try:
            value=self.book.drafts().get(person,self.book.values().get(person,empty_profile()))
            for key in ('asset','network','address'):self.fields[key].set(value['crypto'][key])
            self.fields['kast'].set(value['kast'])
            for name,button in self.person_buttons.items():button.configure(style='Finance.Active.Tab.TButton' if name==person else 'Finance.Tab.TButton')
        finally:self.loading=False
        self.copy_state()
    def raw(self,strip=False):
        result={'crypto':{key:self.fields[key].get() for key in ('asset','network','address')},'kast':self.fields['kast'].get()}
        if strip:
            result['crypto']={k:v.strip() for k,v in result['crypto'].items()};result['kast']=result['kast'].strip()
        return result
    def copy_state(self):
        saved=self.book.values().get(self.current,empty_profile());value=self.raw(strip=True)
        for key in self.copies:
            enabled=bool(saved['crypto']['address']) and saved['crypto']==value['crypto'] if key=='address' else bool(saved['kast']) and saved['kast']==value['kast']
            self.copies[key].configure(state='normal' if enabled else 'disabled')
    def changed(self,*args):
        if self.loading or self.current is None:return
        self.book.draft(self.current,self.raw());self.copy_state()
    def save(self):
        try:
            self.book.save({self.current:self.raw()});self.select(self.current)
            text=self.book.backup_warning or 'Perfil de '+self.current+' guardado.'
            self.note.configure(text=text);self.view.app.status.configure(text=text)
        except Exception as error:messagebox.showerror('Revisar perfil',str(error),parent=self.view.app)
    def copy(self,key):
        self.copy_state()
        if str(self.copies[key].cget('state'))=='disabled':return
        saved=self.book.values().get(self.current,empty_profile());value=saved['crypto']['address'] if key=='address' else saved['kast']
        self.clipboard_clear();self.clipboard_append(value)
        self.note.configure(text=('Billetera' if key=='address' else 'Usuario de Kast')+' de '+self.current+' copiado.')
    def import_file(self):
        path=filedialog.askopenfilename(parent=self.view.app,title='Cargar billeteras del equipo',filetypes=[('Billeteras privadas','*.almwallets')])
        if not path:return
        try:
            values=self.book.read_import(path);lines=[]
            for person,value in values.items():
                c=value['crypto'];lines.append(person+'\n'+(' · '.join([c['asset'],c['network'],c['address']]) if c['address'] else '')+('\nKast: '+value['kast'] if value['kast'] else ''))
            if not messagebox.askyesno('Revisar perfiles','\n\n'.join(lines)+'\n\n¿Guardar estos datos?',parent=self.view.app):return
            self.book.save(values,replace=False);self.refresh()
            self.note.configure(text=self.book.backup_warning or 'Datos cargados. Podés completar los demás perfiles a mano.')
        except Exception as error:messagebox.showerror('Cargar billeteras',str(error),parent=self.view.app)
