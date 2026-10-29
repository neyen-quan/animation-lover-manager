import tkinter as tk
from tkinter import ttk,font as tkfont
BG='#181b30';CARD='#262b45';SURFACE='#20243b';HOVER='#2d334f';LINE='#353b57'
FG='#edf0fa';MUTED='#a4acc4';ACCENT='#737bff';SHELL='#111425'
POPUP_BG='#e9e1d3';POPUP_INPUT='#f7f0e4';POPUP_FG='#292d40';POPUP_MUTED='#626174'
POPUP_BUTTON='#d8cdbb';POPUP_HOVER='#cbbda6';POPUP_BORDER='#9482b7';POPUP_ACCENT='#535bb8'
def apply_theme(root):
    root.configure(bg=BG)
    s=ttk.Style(root);s.theme_use('clam')
    s.configure('.',background=BG,foreground=FG,font=('Segoe UI',10))
    s.configure('TFrame',background=BG);s.configure('Panel.TFrame',background=SURFACE)
    s.configure('Shell.TFrame',background=SHELL);s.configure('Shell.TLabel',background=SHELL)
    for orient in ['Vertical','Horizontal']:
        s.configure(orient+'.TScrollbar',background=LINE,troughcolor=BG,arrowcolor=MUTED,borderwidth=0,lightcolor=LINE,darkcolor=LINE,arrowsize=10)
    s.configure('TButton',padding=(12,7),background='#2c3650',foreground=FG,font=('Segoe UI',10,'bold'),borderwidth=1,relief='raised',bordercolor='#414f6b',lightcolor='#53617b',darkcolor='#1b2237',focuscolor='#2c3650')
    s.map('TButton',background=[('active',HOVER),('disabled',SURFACE)],foreground=[('disabled','#77809c')])
    s.configure('Accent.TButton',background='#626fe0',foreground='white',padding=(15,8),font=('Segoe UI',10,'bold'),bordercolor='#8391f2',lightcolor='#a2adff',darkcolor='#4651ad')
    s.map('Accent.TButton',background=[('active','#7a82ff'),('disabled','#353b62')])
    s.configure('Nav.TButton',padding=(12,6),anchor='w',background=BG,foreground=MUTED)
    s.map('Nav.TButton',background=[('active',CARD)],foreground=[('active',FG)])
    s.configure('Active.Nav.TButton',padding=(12,6),anchor='w',background='#303961',foreground='#dfe4ff')
    s.map('Active.Nav.TButton',background=[('active','#3c4777')])
    s.configure('Tab.TButton',background=BG,foreground=MUTED,padding=(15,10))
    s.map('Tab.TButton',background=[('active',CARD)])
    s.configure('Active.Tab.TButton',background=CARD,foreground='#bcc4ff',padding=(15,10),font=('Segoe UI',10,'bold'))
    s.configure('TEntry',bordercolor=LINE,lightcolor=LINE,darkcolor=LINE,fieldbackground=SURFACE,foreground=FG,insertcolor=FG,borderwidth=1,padding=8)
    s.map('TEntry',bordercolor=[('focus',ACCENT)])
    s.configure('TCombobox',fieldbackground=SURFACE,background=SURFACE,foreground=FG,arrowcolor=MUTED,padding=6,borderwidth=0,bordercolor=LINE,lightcolor=LINE,darkcolor=LINE)
    s.map('TCombobox',fieldbackground=[('readonly',SURFACE)],foreground=[('readonly',FG)],selectbackground=[('readonly',SURFACE)],selectforeground=[('readonly',FG)])
    s.configure('TCheckbutton',background=BG,foreground=MUTED,indicatorbackground=SURFACE,indicatorforeground=ACCENT)
    s.configure('TSeparator',background=LINE)
    s.configure('Toolbar.TFrame',background='#20283e',borderwidth=1,relief='raised',bordercolor='#3a4660',lightcolor='#45516c',darkcolor='#1a2034')
    s.configure('Toolbar.TLabel',background='#20283e',foreground='#c5cee3',font=('Segoe UI',10,'bold'))
    root.option_add('*TCombobox*Listbox.background',CARD);root.option_add('*TCombobox*Listbox.foreground',FG)
    root.option_add('*Text.font',('Segoe UI',11))

