"""Always-visible project tabs: one click selects the target workspace."""
import tkinter as tk
from tkinter import font as tkfont
from .widgets import WrapBar
from .theme import SHELL

def rounded(canvas,x,y,w,h,fill,outline,r=10):
    points=[x+r,y,x+w-r,y,x+w,y,x+w,y+r,x+w,y+h-r,x+w,y+h,x+w-r,y+h,x+r,y+h,x,y+h,x,y+h-r,x,y+r,x,y]
    return canvas.create_polygon(points,smooth=True,splinesteps=18,fill=fill,outline=outline,width=1)

def badge(name):
    if name[:3].isdigit():return name[:3]
    return ''.join(word[0] for word in name.split()[:2]).upper()

class ProjectTab(tk.Canvas):
    def __init__(self,parent,project,command):
        self.name_font=tkfont.Font(root=parent,family='Segoe UI',size=-15,weight='bold')
        width=max(125,min(260,self.name_font.measure(project['name'])+58))
        super().__init__(parent,width=width,height=36,bg=SHELL,highlightthickness=0,takefocus=True,cursor='hand2')
        self.project=project;self.command=command;self.active=False;self.hover=False;self.pressed=False
        self.bind('<Configure>',self.draw);self.bind('<Enter>',lambda e:self.over(True));self.bind('<Leave>',lambda e:self.over(False))
        self.bind('<Button-1>',lambda e:self.press());self.bind('<ButtonRelease-1>',self.release)
        self.bind('<Return>',lambda e:self.invoke());self.bind('<space>',lambda e:self.invoke())
        self.bind('<FocusIn>',self.draw);self.bind('<FocusOut>',self.draw)
    def over(self,value):self.hover=value;self.draw()
    def press(self):self.pressed=True;self.focus_set();self.draw()
    def release(self,event):
        pressed=self.pressed;self.pressed=False;self.draw()
        if pressed and 0<=event.x<=self.winfo_width() and 0<=event.y<=self.winfo_height():self.invoke()
    def invoke(self):self.command(self.project['id']);return 'break'
    def draw(self,event=None):
        self.delete('all');w=max(1,self.winfo_width());h=max(1,self.winfo_height());green=self.project['personal']
        accent='#a5e7bd' if green else '#c2c8ff'
        fill=('#2e5e43' if green else '#35436b') if self.active else ('#203d2e' if green else '#26304b') if self.hover else ('#142d21' if green else '#192034')
        border=('#7bb994' if green else '#8b9bd5') if self.active else ('#4b795c' if green else '#4b5879') if self.hover else ('#2d4b38' if green else '#303a53')
        top=1 if self.active else 4
        if self.active:rounded(self,1,4,w-2,h-5,'#07150e' if green else '#090e1c','#07150e' if green else '#090e1c')
        rounded(self,1,top,w-2,h-top-3,fill,border)
        if self.active:self.create_line(12,top+2,w-12,top+2,fill=accent,width=2)
        rounded(self,8,top+5,27,22,'#437454' if green and self.active else '#4a5d91' if self.active else fill,border,r=6)
        self.create_text(21.5,top+16,text=badge(self.project['name']),fill=accent if self.active or self.hover else '#70947e' if green else '#7b89a9',font=('Segoe UI',-10,'bold'))
        label=self.project['name']
        while label and self.name_font.measure(label)>w-49:label=label[:-1]
        if label!=self.project['name']:label=label[:-1]+'…'
        self.create_text(43,top+16,text=label,anchor='w',fill='#f1f8f4' if self.active else '#b7d1c0' if green and self.hover else '#c4cce1' if self.hover else '#789b85' if green else '#8e9bb8',font=self.name_font)

class ProjectTabs(WrapBar):
    def __init__(self,parent,projects,current,command):
        super().__init__(parent,style='Shell.TFrame')
        self.tabs={};self.command=command;self.refresh(projects,current)
    def refresh(self,projects,current):
        if list(self.tabs)!=[p['id'] for p in projects]:
            for tab in self.tabs.values():tab.destroy()
            self.tabs={};self.children_list.clear();self.hidden.clear()
            for project in projects:self.tabs[project['id']]=self.add(ProjectTab(self,project,self.command))
        for project in projects:
            tab=self.tabs[project['id']];tab.project=project;tab.active=project['id']==current;tab.draw()
        self.reflow()
    def redraw(self):
        for tab in self.tabs.values():tab.draw()
