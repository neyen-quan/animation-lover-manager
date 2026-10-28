import tkinter as tk
from tkinter import ttk,font as tkfont

class NavItem(tk.Canvas):
    """Compact navigation with a drawn icon, frosted surface and keyboard focus."""
    COLORS={'Hoy':'#b7baff','Todas':'#8bc9ef','Por persona':'#80d7c2','Recientes':'#e8c18b','Idea':'#f0d68c','Roadmap':'#c4b3f3','Nota':'#9fc6ed','Papelera':'#e6a9bc','Finanzas':'#a8d2b4'}
    def __init__(self,parent,text,key,command):
        super().__init__(parent,height=32,width=156,bg='#181b30',highlightthickness=0,takefocus=True,cursor='hand2')
        self.label=text;self.key=key;self.command=command;self.active=False;self.hover=False;self.pressed=False
        self.label_font=tkfont.Font(family='Segoe UI',size=-14,weight='bold')
        self.bind('<Configure>',self.draw)
        self.bind('<Enter>',lambda e:self.over(True));self.bind('<Leave>',lambda e:self.over(False))
        self.bind('<Button-1>',self.press);self.bind('<ButtonRelease-1>',self.release)
        self.bind('<Return>',lambda e:self.invoke());self.bind('<space>',lambda e:self.invoke())
        self.bind('<FocusIn>',self.draw);self.bind('<FocusOut>',self.draw)
    def set_active(self,value):
        self.active=value;self.draw()
    def over(self,value):self.hover=value;self.draw()
    def press(self,event):self.pressed=True;self.focus_set();self.draw()
    def release(self,event):
        pressed=self.pressed;self.pressed=False;self.draw()
        if pressed and 0<=event.x<=self.winfo_width() and 0<=event.y<=self.winfo_height():self.invoke()
    def invoke(self):self.command();return 'break'
    def draw(self,event=None):
        self.delete('all');w=max(1,self.winfo_width());h=self.winfo_height();r=7
        fill='#303d62' if self.active else '#29334c' if self.hover else '#20273c'
        if self.pressed:fill='#25304b'
        border='#7386c1' if self.active else '#4b5c7b' if self.hover else '#303b52'
        points=[r,1,w-r,1,w-1,1,w-1,r,w-1,h-r,w-1,h-1,w-r,h-1,r,h-1,1,h-1,1,h-r,1,r,1,1]
        self.create_polygon(points,smooth=True,splinesteps=12,fill=fill,outline=border)
        self.create_line(10,3,w-10,3,fill='#526282' if self.active or self.hover else '#39445c')
        if self.active:self.create_line(3,9,3,h-9,fill='#b2baff',width=3)
        color=self.COLORS.get(self.key,'#b7baff');x=15;y=h/2
        self.icon(x,y,color)
        label=self.label
        while label and self.label_font.measure(label)>w-48:label=label[:-1]
        if label!=self.label:label=label[:-1]+'…'
        self.create_text(40,y,text=label,anchor='w',font=self.label_font,fill='#f2f3fc' if self.active else '#cdd6eb')
        if self.focus_get()==self:self.create_rectangle(6,5,w-6,h-5,outline='#b6c0e4',dash=(2,3))
    def icon(self,x,y,c):
        def line(*v,**kw):self.create_line(*v,fill=c,width=1.5,capstyle='round',joinstyle='round',**kw)
        def rect(a,b,d,e):self.create_rectangle(a,b,d,e,outline=c,width=1.3)
        def oval(a,b,d,e,fill=''):self.create_oval(a,b,d,e,outline=c,fill=fill,width=1.3)
        if self.key=='Hoy':
            oval(x-4,y-4,x+4,y+4)
            for a,b in [(0,8),(8,0),(-8,0),(0,-8)]:line(x+a*.75,y+b*.75,x+a,y+b)
        elif self.key=='Todas':
            for a,b in [(-6,-6),(2,-6),(-6,2),(2,2)]:rect(x+a,y+b,x+a+5,y+b+5)
        elif self.key=='Por persona':
            oval(x-3,y-7,x+3,y-1);line(x-6,y+6,x-6,y+3,x-3,y,x+3,y,x+6,y+3,x+6,y+6)
            line(x+6,y-5,x+8,y-3,x+8,y+2)
        elif self.key=='Recientes':oval(x-7,y-7,x+7,y+7);line(x,y-4,x,y,x+4,y+2)
        elif self.key=='Idea':oval(x-5,y-7,x+5,y+3);line(x-3,y+4,x+3,y+4);line(x-2,y+7,x+2,y+7)
        elif self.key=='Roadmap':
            oval(x-8,y+3,x-4,y+7);oval(x+4,y-7,x+8,y-3);line(x-4,y+5,x+1,y+5,x+1,y-5,x+4,y-5)
        elif self.key=='Nota':
            rect(x-6,y-7,x+6,y+7)
            for d in [-3,1,5]:line(x-3,y+d,x+3,y+d)
        elif self.key=='Papelera':
            line(x-7,y-4,x+7,y-4);line(x-3,y-7,x+3,y-7);line(x-5,y-3,x-4,y+7,x+4,y+7,x+5,y-3)
            line(x-1,y-1,x-1,y+4);line(x+2,y-1,x+2,y+4)
        else:rect(x-7,y-5,x+7,y+6);rect(x+2,y-1,x+8,y+3)