def apply_popup_theme(window):
    """Warm, contrasting dialogs; named ttk styles leave the dark board intact."""
    POPUP_ACCENT=project_color(window,globals()['POPUP_ACCENT'])
    POPUP_BORDER=project_color(window,globals()['POPUP_BORDER'])
    window.configure(bg=POPUP_BG,highlightthickness=2,highlightbackground=POPUP_BORDER,highlightcolor=POPUP_BORDER)
    style=ttk.Style(window)
    style.configure('Popup.TFrame',background=POPUP_BG)
    style.configure('Popup.TLabel',background=POPUP_BG,foreground=POPUP_FG)
    style.configure('Popup.TButton',background='#e1d6c3',foreground=POPUP_FG,focuscolor='#e1d6c3',font=('Segoe UI',10,'bold'),borderwidth=1,relief='raised',bordercolor='#bcad93',lightcolor='#fff7e8',darkcolor='#b3a183')
    style.map('Popup.TButton',background=[('disabled','#e0d8ca'),('active',POPUP_HOVER)],foreground=[('disabled','#777268'),('!disabled',POPUP_FG)])
    style.configure('Popup.Accent.TButton',background=POPUP_ACCENT,foreground='#ffffff',focuscolor=POPUP_ACCENT,borderwidth=1,relief='raised',bordercolor='#777dcb',lightcolor='#a1a6e5',darkcolor='#3d438b')
    style.map('Popup.Accent.TButton',background=[('disabled','#c7c4d8'),('active','#444a9b')],foreground=[('disabled','#656173'),('!disabled','#ffffff')])
    style.configure('Popup.TEntry',fieldbackground=POPUP_INPUT,foreground=POPUP_FG,insertcolor=POPUP_FG,bordercolor=POPUP_BORDER,lightcolor=POPUP_BORDER,darkcolor=POPUP_BORDER)
    style.map('Popup.TEntry',bordercolor=[('focus',POPUP_ACCENT)])
    style.configure('Popup.TCombobox',fieldbackground=POPUP_INPUT,background=POPUP_BUTTON,foreground=POPUP_FG,arrowcolor=POPUP_FG,bordercolor=POPUP_BORDER,lightcolor=POPUP_BORDER,darkcolor=POPUP_BORDER)
    style.map('Popup.TCombobox',fieldbackground=[('readonly',POPUP_INPUT)],foreground=[('readonly',POPUP_FG)],selectbackground=[('readonly',POPUP_INPUT)],selectforeground=[('readonly',POPUP_FG)])
    style.configure('Popup.TCheckbutton',background=POPUP_BG,foreground=POPUP_MUTED,indicatorbackground=POPUP_INPUT,indicatorforeground=POPUP_ACCENT)
    style.map('Popup.TCheckbutton',background=[('active',POPUP_BG)],foreground=[('active',POPUP_FG)])
    style.configure('Popup.TSeparator',background='#baae9d')
    style.configure('Popup.Toolbar.TFrame',background='#eee6d8',borderwidth=1,relief='raised',bordercolor='#cebfaa',lightcolor='#fff7e9',darkcolor='#c8b89f')
    style.configure('Popup.Header.TFrame',background='#f2eadc',borderwidth=1,relief='raised',bordercolor='#d1c2ae',lightcolor='#fff8ec',darkcolor='#cdbda5')
    for orient in ['Vertical','Horizontal']:
        style.configure('Popup.'+orient+'.TScrollbar',background=POPUP_BUTTON,troughcolor=POPUP_BG,arrowcolor=POPUP_MUTED,lightcolor=POPUP_BG,darkcolor=POPUP_BG)
        style.map('Popup.'+orient+'.TScrollbar',background=[('active',POPUP_HOVER)])
        style.configure('Popup.'+orient+'.TProgressbar',background=POPUP_ACCENT,troughcolor='#d5ccbd',bordercolor='#baae9d',lightcolor=POPUP_ACCENT,darkcolor=POPUP_ACCENT)
    def restyle(widget):
        if isinstance(widget,ttk.Combobox):
            widget.configure(style='Popup.TCombobox')
            # A combobox's native Tk list lives outside the ordinary widget tree.
            try:
                popdown=widget.tk.call('ttk::combobox::PopdownWindow',str(widget))
                widget.tk.call(str(popdown)+'.f.l','configure','-background',POPUP_INPUT,'-foreground',POPUP_FG,'-selectbackground',POPUP_ACCENT,'-selectforeground','#ffffff')
            except tk.TclError:pass
        elif isinstance(widget,ttk.Entry):widget.configure(style='Popup.TEntry')
        elif isinstance(widget,ttk.Checkbutton):widget.configure(style='Popup.TCheckbutton')
        elif isinstance(widget,ttk.Button):widget.configure(style='Popup.Accent.TButton' if 'Accent.' in str(widget.cget('style')) else 'Popup.TButton')
        elif isinstance(widget,ttk.Label):
            color=str(widget.cget('foreground')).lower()
            color=POPUP_MUTED if color in (MUTED,POPUP_MUTED) else '#865000' if color in ('#fdab3d','#865000') else POPUP_FG
            background='#f2eadc' if str(widget.master.cget('style'))=='Popup.Header.TFrame' else '#eee6d8' if str(widget.master.cget('style'))=='Popup.Toolbar.TFrame' else POPUP_BG
            widget.configure(style='Popup.TLabel',background=background,foreground=color)
            text=str(widget.cget('text'))
            if text and len(text)<=44 and color!=POPUP_MUTED:
                current=tkfont.Font(root=window,font=widget.cget('font') or style.lookup('TLabel','font'))
                widget.configure(font=(current.actual('family'),current.actual('size'),'bold'))
        elif isinstance(widget,ttk.Frame):
            if widget.__class__.__name__=='WrapBar':
                widget.configure(style='Popup.Toolbar.TFrame');widget.inset=6;widget.reflow()
            elif any(isinstance(child,ttk.Label) and str(child.cget('text')) in ('Soltá una idea','Detalle de tarjeta') for child in widget.winfo_children()):
                widget.configure(style='Popup.Header.TFrame')
            else:widget.configure(style='Popup.TFrame')
        elif isinstance(widget,ttk.Scrollbar):widget.configure(style='Popup.'+str(widget.cget('orient')).title()+'.TScrollbar')
        elif isinstance(widget,ttk.Progressbar):widget.configure(style='Popup.'+str(widget.cget('orient')).title()+'.TProgressbar')
        elif isinstance(widget,ttk.Separator):widget.configure(style='Popup.TSeparator')
        elif isinstance(widget,tk.Text):
            widget.configure(bg=POPUP_INPUT,fg=POPUP_FG,insertbackground=POPUP_FG,selectbackground=POPUP_ACCENT,selectforeground='#ffffff',highlightthickness=1,highlightbackground=POPUP_BORDER,highlightcolor=POPUP_ACCENT,relief='flat',borderwidth=0)
            widget.configure(padx=max(10,int(widget.cget('padx'))),pady=max(8,int(widget.cget('pady'))))
        elif isinstance(widget,tk.Canvas):widget.configure(bg=POPUP_BG)
        for child in widget.winfo_children():
            if not isinstance(child,tk.Toplevel):restyle(child)
    for child in window.winfo_children():restyle(child)
    palette=getattr(window._root(),'_project_palette',{})
    for name in ['Popup.Accent.TButton','Popup.TButton','Popup.TEntry','Popup.TCombobox','Popup.TCheckbutton','Popup.TSeparator','Popup.Horizontal.TProgressbar','Popup.Vertical.TProgressbar']:_map_style(style,name,palette)

