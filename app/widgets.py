import tkinter as tk
from tkinter import ttk

class ScrollArea(ttk.Frame):
    """Contenido desplazable: controles accesibles aun con escala de Windows alta."""
    def __init__(self,parent,**kw):
        super().__init__(parent,**kw)
        self.canvas=tk.Canvas(self,bg='#10131d',highlightthickness=0)
        self.vbar=ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.canvas.grid(row=0,column=0,sticky='nsew');self.vbar.grid(row=0,column=1,sticky='ns')
        self.rowconfigure(0,weight=1);self.columnconfigure(0,weight=1)
        self.body=ttk.Frame(self.canvas);self.window=self.canvas.create_window(0,0,anchor='nw',window=self.body)
        self.body.bind('<Configure>',self.region)
        self.canvas.bind('<Configure>',self.resize)
        self.canvas.bind_all('<MouseWheel>',self.wheel,add='+')
    def resize(self,event):self.canvas.itemconfigure(self.window,width=event.width);self.region()
    def region(self,event=None):
        self.canvas.itemconfigure(self.window,height=max(self.body.winfo_reqheight(),self.canvas.winfo_height()))
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    def wheel(self,event):
        w=event.widget
        while w:
            if w==self.body:
                if self.body.winfo_reqheight()>self.canvas.winfo_height():self.canvas.yview_scroll(-int(event.delta/120),'units')
                return
            w=getattr(w,'master',None)

class WrapBar(ttk.Frame):
    def __init__(self,parent,**kw):
        super().__init__(parent,**kw);self.children_list=[];self.bind('<Configure>',self.reflow)
    def add(self,widget):self.children_list.append(widget);widget.grid(row=0,column=len(self.children_list)-1,padx=(0,6),pady=3,sticky='w');return widget
    def reflow(self,event=None):
        width=max(1,self.winfo_width());x=0;row=0;col=0
        for w in self.children_list:
            needed=w.winfo_reqwidth()+6
            if x and x+needed>width:row+=1;col=0;x=0
            w.grid(row=row,column=col,sticky='w',padx=(0,6),pady=3);col+=1;x+=needed
