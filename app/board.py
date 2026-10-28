"""Tablero nativo: tabla agrupada y tarjetas con selección y acciones al pasar el mouse."""
import datetime as dt
import hashlib
import tkinter as tk
from tkinter import ttk,font as tkfont
from .core import urgency
from .widgets import AutoScrollbar
from .theme import BG,CARD,FG,MUTED,ACCENT,LINE,SURFACE,HOVER

STATUS_COLORS={'Pendiente':'#fdab3d','En curso':'#7b83ff','Esperando':'#e89a59','Terminado':'#00c875'}
GROUPS=[('Vencidas','#f07188'),('En curso','#7b83ff'),('Pendientes','#fdab3d'),('En espera','#e89a59'),('Terminadas','#00c875')]
KIND_COLORS={'Tarea':'#8b98ff','Idea':'#b69aff','Roadmap':'#62c6d5','Nota':'#a1afc6'}
AVATARS=['#6c6cde','#338c9d','#a75d95','#997335','#547ca7']

def group_for(item):
    if urgency(item)==3:return 'Vencidas'
    return {'Pendiente':'Pendientes','En curso':'En curso','Esperando':'En espera','Terminado':'Terminadas'}.get(item.get('status'),'Pendientes')

def initials(name):
    words=str(name).split()
    if not words:return '?'
    return ((words[0][0]+words[-1][0]) if len(words)>1 else words[0][:2]).upper()

def avatar_color(name):return AVATARS[int(hashlib.sha256(str(name).encode()).hexdigest()[:8],16)%len(AVATARS)]