# A project theme affects presentation only; semantic warnings keep their colors.
GREEN_PALETTE={
    BG:'#10251f',CARD:'#203d33',SURFACE:'#183128',HOVER:'#294e3f',LINE:'#355849',
    FG:'#edf8f1',MUTED:'#a4c2b2',ACCENT:'#46bd88',SHELL:'#0a1b16',
    '#2c3650':'#28523f','#414f6b':'#426e58','#53617b':'#608c72','#1b2237':'#10291e',
    '#626fe0':'#277950','#8391f2':'#56b780','#a2adff':'#9cdbb4','#4651ad':'#1b5639',
    '#7a82ff':'#369d6c','#353b62':'#254b3a','#77809c':'#72907e',
    '#303961':'#28533e','#dfe4ff':'#e2f6e8','#3c4777':'#386a50','#bcc4ff':'#a7e7be',
    '#20283e':'#18392b','#3a4660':'#3a634b','#45516c':'#4e785e','#1a2034':'#10271c','#c5cee3':'#c3ddce',
    '#232c43':'#1c3b2d','#46516e':'#466e57','#a7afff':'#9de7b9','#aab8ff':'#a0e2b7',
    '#303d62':'#2b5a41','#29334c':'#254a36','#20273c':'#173325','#25304b':'#21432f',
    '#7386c1':'#70b68d','#4b5c7b':'#4c8163','#303b52':'#31533f','#526282':'#679479',
    '#39445c':'#3b634b','#b2baff':'#a7efc1','#f2f3fc':'#eefaf2','#cdd6eb':'#d0e6d6',
    '#b7baff':'#b0e3c2','#8bc9ef':'#9dddb7','#c4b3f3':'#b1d8b5','#9fc6ed':'#abd9bb',
    '#24283f':'#203e2d','#303653':'#2c583f','#53607b':'#52795f','#303650':'#294b36',
    '#7b83ff':'#5fbc8c','#8b98ff':'#91d6a9','#aaa5ff':'#b0d7a7','#96a6c5':'#a1bfa9',
    '#3b477a':'#2d6548','#8b96ff':'#84d6a1','#b19bdb':'#a3d2ae','#72bdd9':'#90cfb4',
    '#b5bfff':'#b1ebc6',POPUP_ACCENT:'#2b7650',POPUP_BORDER:'#79a68c',
    '#777dcb':'#5a9f77','#a1a6e5':'#a6d8b8','#3d438b':'#205738','#444a9b':'#205f40',
}

