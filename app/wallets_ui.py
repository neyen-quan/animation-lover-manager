"""Compact editable team wallets, kept entirely inside the finance workspace."""
import tkinter as tk
from tkinter import ttk,messagebox,filedialog
from .wallets import WalletBook,NETWORK,address
from .theme import MUTED
from .widgets import WrapBar


class WalletsView(ttk.Frame):
    def __init__(self,view):
        super().__init__(view)
        self.view=view;self.book=WalletBook(view.ledger.store);self.fields={};self.copies={};self.controls=[]
        self.columnconfigure(0,weight=1)
        self.heading=ttk.Label(self,text=NETWORK,font=('Segoe UI',-14,'bold'))
        self.heading.grid(row=0,column=0,sticky='w',pady=(2,8))
        self.rows=ttk.Frame(self);self.rows.grid(row=1,column=0,sticky='nsew');self.rowconfigure(1,weight=1)
        self.rows.columnconfigure(1,weight=1)
        footer=WrapBar(self);footer.grid(row=2,column=0,sticky='ew',pady=(8,0))
        self.import_button=footer.add(ttk.Button(footer,text='Cargar archivo de billeteras',command=self.import_file,style='Finance.TButton'))
        self.note=ttk.Label(self,text='Completá una dirección y tocá Guardar. Los campos vacíos quedan pendientes.',font=('Segoe UI',-11),foreground=MUTED,wraplength=500)
        self.note.grid(row=3,column=0,sticky='ew',pady=(5,0))
        self.bind('<Configure>',lambda e:self.note.configure(wraplength=max(160,e.width-6)))
        self.refresh()
    def refresh(self):
        people=self.book.people()
        if list(self.fields)!=people:
            for child in self.rows.winfo_children():child.destroy()
            self.fields={};self.copies={};self.controls=[]
            saved=self.book.values();drafts=self.book.drafts()
            for i,person in enumerate(people):
                self.rows.rowconfigure(i,weight=1)
                label=ttk.Label(self.rows,text=person,font=('Segoe UI',-13,'bold'))
                label.grid(row=i,column=0,sticky='w',padx=(0,8),pady=3)
                var=tk.StringVar(value=drafts.get(person,saved.get(person,'')));self.fields[person]=var
                field=ttk.Entry(self.rows,textvariable=var,font=('Consolas',-13),width=12)
                field.grid(row=i,column=1,sticky='ew',pady=3)
                copy=ttk.Button(self.rows,text='Copiar',command=lambda p=person:self.copy(p),style='Finance.TButton')
                copy.grid(row=i,column=2,padx=(6,0),pady=3);self.copies[person]=copy
                save=ttk.Button(self.rows,text='Guardar',command=lambda p=person:self.save(p),style='Finance.TButton')
                save.grid(row=i,column=3,padx=(5,0),pady=3)
                field.bind('<Return>',lambda e,p=person:self.save(p))
                var.trace_add('write',lambda *a,p=person:self.changed(p))
                self.controls.extend([label,field,copy,save])
        for p in people:self.copy_state(p)
    def copy_state(self,person):
        saved=self.book.values().get(person,'')
        enabled=bool(saved) and self.fields[person].get().strip()==saved
        self.copies[person].configure(state='normal' if enabled else 'disabled')
    def changed(self,person):
        self.book.draft(person,self.fields[person].get());self.copy_state(person)
    def save(self,person):
        try:
            value=address(self.fields[person].get());self.book.save({person:value});self.fields[person].set(value)
            text=self.book.backup_warning or ('Billetera de '+person+' guardada.' if value else 'Billetera de '+person+' pendiente de completar.')
            self.note.configure(text=text);self.view.app.status.configure(text=text)
            self.copy_state(person)
        except Exception as error:messagebox.showerror('Revisar billetera',str(error),parent=self.view.app)
    def copy(self,person):
        value=self.book.values().get(person,'')
        if not value or self.fields[person].get().strip()!=value:return
        self.clipboard_clear();self.clipboard_append(value)
        self.note.configure(text='Dirección de '+person+' copiada · '+NETWORK)
    def import_file(self):
        path=filedialog.askopenfilename(parent=self.view.app,title='Cargar billeteras del equipo',filetypes=[('Billeteras privadas','*.almwallets')])
        if not path:return
        try:
            values=self.book.read_import(path)
            preview='\n\n'.join(p+'\n'+v for p,v in values.items())
            if not messagebox.askyesno('Revisar billeteras',NETWORK+'\n\n'+preview+'\n\n¿Guardar estas billeteras?',parent=self.view.app):return
            self.book.save(values,replace=False)
            for p,value in values.items():self.fields[p].set(value)
            self.refresh();self.note.configure(text=self.book.backup_warning or 'Billeteras cargadas. Podés completar las demás a mano.')
        except Exception as error:messagebox.showerror('Cargar billeteras',str(error),parent=self.view.app)