def due_label(value):
    try:
        date=dt.date.fromisoformat(value)
        month=['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][date.month-1]
        return f'{date.day} {month}'
    except (ValueError,TypeError):return 'Sin fecha'

class TaskBoard(ttk.Frame):
    def __init__(self,parent,on_open,on_new,on_action):
        super().__init__(parent,style='Panel.TFrame')
        self.on_open=on_open;self.on_new=on_new;self.on_action=on_action
        self.items=[];self.mode='table';self.group_mode='status';self.selected_id=None;self.hover_id=None;self.collapsed=set();self.hits=[];self.shapes={};self.menu_shapes={};self.tip=None;self.tip_job=None;self.layout_job=None
        self.canvas=tk.Canvas(self,bg=SURFACE,highlightthickness=0,height=300,takefocus=True)
        sy=AutoScrollbar(self,orient='vertical',command=self.scroll_y);sx=AutoScrollbar(self,orient='horizontal',command=self.scroll_x)
        self.canvas.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        self.canvas.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
        self.columnconfigure(0,weight=1);self.rowconfigure(0,weight=1)
        self.canvas.bind('<Configure>',self.schedule_render)
        self.canvas.bind('<Motion>',self.motion);self.canvas.bind('<Leave>',lambda e:self.clear_hover())
        self.canvas.bind('<Button-1>',self.click);self.canvas.bind('<Double-1>',self.double_click)
        self.canvas.bind('<Button-3>',self.context_click);self.canvas.bind('<Return>',lambda e:self.on_open())
        self.canvas.bind('<Up>',lambda e:self.navigate(-1));self.canvas.bind('<Down>',lambda e:self.navigate(1))
        self.canvas.bind('<MouseWheel>',self.wheel)
        self.canvas.bind('<Button-4>',lambda e:self.scroll_y('scroll',-1,'units'))
        self.canvas.bind('<Button-5>',lambda e:self.scroll_y('scroll',1,'units'))
    def s(self,n):return round(n*self.scale)
    def selection(self):return (self.selected_id,) if self.selected_id else ()
    def selection_set(self,id):
        if any(d['id']==id for d in self.items):self.selected_id=id;self.render()
    def set_items(self,items):
        self.items=list(items)
        if self.selected_id not in {d['id'] for d in items}:self.selected_id=None
        self.hover_id=None;self.hide_tip();self.render()
    def set_mode(self,mode):
        self.mode=mode if mode in ('table','cards') else 'table';self.canvas.xview_moveto(0);self.canvas.yview_moveto(0);self.render()
    def schedule_render(self,event=None):
        if self.layout_job:self.after_cancel(self.layout_job)
        self.layout_job=self.after(30,self.render)
    def round_rect(self,x,y,w,h,fill,outline='',radius=6,tags=()):
        r=min(self.s(radius),h/2,w/2)
        points=[x+r,y,x+w-r,y,x+w,y,x+w,y+r,x+w,y+h-r,x+w,y+h,x+w-r,y+h,x+r,y+h,x,y+h,x,y+h-r,x,y+r,x,y]
        return self.canvas.create_polygon(points,smooth=True,splinesteps=16,fill=fill,outline=outline or fill,width=1,tags=tags)
    def text(self,x,y,value,font='normal',fill=FG,anchor='w',**kw):return self.canvas.create_text(x,y,text=value,font=self.fonts[font],fill=fill,anchor=anchor,**kw)
    def fit(self,value,width,font='normal'):
        value=str(value);f=self.fonts[font]
        if f.measure(value)<=width:return value
        while value and f.measure(value+'…')>width:value=value[:-1]
        return value+'…'
    def lines(self,value,width,count=2,font='normal'):
        words=str(value).replace('\n',' ').split();lines=[];current=''
        for word in words:
            trial=(current+' '+word).strip()
            if current and self.fonts[font].measure(trial)>width:lines.append(current);current=word
            else:current=trial
        if current:lines.append(current)
        if len(lines)>count:lines=lines[:count];lines[-1]=self.fit(lines[-1]+' …',width,font)
        return '\n'.join(self.fit(line,width,font) for line in lines)
    def pill(self,x,y,label,color,width=None,dark=False):
        w=width or self.fonts['small'].measure(label)+self.s(18);h=self.s(24)
        self.round_rect(x,y,w,h,color if dark else CARD,outline=color if not dark else '',radius=5)
        self.text(x+w/2,y+h/2,label,'small',fill='#181b34' if color in ('#fdab3d','#00c875','#62c6d5','#e89a59') and dark else (FG if dark else color),anchor='center')
        return w
    def owners(self,x,y,names,width):
        names=names or []
        if not names:self.text(x,y,'Por asignar','small',MUTED);return
        size=self.s(24);step=self.s(19)
        for index,name in enumerate(names[:3]):
            left=x+step*index
            self.canvas.create_oval(left,y-size/2,left+size,y+size/2,fill=avatar_color(name),outline=SURFACE,width=2)
            self.text(left+size/2,y,initials(name),'avatar',anchor='center')
        used=size+step*(min(3,len(names))-1)+self.s(8)
        label=names[0] if len(names)==1 else f'{len(names)} personas'
        if width-used>self.s(25):self.text(x+used,y,self.fit(label,width-used,'small'),'small',MUTED)
    def render(self):
        self.layout_job=None
        if not self.winfo_exists():return
        self.scale=max(.85,float(self.tk.call('tk','scaling'))/1.333)
        self.fonts={key:tkfont.Font(family='Segoe UI',size=size,weight=weight) for key,size,weight in [('normal',10,'normal'),('small',9,'normal'),('bold',10,'bold'),('heading',12,'bold'),('avatar',8,'bold'),('empty',16,'bold')]}
        self.canvas.delete('all');self.hits=[];self.shapes={};self.menu_shapes={}
        if self.mode=='cards':self.draw_cards()
        else:self.draw_table()
        self.paint_selection()
    def add_hit(self,x,y,w,h,kind,value):self.hits.append((x,y,x+w,y+h,kind,value))
    def draw_table(self):
        pad=self.s(16);width=max(self.canvas.winfo_width()-2*pad,self.s(850));y=self.s(16)
        groups=[(name,color,[d for d in self.items if group_for(d)==name]) for name,color in GROUPS]
        if self.group_mode=='recent':groups=[('Actualizaciones recientes',ACCENT,self.items)]
        if not self.items:self.empty(width,pad);return
        for name,color,items in groups:
            if not items:continue
            self.text(pad,y+self.s(16),'›' if name in self.collapsed else '⌄','heading',color)
            self.text(pad+self.s(26),y+self.s(16),name,'heading',color)
            self.text(pad+self.s(26)+self.fonts['heading'].measure(name)+self.s(14),y+self.s(16),f'{len(items)} '+('elemento' if len(items)==1 else 'elementos'),'small',MUTED)
            self.add_hit(pad,y,width,self.s(38),'group',name);y+=self.s(42)
            if name in self.collapsed:continue
            fractions=[.34,.09,.17,.14,.13,.09,.04];edges=[pad]
            for f in fractions:edges.append(edges[-1]+width*f)
            self.round_rect(pad,y,width,self.s(34),'#24283f',radius=5)
            for index,label in enumerate(['Tarea','Tipo','Responsables','Estado','Fecha límite','Prioridad','']):self.text(edges[index]+self.s(14),y+self.s(17),label,'small',MUTED)
            y+=self.s(34)
            for d in items:
                h=self.s(46);id=d['id'];shape=self.canvas.create_rectangle(pad,y,pad+width,y+h,fill=SURFACE,outline=LINE,width=1)
                self.shapes[id]=shape;self.canvas.create_rectangle(pad,y,pad+self.s(4),y+h,fill=color,outline=color)
                cy=y+h/2
                self.text(edges[0]+self.s(18),cy,self.fit(d['title'],edges[1]-edges[0]-self.s(34)),'normal')
                if d.get('questions'):self.text(edges[1]-self.s(13),cy,'•','bold','#fdab3d')
                self.text(edges[1]+self.s(12),cy,d['kind'],'small',KIND_COLORS.get(d['kind'],MUTED))
                self.owners(edges[2]+self.s(10),cy,d.get('owners'),edges[3]-edges[2]-self.s(18))
                self.pill(edges[3]+self.s(7),cy-self.s(12),d['status'],STATUS_COLORS.get(d['status'],ACCENT),edges[4]-edges[3]-self.s(14),True)
                self.text(edges[4]+self.s(14),cy,due_label(d['deadline']),'small','#f07188' if urgency(d)==3 else MUTED)
                priority='Máxima' if urgency(d)==3 else d['priority'];pc={'Máxima':'#f07188','Alta':'#fdab3d','Media':'#aaa5ff','Baja':'#96a6c5'}.get(priority,MUTED)
                self.text(edges[5]+self.s(13),cy,'● '+priority,'small',pc)
                self.menu_shapes[id]=self.text(edges[6]+(edges[7]-edges[6])/2,cy,'···','bold',MUTED,anchor='center')
                self.add_hit(pad,y,width-self.s(32),h,'item',id);self.add_hit(pad+width-self.s(32),y,self.s(32),h,'menu',id)
                y+=h
            self.text(pad+self.s(18),y+self.s(17),'+  Añadir tarea','small',MUTED);self.add_hit(pad,y,width,self.s(34),'new',None)
            y+=self.s(62)
        self.canvas.configure(scrollregion=(0,0,pad*2+width,max(y,self.canvas.winfo_height())))
    def draw_cards(self):
        pad=self.s(16);gap=self.s(16);colw=max(self.s(220),int((self.canvas.winfo_width()-2*pad-3*gap)/4));statuses=['Pendiente','En curso','Esperando','Terminado'];bottom=self.s(270)
        for i,status in enumerate(statuses):
            x=pad+i*(colw+gap);color=STATUS_COLORS[status];items=[d for d in self.items if d['status']==status]
            self.round_rect(x,self.s(16),colw,self.s(40),CARD,radius=7)
            self.canvas.create_oval(x+self.s(13),self.s(31),x+self.s(21),self.s(39),fill=color,outline=color)
            self.text(x+self.s(30),self.s(36),status,'bold')
            self.text(x+colw-self.s(17),self.s(36),str(len(items)),'small',MUTED,anchor='e');y=self.s(70)
            for d in items:
                h=self.s(205);shape=self.round_rect(x,y,colw,h,CARD,outline=LINE,radius=10);self.shapes[d['id']]=shape
                self.text(x+self.s(16),y+self.s(22),d['kind'].upper(),'small',KIND_COLORS.get(d['kind'],MUTED))
                self.menu_shapes[d['id']]=self.text(x+colw-self.s(20),y+self.s(22),'···','bold',MUTED,anchor='center')
                title=self.lines(d['title'],colw-self.s(32),2,'bold')
                self.text(x+self.s(16),y+self.s(44),title,'bold',anchor='nw')
                self.text(x+self.s(16),y+self.s(91),self.lines(d.get('summary',''),colw-self.s(32),2),'small',MUTED,anchor='nw')
                priority='Máxima' if urgency(d)==3 else d['priority'];pc={'Máxima':'#f07188','Alta':'#fdab3d'}.get(priority,'#aaa5ff')
                self.pill(x+self.s(16),y+self.s(137),priority,pc)
                self.text(x+colw-self.s(15),y+self.s(149),due_label(d['deadline']),'small','#f07188' if urgency(d)==3 else MUTED,anchor='e')
                self.owners(x+self.s(16),y+self.s(184),d.get('owners'),colw-self.s(32))
                self.add_hit(x,y,colw,h,'item',d['id']);self.add_hit(x+colw-self.s(40),y,self.s(40),self.s(38),'menu',d['id'])
                y+=h+gap
            self.text(x+self.s(15),y+self.s(20),'+ Añadir tarea','small',MUTED);self.add_hit(x,y,colw,self.s(40),'new',None)
            bottom=max(bottom,y+self.s(56))
        self.canvas.configure(scrollregion=(0,0,pad*2+4*(colw+gap)-gap,bottom))
    def empty(self,width,pad):
        y=self.s(35)
        self.text(pad+self.s(14),y,'Tu tablero empieza acá','empty')
        self.text(pad+self.s(14),y+self.s(38),'Creá una tarjeta o soltá una idea para organizar lo que sigue.','normal',MUTED)
        self.round_rect(pad+self.s(14),y+self.s(70),self.s(155),self.s(38),ACCENT,radius=6)
        self.text(pad+self.s(91),y+self.s(89),'+ Nueva tarjeta','bold',anchor='center')
        self.add_hit(pad+self.s(14),y+self.s(70),self.s(155),self.s(38),'new',None)
        self.canvas.configure(scrollregion=(0,0,pad*2+width,max(self.s(250),self.canvas.winfo_height())))
    def hit(self,event):
        x=self.canvas.canvasx(event.x);y=self.canvas.canvasy(event.y)
        return next((h for h in reversed(self.hits) if h[0]<=x<=h[2] and h[1]<=y<=h[3]),None)
    def paint_selection(self):
        for id,shape in self.shapes.items():
            selected=id==self.selected_id;hover=id==self.hover_id
            self.canvas.itemconfigure(shape,fill='#303653' if selected else HOVER if hover else CARD if self.mode=='cards' else SURFACE,outline=ACCENT if selected or hover else LINE,width=2 if selected else 1)
            if id in self.menu_shapes:self.canvas.itemconfigure(self.menu_shapes[id],fill=MUTED if selected or hover else CARD if self.mode=='cards' else SURFACE)
    def motion(self,event):
        hit=self.hit(event);id=hit[5] if hit and hit[4] in ('item','menu') else None
        self.canvas.configure(cursor='hand2' if hit else '')
        if id!=self.hover_id:
            self.hover_id=id;self.paint_selection();self.hide_tip()
            if id:self.tip_job=self.after(650,lambda:self.show_tip(id,event.x_root,event.y_root))
    def clear_hover(self):self.hover_id=None;self.paint_selection();self.hide_tip()
    def hide_tip(self):
        if self.tip_job:self.after_cancel(self.tip_job);self.tip_job=None
        if self.tip:self.tip.destroy();self.tip=None
    def show_tip(self,id,x,y):
        self.tip_job=None
        d=next((d for d in self.items if d['id']==id),None)
        if not d or self.hover_id!=id:return
        tip=tk.Toplevel(self);tip.overrideredirect(True);tip.configure(bg=LINE);self.tip=tip
        body=tk.Frame(tip,bg='#303650',padx=14,pady=10);body.pack(padx=1,pady=1)
        tk.Label(body,text=d['title'],font=self.fonts['bold'],fg=FG,bg='#303650',wraplength=self.s(340),justify='left').pack(anchor='w')
        details=d.get('summary') or 'Abrí la tarjeta para ver o editar sus detalles.'
        tk.Label(body,text=details[:600],font=self.fonts['small'],fg=MUTED,bg='#303650',wraplength=self.s(340),justify='left').pack(anchor='w',pady=(5,0))
        tip.update_idletasks();tip.geometry(f'+{max(0,min(x+14,self.winfo_screenwidth()-tip.winfo_reqwidth()-15))}+{max(0,min(y+18,self.winfo_screenheight()-tip.winfo_reqheight()-40))}')
    def click(self,event):
        self.hide_tip();self.canvas.focus_set();hit=self.hit(event)
        if not hit:self.selected_id=None;self.paint_selection();return
        kind,value=hit[4:]
        if kind=='group':
            if value in self.collapsed:self.collapsed.remove(value)
            else:self.collapsed.add(value)
            self.render()
        elif kind=='new':self.on_new()
        else:
            self.selected_id=value;self.paint_selection()
            if kind=='menu':self.menu(event.x_root,event.y_root)
            elif self.mode=='cards':self.on_open()
    def double_click(self,event):
        hit=self.hit(event)
        if hit and hit[4]=='item' and self.mode=='table':self.selected_id=hit[5];self.on_open()
    def context_click(self,event):
        self.hide_tip();hit=self.hit(event)
        if hit and hit[4] in ('item','menu'):self.selected_id=hit[5];self.paint_selection();self.menu(event.x_root,event.y_root)
    def menu(self,x,y):
        menu=tk.Menu(self,tearoff=False,bg=CARD,fg=FG,activebackground=HOVER,activeforeground=FG,font=('Segoe UI',10),bd=0)
        selected=next((d for d in self.items if d['id']==self.selected_id),{})
        delete_label='Restaurar tarjeta' if selected.get('deleted') else 'Eliminar tarjeta'
        for label,action in [('Abrir tarjeta','open'),('Preparar mensaje','notify'),(delete_label,'delete')]:menu.add_command(label=label,command=lambda a=action:self.on_action(a))
        try:menu.tk_popup(x,y)
        finally:menu.grab_release()
    def navigate(self,direction):
        ids=[d['id'] for d in self.items]
        if not ids:return
        index=ids.index(self.selected_id) if self.selected_id in ids else (-1 if direction>0 else 0)
        self.selected_id=ids[(index+direction)%len(ids)];self.paint_selection()
        hit=next((h for h in self.hits if h[4]=='item' and h[5]==self.selected_id),None)
        if hit:
            region=self.canvas.bbox('all')
            if region:self.canvas.yview_moveto(max(0,hit[1]-self.s(50))/max(1,region[3]))
        return 'break'
    def wheel(self,event):
        self.hide_tip()
        if event.state&1:self.canvas.xview_scroll(-int(event.delta/120),'units')
        else:self.canvas.yview_scroll(-int(event.delta/120),'units')
        return 'break'
    def scroll_y(self,*args):self.hide_tip();self.canvas.yview(*args)
    def scroll_x(self,*args):self.hide_tip();self.canvas.xview(*args)
    def destroy(self):
        self.hide_tip()
        if self.layout_job:self.after_cancel(self.layout_job)
        super().destroy()