PROJECT_STYLES=['.','TFrame','Panel.TFrame','Shell.TFrame','Shell.TLabel','TLabel','TButton','Accent.TButton',
    'Nav.TButton','Active.Nav.TButton','Tab.TButton','Active.Tab.TButton','TEntry','TCombobox','TCheckbutton',
    'TSeparator','Toolbar.TFrame','Toolbar.TLabel','Vertical.TScrollbar','Horizontal.TScrollbar',
    'Finance.Treeview','Finance.Treeview.Heading','Finance.TButton','Finance.Accent.TButton']

def project_color(widget,color):
    palette=getattr(widget._root(),'_project_palette',{})
    return palette.get(str(color).lower(),color)

def project_primary(widget):
    return getattr(widget._root(),'_project_palette',{}).get('#626fe0',ACCENT)

def recolor_canvas(canvas):
    if not canvas.winfo_exists():return
    for item in canvas.find_all():
        options=canvas.itemconfigure(item)
        for key in ('fill','outline'):
            if key in options:
                value=canvas.itemcget(item,key);mapped=project_color(canvas,value)
                if value!=mapped:canvas.itemconfigure(item,**{key:mapped})

def themed_drawing(method):
    from functools import wraps
    @wraps(method)
    def draw(self,*args,**kwargs):
        result=method(self,*args,**kwargs)
        canvases=[self] if isinstance(self,tk.Canvas) else [getattr(self,name,None) for name in ('canvas','metric_frame','chart')]
        for canvas in canvases:
            if isinstance(canvas,tk.Canvas):recolor_canvas(canvas)
        return result
    return draw

def recolor_widgets(parent):
    """Remember base colors once, so switching back restores exact original hues."""
    if not parent.winfo_exists():return
    keys=('background','foreground','insertbackground','highlightbackground','highlightcolor','selectbackground','selectforeground')
    original=getattr(parent,'_project_base_colors',{})
    config=parent.configure()
    for key in keys:
        if key not in config:continue
        if key not in original:
            value=str(parent.cget(key))
            if value.startswith('#'):original[key]=value
        if key in original:parent.configure(**{key:project_color(parent,original[key])})
    parent._project_base_colors=original
    if isinstance(parent,tk.Text):
        tags=getattr(parent,'_project_base_tags',{})
        for tag in parent.tag_names():
            for option in ('foreground','background'):
                key=(tag,option)
                if key not in tags:
                    value=parent.tag_cget(tag,option)
                    if str(value).startswith('#'):tags[key]=value
                if key in tags:parent.tag_configure(tag,**{option:project_color(parent,tags[key])})
        parent._project_base_tags=tags
    for child in parent.winfo_children():
        if not isinstance(child,tk.Toplevel):recolor_widgets(child)

def _map_style(style,name,palette):
    original=style.configure(name) or {}
    colors={key:palette.get(str(value).lower(),value) for key,value in original.items() if str(value).startswith('#')}
    if colors:style.configure(name,**colors)
    for key,entries in style.map(name).items():
        changed=[tuple(entry[:-1])+(palette.get(str(entry[-1]).lower(),entry[-1]),) for entry in entries]
        style.map(name,**{key:changed})

def apply_project_theme(root,personal=False):
    root._project_palette=GREEN_PALETTE if personal else {}
    apply_theme(root)
    style=ttk.Style(root)
    # These styles may be created lazily by the finance workspace. Restore their
    # base values before mapping, including when returning to the main project.
    style.configure('Finance.Treeview',background=SURFACE,fieldbackground=SURFACE,foreground=FG,bordercolor=LINE,lightcolor=LINE,darkcolor=LINE)
    style.configure('Finance.Treeview.Heading',background=CARD,foreground=FG,bordercolor=LINE,lightcolor=LINE,darkcolor=LINE)
    style.map('Finance.Treeview',background=[('selected','#3b477a')],foreground=[('selected','#ffffff')])
    style.configure('Finance.TButton',font=('Segoe UI',-13,'bold'),padding=(8,6))
    style.configure('Finance.Accent.TButton',font=('Segoe UI',-13,'bold'),padding=(8,6),background=project_primary(root),foreground='white')
    for name in PROJECT_STYLES:_map_style(style,name,root._project_palette)
    recolor_widgets(root)
    root.option_add('*TCombobox*Listbox.background',project_color(root,CARD))
    root.option_add('*TCombobox*Listbox.foreground',project_color(root,FG))
