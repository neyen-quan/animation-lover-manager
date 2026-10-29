"""A project button and a centered chooser with direct, colored choices."""
import tkinter as tk
from tkinter import ttk,font as tkfont
from .theme import FG,MUTED,SHELL,project_color,themed_drawing,POPUP_BG
from .windowing import place_window

def rounded(canvas,x,y,w,h,fill,outline,r=12):
    points=[x+r,y,x+w-r,y,x+w,y,x+w,y+r,x+w,y+h-r,x+w,y+h,x+w-r,y+h,x+r,y+h,x,y+h,x,y+h-r,x,y+r,x,y]
    return canvas.create_polygon(points,smooth=True,splinesteps=18,fill=fill,outline=outline,width=1)

def badge(name):
    if name[:3].isdigit():return name[:3]
    return ''.join(word[0] for word in name.split()[:2]).upper()

class ProjectButton(tk.Canvas):
    def __init__(self,parent,variable,command):
        super().__init__(parent,width=260,height=42,bg=SHELL,highlightthickness=0,takefocus=True,cursor='hand2')
        self.variable=variable;self.command=command;self.hover=False;self.pressed=False
        self.name_font=tkfont.Font(family='Segoe UI',size=-17,weight='bold')
        self.trace=variable.trace_add('write',lambda *args:self.draw())
        self.bind('<Configure>',self.draw);self.bind('<Enter>',lambda e:self.over(True));self.bind('<Leave>',lambda e:self.over(False))
        self.bind('<Button-1>',lambda e:self.press());self.bind('<ButtonRelease-1>',self.release)
        self.bind('<Return>',lambda e:self.invoke());self.bind('<space>',lambda e:self.invoke())
        self.bind('<FocusIn>',self.draw);self.bind('<FocusOut>',self.draw)
    def over(self,value):self.hover=value;self.draw()
    def press(self):self.pressed=True;self.focus_set();self.draw()
    def release(self,event):
        pressed=self.pressed;self.pressed=False;self.draw()
        if pressed and 0<=event.x<=self.winfo_width() and 0<=event.y<=self.winfo_height():self.invoke()
    def invoke(self):self.command();return 'break'
    @themed_drawing
    def draw(self,event=None):
        self.delete('all');w=max(1,self.winfo_width());h=max(1,self.winfo_height())
        rounded(self,1,1,w-2,h-2,'#25304b' if self.pressed else '#29334c' if self.hover else '#20273c','#7386c1' if self.hover else '#4b5c7b')
        self.create_line(14,3,w-14,3,fill='#526282')
        rounded(self,8,7,32,h-14,'#303d62','#7386c1',r=8)
        self.create_text(24,h/2,text=badge(self.variable.get()),fill='#dfe4ff',font=('Segoe UI',-11,'bold'))
        label=self.variable.get()
        while label and self.name_font.measure(label)>w-86:label=label[:-1]
        if label!=self.variable.get():label=label[:-1]+'…'
        self.create_text(50,h/2,text=label,anchor='w',fill=FG,font=self.name_font)
        x=w-22;y=h/2
        # Two directions signal switching, rather than an ordinary list field.
        self.create_line(x-5,y-5,x+5,y-5,x+2,y-8,fill='#b2baff',width=1.5,joinstyle='round')
        self.create_line(x+5,y+5,x-5,y+5,x-2,y+8,fill='#b2baff',width=1.5,joinstyle='round')
    def destroy(self):
        self.variable.trace_remove('write',self.trace)
        super().destroy()

class ProjectOption(tk.Canvas):
    def __init__(self,parent,project,current,command):
        super().__init__(parent,width=300,height=152,bg=POPUP_BG,highlightthickness=0,takefocus=True,cursor='hand2')
        self.project=project;self.current=current;self.command=command;self.hover=False
        self.name_font=tkfont.Font(family='Segoe UI',size=-19,weight='bold')
        self.bind('<Configure>',self.draw);self.bind('<Enter>',lambda e:self.over(True));self.bind('<Leave>',lambda e:self.over(False))
        self.bind('<Button-1>',lambda e:self.invoke());self.bind('<Return>',lambda e:self.invoke());self.bind('<space>',lambda e:self.invoke())
        self.bind('<FocusIn>',self.draw);self.bind('<FocusOut>',self.draw)
    def over(self,value):self.hover=value;self.draw()
    def invoke(self):self.command(self.project['id']);return 'break'
    def draw(self,event=None):
        self.delete('all');w=max(1,self.winfo_width());h=max(1,self.winfo_height())
        green=self.project['personal']
        accent='#88dfad' if green else '#b4b8ff';border='#5c9c77' if green else '#757fbd'
        fill=('#254a36' if green else '#303957') if self.hover else ('#17382a' if green else '#202940')
        rounded(self,2,2,w-4,h-4,fill,accent if self.current or self.hover else border)
        self.create_line(18,5,w-18,5,fill=accent,width=2 if self.current else 1)
        rounded(self,16,17,48,35,'#2e5e43' if green else '#38446b',border,r=9)
        self.create_text(40,35,text=badge(self.project['name']),fill=accent,font=('Segoe UI',-14,'bold'))
        self.create_text(w-18,35,text='ACTUAL' if self.current else ('PERSONAL' if green else 'EQUIPO'),anchor='e',fill=accent,font=('Segoe UI',-10,'bold'))
        label=self.project['name']
        while label and self.name_font.measure(label)>w-34:label=label[:-1]
        if label!=self.project['name']:label=label[:-1]+'…'
        self.create_text(18,82,text=label,anchor='w',fill='#f0f7f4',font=self.name_font)
        self.create_text(18,117,text='Estás en este proyecto' if self.current else 'Cambiar a este proyecto  →',anchor='w',fill='#a8c8b5' if green else '#b2bbd4',font=('Segoe UI',-12))

class ProjectPicker(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app);self.withdraw();self.transient(app);self.title('Cambiar proyecto')
        self.app=app;self.cards={};self.columnconfigure(0,weight=1)
        body=ttk.Frame(self,padding=22);body.grid(row=0,column=0,sticky='nsew');body.columnconfigure(0,weight=1)
        ttk.Label(body,text='Elegí un proyecto',font=('Segoe UI',20,'bold')).grid(row=0,column=0,sticky='w',pady=(0,16))
        choices=ttk.Frame(body);choices.grid(row=1,column=0,sticky='ew')
        projects=app.projects.list()
        for i,p in enumerate(projects):
            choices.columnconfigure(i,weight=1,uniform='choice')
            card=ProjectOption(choices,p,p['id']==app.project_id,self.choose)
            card.grid(row=0,column=i,sticky='ew',padx=(0,12 if i<len(projects)-1 else 0));self.cards[p['id']]=card
        ttk.Button(body,text='Cerrar',command=self.destroy).grid(row=2,column=0,sticky='e',pady=(14,0))
        self.bind('<Escape>',lambda e:self.destroy());self.protocol('WM_DELETE_WINDOW',self.destroy)
        place_window(self,720,306,parent=app)
        self.grab_set();self.cards[app.project_id].focus_set()
    def choose(self,id):
        self.destroy();self.app.switch_project(id)