class AutoScrollbar(ttk.Scrollbar):
    def set(self,first,last):
        if float(first)<=0.00001 and float(last)>=0.99999:
            if self.winfo_manager():self.grid_remove()
        elif not self.winfo_manager():self.grid()
        super().set(first,last)

class ScrollArea(ttk.Frame):
    """Contenido desplazable: controles accesibles aun con escala de Windows alta."""
    def __init__(self,parent,**kw):
        super().__init__(parent,**kw)
        self.canvas=tk.Canvas(self,bg='#181b30',highlightthickness=0)
        self.vbar=AutoScrollbar(self,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.canvas.grid(row=0,column=0,sticky='nsew');self.vbar.grid(row=0,column=1,sticky='ns')
        self.rowconfigure(0,weight=1);self.columnconfigure(0,weight=1)
        self.body=ttk.Frame(self.canvas);self.window=self.canvas.create_window(0,0,anchor='nw',window=self.body)
        self.body.bind('<Configure>',self.region)
        self.canvas.bind('<Configure>',self.resize)
        self.canvas.bind_all('<MouseWheel>',self.wheel,add='+')
    def resize(self,event):
        if int(float(self.canvas.itemcget(self.window,'width')))!=event.width:self.canvas.itemconfigure(self.window,width=event.width)
        self.region()
    def region(self,event=None):
        height=max(self.body.winfo_reqheight(),self.canvas.winfo_height())
        if int(float(self.canvas.itemcget(self.window,'height')))!=height:self.canvas.itemconfigure(self.window,height=height)
        bbox=self.canvas.bbox('all')
        current=tuple(map(int,self.canvas.cget('scrollregion').split())) if self.canvas.cget('scrollregion') else ()
        if bbox and current!=bbox:self.canvas.configure(scrollregion=bbox)
    def wheel(self,event):
        w=event.widget
        while w:
            if w==self.body:
                if self.body.winfo_reqheight()>self.canvas.winfo_height():self.canvas.yview_scroll(-int(event.delta/120),'units')
                return
            w=getattr(w,'master',None)

class WrapBar(ttk.Frame):
    """Flujo sin propagación de columnas: evita ciclos de negociación en Tk."""
    def __init__(self,parent,**kw):
        super().__init__(parent,height=42,**kw)
        self.children_list=[];self.inset=0;self.bind('<Configure>',self.reflow)
    def add(self,widget):
        self.children_list.append(widget);self.after_idle(self.reflow);return widget
    def reflow(self,event=None):
        if not self.winfo_exists():return
        width=max(1,self.winfo_width()-self.inset);x=self.inset;y=3+self.inset;line_height=0
        for w in self.children_list:
            needed=min(w.winfo_reqwidth(),width);height=w.winfo_reqheight()
            if x>self.inset and x+needed>width:y+=line_height+6;x=self.inset;line_height=0
            info=w.place_info()
            if int(info.get('x',-1))!=x or int(info.get('y',-1))!=y or int(info.get('width',-1))!=needed:
                w.place(x=x,y=y,width=needed,height=height)
            x+=needed+6;line_height=max(line_height,height)
        needed_height=y+line_height+3+self.inset
        if int(self.cget('height'))!=needed_height:self.configure(height=needed_height)
