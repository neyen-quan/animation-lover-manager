import tkinter as tk
from tkinter import ttk
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
    s.configure('TButton',padding=(12,8),background=CARD,foreground=FG,borderwidth=0,relief='flat',focuscolor=CARD)
    s.map('TButton',background=[('active',HOVER),('disabled',SURFACE)],foreground=[('disabled','#77809c')])
    s.configure('Accent.TButton',background='#616ce8',foreground='white',padding=(15,9),font=('Segoe UI',10,'bold'))
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
    root.option_add('*TCombobox*Listbox.background',CARD);root.option_add('*TCombobox*Listbox.foreground',FG)
    root.option_add('*Text.font',('Segoe UI',11))

def apply_popup_theme(window):
    """Warm, contrasting dialogs; named ttk styles leave the dark board intact."""
    window.configure(bg=POPUP_BG,highlightthickness=2,highlightbackground=POPUP_BORDER,highlightcolor=POPUP_BORDER)
    style=ttk.Style(window)
    style.configure('Popup.TFrame',background=POPUP_BG)
    style.configure('Popup.TLabel',background=POPUP_BG,foreground=POPUP_FG)
    style.configure('Popup.TButton',background=POPUP_BUTTON,foreground=POPUP_FG,focuscolor=POPUP_BUTTON)
    style.map('Popup.TButton',background=[('disabled','#e0d8ca'),('active',POPUP_HOVER)],foreground=[('disabled','#777268'),('!disabled',POPUP_FG)])
    style.configure('Popup.Accent.TButton',background=POPUP_ACCENT,foreground='#ffffff',focuscolor=POPUP_ACCENT)
    style.map('Popup.Accent.TButton',background=[('disabled','#c7c4d8'),('active','#444a9b')],foreground=[('disabled','#656173'),('!disabled','#ffffff')])
    style.configure('Popup.TEntry',fieldbackground=POPUP_INPUT,foreground=POPUP_FG,insertcolor=POPUP_FG,bordercolor=POPUP_BORDER,lightcolor=POPUP_BORDER,darkcolor=POPUP_BORDER)
    style.map('Popup.TEntry',bordercolor=[('focus',POPUP_ACCENT)])
    style.configure('Popup.TCombobox',fieldbackground=POPUP_INPUT,background=POPUP_BUTTON,foreground=POPUP_FG,arrowcolor=POPUP_FG,bordercolor=POPUP_BORDER,lightcolor=POPUP_BORDER,darkcolor=POPUP_BORDER)
    style.map('Popup.TCombobox',fieldbackground=[('readonly',POPUP_INPUT)],foreground=[('readonly',POPUP_FG)],selectbackground=[('readonly',POPUP_INPUT)],selectforeground=[('readonly',POPUP_FG)])
    style.configure('Popup.TCheckbutton',background=POPUP_BG,foreground=POPUP_MUTED,indicatorbackground=POPUP_INPUT,indicatorforeground=POPUP_ACCENT)
    style.map('Popup.TCheckbutton',background=[('active',POPUP_BG)],foreground=[('active',POPUP_FG)])
    style.configure('Popup.TSeparator',background='#baae9d')
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
            widget.configure(style='Popup.TLabel',background=POPUP_BG,foreground=color)
        elif isinstance(widget,ttk.Frame):widget.configure(style='Popup.TFrame')
        elif isinstance(widget,ttk.Scrollbar):widget.configure(style='Popup.'+str(widget.cget('orient')).title()+'.TScrollbar')
        elif isinstance(widget,ttk.Progressbar):widget.configure(style='Popup.'+str(widget.cget('orient')).title()+'.TProgressbar')
        elif isinstance(widget,ttk.Separator):widget.configure(style='Popup.TSeparator')
        elif isinstance(widget,tk.Text):
            widget.configure(bg=POPUP_INPUT,fg=POPUP_FG,insertbackground=POPUP_FG,selectbackground=POPUP_ACCENT,selectforeground='#ffffff',highlightthickness=1,highlightbackground=POPUP_BORDER,highlightcolor=POPUP_ACCENT,relief='flat',borderwidth=0)
        elif isinstance(widget,tk.Canvas):widget.configure(bg=POPUP_BG)
        for child in widget.winfo_children():
            if not isinstance(child,tk.Toplevel):restyle(child)
    for child in window.winfo_children():restyle(child)
