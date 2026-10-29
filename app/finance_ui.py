"""Finance workspace, keeping the task workspace and its capture independent."""
import copy
import datetime as dt
import json
import os
import tempfile
import uuid
import wave
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from .finance import Finance, KINDS, PLATFORMS, entry, cents, usd, totals, outstanding
from .theme import BG, CARD, FG, MUTED, ACCENT, SURFACE, LINE, apply_popup_theme
from .widgets import WrapBar, ScrollArea
from .windowing import place_window

class FinanceView(ttk.Frame):
    def __init__(self, app):
        super().__init__(app, padding=(22,16,24,12))
        self.app = app; self.ledger = Finance(app.store)
        self.columnconfigure(0, weight=1); self.rowconfigure(5, weight=1)
        self.section = 'Resumen'; self.page = 0; self.month = tk.StringVar(value='Todos')
        self.query = tk.StringVar(); self.scope = tk.StringVar(value='Todos'); self.selected_id = None
        ttk.Label(self, text='Finanzas', font=('Segoe UI',25,'bold')).grid(row=0, column=0, sticky='w')
        self.subtitle = ttk.Label(self, foreground=MUTED)
        self.subtitle.grid(row=1, column=0, sticky='ew', pady=(4,10))
        self.metric_frame = tk.Canvas(self, height=86, bg=BG, highlightthickness=0)
        self.metric_frame.grid(row=2, column=0, sticky='ew', pady=(0,8))
        self.metric_frame.bind('<Configure>', lambda e:self.draw_metrics())
        tabs = WrapBar(self); self.tab_bar=tabs; tabs.grid(row=3,column=0,sticky='ew',pady=(0,5)); self.tabs={}
        for label in ['Resumen','Movimientos','Por persona','Insights mensuales']:
            self.tabs[label] = tabs.add(ttk.Button(tabs,text=label,command=lambda v=label:self.show(v)))
        tools = WrapBar(self); self.tools=tools; tools.grid(row=4,column=0,sticky='ew',pady=(0,7))
        for label, command in [('+ Registrar', self.capture), ('+ Gasto', lambda:self.capture('Gasto')),
                               ('+ Retiro', lambda:self.capture('Retiro')), ('+ Reintegro', lambda:self.capture('Reintegro')),
                               ('+ Reparto', lambda:self.capture('Reparto'))]:
            tools.add(ttk.Button(tools, text=label, command=command, style='Accent.TButton' if label=='+ Registrar' else 'TButton'))
        self.body=ttk.Frame(self);self.body.grid(row=5,column=0,sticky='nsew');self.body.rowconfigure(2,weight=1);self.body.columnconfigure(0,weight=1)
        filters=WrapBar(self.body);filters.grid(row=0,column=0,sticky='ew')
        filters.add(ttk.Label(filters,text='Mes'))
        self.month_box=filters.add(ttk.Combobox(filters,textvariable=self.month,state='readonly',width=9));self.month_box.bind('<<ComboboxSelected>>',lambda e:self.reload())
        filters.add(ttk.Entry(filters,textvariable=self.query,width=18))
        self.scope_box=filters.add(ttk.Combobox(filters,textvariable=self.scope,values=['Todos']+KINDS+['Anulados'],state='readonly',width=13));self.scope_box.bind('<<ComboboxSelected>>',lambda e:self.reload())
        self.chart=tk.Canvas(self.body,height=100,bg=SURFACE,highlightthickness=1,highlightbackground=LINE)
        self.chart.grid(row=1,column=0,sticky='ew',pady=7);self.chart.bind('<Configure>',lambda e:self.draw_chart())
        style=ttk.Style(self);style.configure('Finance.Treeview',background=SURFACE,fieldbackground=SURFACE,foreground=FG,rowheight=30,borderwidth=0,bordercolor=LINE,lightcolor=LINE,darkcolor=LINE,font=('Segoe UI',10))
        style.configure('Finance.Treeview.Heading',background=CARD,foreground=FG,font=('Segoe UI',10,'bold'),padding=7,bordercolor=LINE,lightcolor=LINE,darkcolor=LINE,relief='flat')
        style.map('Finance.Treeview',background=[('selected','#3b477a')],foreground=[('selected','#ffffff')])
        self.table=ttk.Treeview(self.body,show='headings',style='Finance.Treeview',selectmode='browse',height=3)
        self.table.grid(row=2,column=0,sticky='nsew');self.table.bind('<Double-1>',lambda e:self.open_selected(quick=True))
        self.table.bind('<Return>',lambda e:self.open_selected(quick=True));self.table.bind('<Configure>',self.resize_table)
        # Paging owns navigation; wheel must not reveal an additional scroll viewport.
        for event in ('<MouseWheel>','<Button-4>','<Button-5>'):self.table.bind(event,lambda e:'break')
        self.table.tag_configure('pending',foreground='#fdc56f');self.table.tag_configure('void',foreground=MUTED)
        bottom=WrapBar(self);self.bottom=bottom;bottom.grid(row=6,column=0,sticky='ew',pady=(7,0))
        self.reimburse_button=bottom.add(ttk.Button(bottom,text='Reintegrar',command=self.reimburse_selected))
        self.open_button=bottom.add(ttk.Button(bottom,text='Abrir / editar',command=self.open_selected))
        bottom.add(ttk.Button(bottom,text='Anterior',command=lambda:self.turn(-1)))
        self.page_label=bottom.add(ttk.Label(bottom,text=''))
        bottom.add(ttk.Button(bottom,text='Siguiente',command=lambda:self.turn(1)))
        bottom.add(ttk.Button(bottom,text='Más opciones',command=self.options))
        self.query.trace_add('write',lambda *a:self.reload())
        self.composer=None;self.page_size=5;self.rows=[];self.display_rows=[];self.refresh()
        self.bind('<Configure>',self.fit_workspace)
        style.configure('Finance.TButton',font=('Segoe UI',-13,'bold'),padding=(8,6))
        style.configure('Finance.Accent.TButton',font=('Segoe UI',-13,'bold'),padding=(8,6),background=ACCENT,foreground='white')
        def compact(parent):
            for child in parent.winfo_children():
                if isinstance(child,ttk.Button) and child not in self.tabs.values():child.configure(style='Finance.Accent.TButton' if 'Accent.' in str(child.cget('style')) else 'Finance.TButton')
                compact(child)
        compact(self)

    def fit_workspace(self,event):
        if event.widget is not self:return
        if event.height<570:self.chart.grid_remove()
        else:self.chart.grid()
        for button in self.tabs.values():button.configure(padding=(8,6))

    def show(self, section):
        if not self.leave_capture():return
        self.section=section;self.page=0;self.refresh()
    def reload(self):self.page=0;self.refresh()
    def turn(self,delta):self.page=max(0,min(self.pages-1,self.page+delta));self.render_table()
    def resize_table(self,event):
        size=max(1,(event.height-36)//30)
        if size != self.page_size:self.page_size=size;self.render_table()
    def refresh(self):
        self.rows=self.ledger.rows();self.balance=totals(self.rows);self.claims=outstanding(self.rows)
        months=sorted({d['date'][:7] for d in self.rows}|{d['period'] for d in self.rows if d['kind']=='Insight'},reverse=True)
        self.month_box.configure(values=['Todos']+months)
        for key,button in self.tabs.items():button.configure(style='Active.Tab.TButton' if key==self.section else 'Tab.TButton',padding=(8,6))
        prev=(dt.date.today().replace(day=1)-dt.timedelta(days=1)).strftime('%Y-%m')
        missing=[p for p in PLATFORMS if not any(d['kind']=='Insight' and d['period']==prev and d['platform']==p and not d['void'] for d in self.rows)]
        self.subtitle.configure(text=('Insights '+prev+' pendientes: '+', '.join(missing)) if dt.date.today().day==1 and missing else 'USD · Caja del negocio, separada de tu dinero personal')
        self.filtered=[d for d in self.rows if (self.month.get()=='Todos' or (d['period'] if d['kind']=='Insight' else d['date'][:7])==self.month.get())]
        self.draw_metrics();self.draw_chart();self.render_table()

    def draw_metrics(self):
        if not hasattr(self,'balance'):return
        c=self.metric_frame;c.delete('all');w=max(1,c.winfo_width());t=self.balance
        metrics=[('CAJA DISPONIBLE',t['cash'],'#aab8ff'),('POR REINTEGRAR',t['debt_total'],'#fdc56f'),('LIBRE TRAS REINTEGROS',t['free'],'#75ddc3')]
        for i,(label,n,color) in enumerate(metrics):
            x=i*w/3+2;r=(i+1)*w/3-8
            c.create_rectangle(x,1,r,82,fill='#232c43',outline='#46516e');c.create_line(x+12,3,r-12,3,fill=color,width=2)
            c.create_text(x+12,18,text=label,anchor='w',fill=color,font=('Segoe UI',-10,'bold'))
            c.create_text(x+12,43,text=usd(n),anchor='w',fill=FG,font=('Segoe UI',-22,'bold'))
            detail=('Incluye en tránsito: '+usd(t['anticipated'])) if i==0 else ('Deudas con el equipo' if i==1 else 'Saldo global, sin filtro mensual')
            c.create_text(x+12,66,text=detail,anchor='w',fill=MUTED,font=('Segoe UI',-10))

    def draw_chart(self):
        if not hasattr(self,'filtered'):return
        c=self.chart;c.delete('all');w=max(100,c.winfo_width());t=totals(self.filtered)
        if self.section=='Insights mensuales':
            data=[(p,sum(d['amount'] for d in self.filtered if d['kind']=='Insight' and not d['void'] and d['platform']==p)) for p in PLATFORMS]
            title='Ingresos informados · Insights no modifican la caja'
        elif self.section=='Por persona':
            data=[(p,self.balance['debt'].get(p,0)) for p in self.ledger.people()];title='Pendiente de devolver · Saldo global'
        else:
            data=[('Gastos',t['expenses']),('Comisiones',t['fees']),('Reintegros',t['reimbursements']),('Repartos',t['distributions'])];title='Salidas registradas · '+self.month.get()
        c.create_text(12,15,text=title,anchor='w',fill=MUTED,font=('Segoe UI',-11,'bold'))
        maximum=max([n for _,n in data]+[1]);colors=['#8b96ff','#e4b264','#61c6ac','#b19bdb','#72bdd9']
        for i,(label,n) in enumerate(data):
            slot=w/max(1,len(data));x=i*slot+12
            c.create_text(x,36,text=label,anchor='w',fill=FG,font=('Segoe UI',-11,'bold'))
            c.create_rectangle(x,49,x+max(1,(slot-26)*n/maximum),58,fill=colors[i%5],outline='')
            c.create_text(x,77,text=usd(n),anchor='w',fill=colors[i%5],font=('Segoe UI',-13,'bold'))

    def render_table(self):
        if not hasattr(self,'filtered'):return
        selected=self.table.selection();keep=selected[0] if selected else None
        self.table.delete(*self.table.get_children())
        if self.section=='Por persona':
            cols=[('Persona',2),('Adelantos pendientes',2),('Repartos pagados',2)]
            self.display_rows=[(p,(p,usd(self.balance['debt'].get(p,0)),usd(self.balance['paid'].get(p,0))),()) for p in self.ledger.people()]
        elif self.section=='Insights mensuales':
            cols=[('Mes',1),('Plataforma',1),('Ingresos USD',1),('Suscriptores',1),('Notas',3)]
            self.display_rows=[(d['id'],(d['period'],d['platform'],usd(d['amount']),d['subscribers'] if d['subscribers'] is not None else '—',d['description']),()) for d in sorted(self.filtered,key=lambda d:d['period'],reverse=True) if d['kind']=='Insight' and not d['void']]
        else:
            cols=[('Fecha',1),('Tipo',1),('Concepto',3),('Origen / persona',1.5),('USD',1),('Estado',1.5)]
            candidates=[d for d in self.filtered if d['kind']!='Insight' and (d['void'] if self.scope.get()=='Anulados' else not d['void'])]
            if self.scope.get() in KINDS:candidates=[d for d in candidates if d['kind']==self.scope.get()]
            if self.query.get():candidates=[d for d in candidates if self.query.get().casefold() in json.dumps(d,ensure_ascii=False).casefold()]
            self.display_rows=[]
            for d in sorted(candidates,key=lambda d:(d['date'],d['id']),reverse=True):
                state='Anulado' if d['void'] else ('Recibido' if d['received'] else 'En tránsito · en caja' if d['include_pending'] else 'Pendiente de ingreso') if d['kind']=='Retiro' else d['funding'] if d['kind']=='Gasto' else 'Registrado'
                if d['id'] in self.claims:
                    remaining=self.claims[d['id']]['remaining']
                    state=('Por reintegrar '+usd(remaining)) if remaining else 'Reintegrado / compensado'
                self.display_rows.append((d['id'],(d['date'],d['kind'],d['description'],d['platform'] or d['person'],usd(d['amount']),state),('void',) if d['void'] else ('pending',) if d['kind']=='Retiro' and not d['received'] else ()))
        self.table.configure(columns=[x[0] for x in cols])
        width=max(400,self.table.winfo_width()-4);weight=sum(x[1] for x in cols)
        for label,n in cols:self.table.heading(label,text=label);self.table.column(label,width=int(width*n/weight),minwidth=30,stretch=True,anchor='w')
        self.pages=max(1,(len(self.display_rows)+self.page_size-1)//self.page_size);self.page=min(self.page,self.pages-1)
        for id,values,tags in self.display_rows[self.page*self.page_size:(self.page+1)*self.page_size]:self.table.insert('', 'end', iid=id, values=values,tags=tags)
        if keep and self.table.exists(keep):self.table.selection_set(keep)
        self.page_label.configure(text=f'{self.page+1} / {self.pages} · {len(self.display_rows)} registros')
        self.open_button.configure(text='+ Cargar insights' if self.section=='Insights mensuales' and not self.display_rows else 'Abrir / editar')

    def open_selected(self,quick=False):
        selection=self.table.selection()
        if self.section=='Por persona':
            if selection:
                self.quick_reimbursement(person=selection[0])
        elif selection:
            d=self.ledger.get(selection[0])
            if quick and d['id'] in self.claims:self.quick_reimbursement(source_id=d['id'])
            else:self.edit(d)
        elif self.section=='Insights mensuales':self.capture('Insight')

    def report_saved(self):
        self.refresh();self.app.status.configure(text=self.ledger.backup_warning or 'Finanzas guardadas · Comprobantes conservados')
        if self.ledger.backup_warning:messagebox.showwarning('Respaldo pendiente',self.ledger.backup_warning,parent=self.app)

    def options(self):
        w=tk.Toplevel(self.app);w.title('Finanzas · Opciones')
        body=ttk.Frame(w,padding=22);body.pack(fill='both',expand=True)
        def do(fn):w.destroy();fn()
        for label,fn in [('Cargar insights mensuales',lambda:self.capture('Insight')),('Importar punto de partida',self.import_start),('Categorías de gastos',self.categories),('Gastos por categoría',self.category_report),('Historial de cambios',self.history),('Pago entre integrantes',lambda:self.edit(entry('Traspaso personal'))),('Respaldar ahora',self.backup)]:
            ttk.Button(body,text=label,command=lambda f=fn:do(f)).pack(fill='x',pady=4)
        place_window(w,500,460,parent=self.app)

    def backup(self):
        try:
            p=self.app.store.backup();messagebox.showinfo('Respaldo completo','Se guardó la base y los comprobantes de Finanzas.\n'+str(p.parent),parent=self.app)
        except Exception as e:messagebox.showerror('No se pudo respaldar',str(e),parent=self.app)

    def categories(self):
        w=tk.Toplevel(self.app);w.title('Categorías de gastos');f=ttk.Frame(w,padding=22);f.pack(fill='both',expand=True)
        old=tk.StringVar(value=self.ledger.categories()[0]);ttk.Combobox(f,textvariable=old,values=self.ledger.categories(),state='readonly').pack(fill='x',pady=8)
        new=tk.StringVar();ttk.Entry(f,textvariable=new).pack(fill='x',pady=8)
        def save(rename):
            try:self.ledger.rename_category(old.get() if rename else None,new.get());w.destroy();self.refresh()
            except Exception as e:messagebox.showerror('Categoría',str(e),parent=w)
        ttk.Button(f,text='Renombrar seleccionada',command=lambda:save(True)).pack(fill='x',pady=6)
        ttk.Button(f,text='Agregar nueva',command=lambda:save(False)).pack(fill='x')
        place_window(w,470,300,parent=self.app)

    def category_report(self):
        w=tk.Toplevel(self.app);w.title('Gastos por categoría')
        area=ScrollArea(w);area.pack(fill='both',expand=True);body=ttk.Frame(area.body,padding=22);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Gastos · '+self.month.get(),font=('Segoe UI',18,'bold')).pack(anchor='w',pady=(0,15))
        t=totals(self.filtered)
        for category,amount in sorted(t['categories'].items(),key=lambda pair:-pair[1]):
            ttk.Label(body,text=category+'   ·   '+usd(amount)).pack(anchor='w',pady=6)
        ttk.Separator(body).pack(fill='x',pady=12)
        ttk.Label(body,text='Gasto operativo total: '+usd(t['expenses']),font=('Segoe UI',12,'bold')).pack(anchor='w')
        ttk.Label(body,text='Comisiones de retiros: '+usd(t['fees']),foreground=MUTED).pack(anchor='w',pady=6)
        place_window(w,540,430,parent=self.app)

    def history(self):
        w=tk.Toplevel(self.app);w.title('Finanzas · Historial');text=tk.Text(w,wrap='word');text.pack(fill='both',expand=True)
        for stamp,before,after in self.ledger.db.execute('SELECT stamp,before,after FROM finance_history ORDER BY seq DESC LIMIT 100'):
            text.insert('end',stamp+'\nAntes:\n'+json.dumps(json.loads(before),ensure_ascii=False,indent=2)+'\nDespués:\n'+json.dumps(json.loads(after),ensure_ascii=False,indent=2)+'\n\n')
        text.configure(state='disabled');place_window(w,800,600,parent=self.app)

    def import_start(self):
        path=filedialog.askopenfilename(parent=self.app,title='Importar punto de partida privado',filetypes=[('Datos de Finanzas','*.almfinance *.zip')])
        if not path:return
        try:
            rows=self.ledger.read_import(path);t=totals(rows)
            msg=f"{len(rows)} movimientos y sus comprobantes.\nCaja: {usd(t['cash'])}\nIncluido en tránsito: {usd(t['anticipated'])}\nPor reintegrar: {usd(t['debt_total'])}\nLibre tras reintegros: {usd(t['free'])}\n\n¿Importar este punto de partida?"
            if messagebox.askyesno('Revisar punto de partida',msg,parent=self.app):self.ledger.save(rows);self.report_saved()
        except Exception as e:messagebox.showerror('Importar',str(e),parent=self.app)

    def edit(self,data,paths=None,after_save=None):
        if not data:return
        d=copy.deepcopy(data);w=tk.Toplevel(self.app);w.title('Finanzas · Revisar movimiento');w.transient(self.app)
        footer=WrapBar(w);footer.pack(side='bottom',fill='x',padx=18,pady=12)
        area=ScrollArea(w);area.pack(fill='both',expand=True);body=ttk.Frame(area.body,padding=20);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Revisar movimiento',font=('Segoe UI',18,'bold')).pack(anchor='w',pady=(0,10))
        fields={};widgets={};frames={};paths=list(paths or [])
        def field(key,label,values=None):
            f=ttk.Frame(body);f.pack(fill='x',pady=4);f.columnconfigure(1,weight=1);frames[key]=f
            ttk.Label(f,text=label,width=23).grid(row=0,column=0,sticky='w')
            value=d.get(key,'')
            if key in ('amount','gross','fee'):value=f'{value/100:.2f}'
            if value is None:value=''
            fields[key]=tk.StringVar(value=value)
            widget=ttk.Combobox(f,textvariable=fields[key],values=values,state='readonly') if values else ttk.Entry(f,textvariable=fields[key])
            widget.grid(row=0,column=1,sticky='ew');widgets[key]=widget
        for key,label,values in [('kind','Tipo',KINDS),('date','Fecha · AAAA-MM-DD',None),('description','Concepto',None),('platform','Plataforma',PLATFORMS),('person','Persona',self.ledger.people()),('recipient','Recibió de esa persona',self.ledger.people()),('funding','Pagado con',['Caja','Bolsillo personal']),('category','Categoría',self.ledger.categories()),('gross','Bruto USD',None),('fee','Comisión USD',None),('amount','Importe / neto USD',None),('period','Mes · AAAA-MM',None),('subscribers','Suscriptores (opcional)',None),('reference','Referencia (opcional)',None)]:field(key,label,values)
        received=tk.BooleanVar(value=d['received']);include=tk.BooleanVar(value=d['include_pending'])
        states=ttk.Frame(body);states.pack(fill='x',pady=8)
        ttk.Checkbutton(states,text='Ya llegó a mi cuenta',variable=received).pack(anchor='w')
        ttk.Checkbutton(states,text='Contar en caja aunque siga en tránsito (excepción)',variable=include).pack(anchor='w')
        ttk.Label(body,text='Explicación y mensaje original',foreground=MUTED).pack(anchor='w',pady=(8,4))
        notes=tk.Text(body,height=4,wrap='word');notes.insert('1.0',d['notes']);notes.pack(fill='x')
        attachment_label=ttk.Label(body,wraplength=620);attachment_label.pack(fill='x',pady=8)
        def labels():attachment_label.configure(text='Comprobantes: '+(', '.join([a['name'] for a in d['attachments']]+[Path(p).name for p in paths]) or 'Ninguno'))
        labels()
        def attach():paths.extend(filedialog.askopenfilenames(parent=w,title='Adjuntar comprobantes'));labels()
        def paste():
            try:paths.append(self.clipboard_image());labels()
            except Exception as e:messagebox.showerror('Pegar captura',str(e),parent=w)
        filesbar=WrapBar(body);filesbar.pack(fill='x')
        filesbar.add(ttk.Button(filesbar,text='Adjuntar comprobante',command=attach));filesbar.add(ttk.Button(filesbar,text='Pegar captura',command=paste))
        for a in d['attachments']:
            filesbar.add(ttk.Button(filesbar,text='Ver '+a['name'][:28],command=lambda a=a:self.open_receipt(a,w)))
        def visible(*_):
            kind=fields['kind'].get()
            shown={'kind','date','description','amount','reference'}
            if kind=='Retiro':shown|={'platform','gross','fee'}
            if kind=='Gasto':shown|={'person','funding','category'}
            if kind in ('Reintegro','Reparto','Traspaso personal'):shown|={'person'}
            if kind=='Traspaso personal':shown|={'recipient'}
            if kind=='Insight':shown|={'platform','period','subscribers'}
            for key,frame in frames.items():
                if key in shown:frame.pack(fill='x',pady=4,before=states)
                else:frame.pack_forget()
            # State controls remain in the stable anchor, hidden for non-withdrawals.
            for child in states.winfo_children():
                if kind=='Retiro':child.pack(anchor='w')
                else:child.pack_forget()
        fields['kind'].trace_add('write',visible);visible()
        def save():
            try:
                n=copy.deepcopy(d);n.update({k:v.get().strip() for k,v in fields.items() if k not in ('amount','gross','fee','subscribers')})
                n['amount']=cents(fields['amount'].get());n['gross']=cents(fields['gross'].get()) if n['kind']=='Retiro' else 0;n['fee']=cents(fields['fee'].get()) if n['kind']=='Retiro' else 0
                n['subscribers']=int(fields['subscribers'].get()) if n['kind']=='Insight' and fields['subscribers'].get().strip() else None
                n.update(received=received.get(),include_pending=include.get(),notes=notes.get('1.0','end').strip())
                if n['kind'] not in ('Retiro','Insight'):n['platform']=''
                for path in paths:
                    a=self.ledger.attachment(path)
                    if not any(x['file']==a['file'] for x in n['attachments']):n['attachments'].append(a)
                duplicates=self.ledger.duplicates(n)
                if duplicates and not messagebox.askyesno('Posible duplicado','Se parece a:\n'+'\n'.join(x['description']+' · '+usd(x['amount']) for x in duplicates[:5])+'\n\n¿Guardar como movimiento diferente? Elegí No para revisar el existente.',parent=w):return
                self.ledger.save([n]);w.destroy();self.report_saved()
                if after_save:after_save()
            except Exception as e:messagebox.showerror('Revisar movimiento',str(e),parent=w)
        footer.add(ttk.Button(footer,text='Guardar movimiento',style='Accent.TButton',command=save))
        footer.add(ttk.Button(footer,text='Cancelar',command=w.destroy))
        if self.ledger.get(d['id']):
            if d['id'] in outstanding(self.ledger.rows()):
                footer.add(ttk.Button(footer,text='Reintegrar',command=lambda:self.quick_reimbursement(source_id=d['id'])))
            def void():
                if messagebox.askyesno('Anular movimiento','Se revertirá su efecto en los saldos y quedará en el historial. ¿Continuar?',parent=w):
                    try:
                        n=copy.deepcopy(d);n['void']=not n['void'];self.ledger.save([n]);w.destroy();self.report_saved()
                    except Exception as e:messagebox.showerror('Anular',str(e),parent=w)
            footer.add(ttk.Button(footer,text='Restaurar' if d['void'] else 'Anular',command=void))
            if d['kind']=='Retiro' and not d['received'] and not d['void']:
                def confirm():
                    try:self.ledger.confirm(d['id']);w.destroy();self.report_saved()
                    except Exception as e:messagebox.showerror('Confirmar',str(e),parent=w)
                footer.add(ttk.Button(footer,text='Confirmar llegada',command=confirm))
        place_window(w,780,730,parent=self.app)
        return w

    def clipboard_image(self):
        from PIL import ImageGrab
        img=ImageGrab.grabclipboard()
        if not hasattr(img,'save'):raise ValueError('Copiá una captura de pantalla antes de pegar.')
        p=Path(tempfile.gettempdir())/(str(uuid.uuid4())+'.png');img.save(p);self.app.tempfiles.append(str(p));return str(p)
    def open_receipt(self,a,parent):
        try:
            p=self.ledger.media/a['file']
            if os.name=='nt':os.startfile(str(p))
            else:
                import webbrowser
                webbrowser.open(p.as_uri())
        except Exception as e:messagebox.showerror('Comprobante',str(e),parent=parent)

    def capture(self,hint=None):
        if self.app.busy or self.app.recording:return
        self.app.hide_capture()
        if self.composer is None:
            from .finance_capture import FinanceCapture
            self.composer=FinanceCapture(self)
        self.body.grid_remove();self.bottom.grid_remove();self.metric_frame.grid_remove();self.tab_bar.grid_remove();self.tools.grid_remove()
        self.composer.grid(row=5,column=0,rowspan=2,sticky='nsew');self.composer.start(hint)
        return self.composer

    def leave_capture(self):
        if self.composer and self.composer.winfo_ismapped():
            if self.app.busy or self.app.recording:
                self.composer.status.configure(text='Terminá la grabación o el procesamiento antes de volver.');return False
            self.composer.grid_remove()
        self.body.grid();self.bottom.grid();self.metric_frame.grid();self.tab_bar.grid();self.tools.grid();return True

    def reimburse_selected(self):
        selection=self.table.selection()
        if not selection:
            self.show('Por persona');self.app.status.configure(text='Hacé doble clic en la persona a la que ya le pagaste.');return
        if self.section=='Por persona':self.quick_reimbursement(person=selection[0])
        elif selection[0] in self.claims:self.quick_reimbursement(source_id=selection[0])
        else:messagebox.showinfo('Reintegrar','Elegí un gasto pagado de bolsillo o una persona con saldo pendiente.',parent=self.app)

    def quick_reimbursement(self,source_id=None,person=None):
        try:proposal=self.ledger.reimbursement(source_id,person)
        except ValueError as e:messagebox.showinfo('Reintegrar',str(e),parent=self.app);return
        w=tk.Toplevel(self.app);w.withdraw();w.transient(self.app);w.title('Registrar reintegro')
        body=ttk.Frame(w,padding=22);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Reintegrar a '+proposal['person'],font=('Segoe UI',18,'bold')).pack(anchor='w')
        ttk.Label(body,text=usd(proposal['amount']),font=('Segoe UI',24,'bold')).pack(anchor='w',pady=(12,4))
        if not proposal['amount']:
            ttk.Label(body,text='Este gasto o adelanto ya está reintegrado o compensado. No queda saldo pendiente.',wraplength=500).pack(anchor='w',pady=12)
            ttk.Button(body,text='Cerrar',command=w.destroy).pack(anchor='e');place_window(w,600,290,parent=self.app);return w
        description=self.ledger.get(source_id)['description'] if source_id else 'Saldo total pendiente con esta persona'
        ttk.Label(body,text=description,wraplength=500).pack(anchor='w',pady=4)
        ttk.Label(body,text='Confirmá cuando ya hayas enviado el dinero. Se descuenta de caja y se salda el reintegro.',foreground=MUTED,wraplength=500).pack(anchor='w',pady=10)
        paths=[];files=ttk.Label(body,text='Comprobante opcional.',wraplength=500);files.pack(anchor='w',pady=6)
        def labels():files.configure(text=', '.join(Path(p).name for p in paths) or 'Comprobante opcional.')
        def attach():paths.extend(filedialog.askopenfilenames(parent=w,title='Comprobante del reintegro'));labels()
        def paste():
            try:paths.append(self.clipboard_image());labels()
            except Exception as e:messagebox.showerror('Pegar captura',str(e),parent=w)
        toolbar=WrapBar(body);toolbar.pack(fill='x')
        toolbar.add(ttk.Button(toolbar,text='Adjuntar comprobante',command=attach));toolbar.add(ttk.Button(toolbar,text='Pegar captura',command=paste))
        footer=WrapBar(body);footer.pack(fill='x',pady=(12,0))
        def confirm():
            try:
                self.ledger.pay_reimbursement(proposal,paths);w.destroy();self.report_saved()
            except Exception as e:messagebox.showerror('Registrar reintegro',str(e),parent=w)
        confirm_button=footer.add(ttk.Button(footer,text='Ya lo pagué · registrar',style='Accent.TButton',command=confirm))
        footer.add(ttk.Button(footer,text='Cancelar',command=w.destroy))
        w.reimbursement_proposal=proposal;w.confirm_button=confirm_button
        place_window(w,640,440,parent=self.app)
        return w
