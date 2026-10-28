import tkinter as tk
from tkinter import ttk

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
        self.children_list=[];self.bind('<Configure>',self.reflow)
    def add(self,widget):
        self.children_list.append(widget);self.after_idle(self.reflow);return widget
    def reflow(self,event=None):
        if not self.winfo_exists():return
        width=max(1,self.winfo_width());x=0;y=3;line_height=0
        for w in self.children_list:
            needed=min(w.winfo_reqwidth(),width);height=w.winfo_reqheight()
            if x and x+needed>width:y+=line_height+6;x=0;line_height=0
            info=w.place_info()
            if int(info.get('x',-1))!=x or int(info.get('y',-1))!=y or int(info.get('width',-1))!=needed:
                w.place(x=x,y=y,width=needed,height=height)
            x+=needed+6;line_height=max(line_height,height)
        needed_height=y+line_height+3
        if int(self.cget('height'))!=needed_height:self.configure(height=needed_height)
