"""Center native windows inside a monitor's usable area, including negative origins."""
import sys


def work_areas():
    if sys.platform != 'win32':return []
    import ctypes
    from ctypes import wintypes as w
    class MonitorInfo(ctypes.Structure):
        _fields_=[('size',w.DWORD),('monitor',w.RECT),('work',w.RECT),('flags',w.DWORD)]
    user=ctypes.windll.user32
    callback_type=ctypes.WINFUNCTYPE(w.BOOL,w.HANDLE,w.HDC,ctypes.POINTER(w.RECT),w.LPARAM)
    user.GetMonitorInfoW.argtypes=[w.HANDLE,ctypes.POINTER(MonitorInfo)]
    user.EnumDisplayMonitors.argtypes=[w.HDC,ctypes.POINTER(w.RECT),callback_type,w.LPARAM]
    areas=[]
    def collect(handle,dc,rect,data):
        info=MonitorInfo();info.size=ctypes.sizeof(info)
        if user.GetMonitorInfoW(handle,ctypes.byref(info)):
            r=info.work;areas.append((r.left,r.top,r.right,r.bottom,bool(info.flags&1)))
        return True
    user.EnumDisplayMonitors(None,None,callback_type(collect),0)
    return areas


def choose_area(areas,point=None):
    if point:
        x,y=point
        found=next((a for a in areas if a[0]<=x<a[2] and a[1]<=y<a[3]),None)
        if found:return found
        return min(areas,key=lambda a:((a[0]+a[2])/2-x)**2+((a[1]+a[3])/2-y)**2)
    if len(areas)>=3:return sorted(areas,key=lambda a:((a[0]+a[2])/2,(a[1]+a[3])/2))[len(areas)//2]
    return next((a for a in areas if a[4]),areas[0])


def centered_rect(area,width,height):
    left,top,right,bottom=area[:4]
    width=min(width,right-left);height=min(height,bottom-top)
    return width,height,left+(right-left-width)//2,top+(bottom-top-height)//2


def native_bounds(window):
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes as w
        user=ctypes.windll.user32
        user.GetWindowRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)]
        # wm frame identifies this toplevel's wrapper, including owned dialogs.
        handle=int(str(window.tk.call('wm','frame',window._w)),0)
        rect=w.RECT()
        if user.GetWindowRect(handle,ctypes.byref(rect)):
            return rect.left,rect.top,rect.right,rect.bottom
    return window.winfo_rootx(),window.winfo_rooty(),window.winfo_rootx()+window.winfo_width(),window.winfo_rooty()+window.winfo_height()


def absolute_geometry(width,height,x,y):
    # A leading + also accepts a signed offset: +-1200 is absolute -1200,
    # whereas -1200 alone would mean an offset from the screen's right edge.
    return f'{width}x{height}+{x}+{y}'


def place_window(window,width=1340,height=860,parent=None):
    areas=work_areas() or [(0,0,window.winfo_screenwidth(),window.winfo_screenheight(),True)]
    point=(parent.winfo_rootx()+parent.winfo_width()/2,parent.winfo_rooty()+parent.winfo_height()/2) if parent and parent.winfo_viewable() else None
    area=choose_area(areas,point)
    width=max(1,min(width,area[2]-area[0]-48));height=max(1,min(height,area[3]-area[1]-80))
    _,_,x,y=centered_rect(area,width,height)
    # Set Tk's own position before mapping; an external SetWindowPos alone can
    # be overwritten by a pending Tk geometry update when an owned dialog maps.
    window.geometry(absolute_geometry(width,height,x,y));window.update_idletasks()
    window.deiconify();window.update_idletasks()
    def center_frame():
        if not window.winfo_exists() or window.state()=='withdrawn':return
        left,top,right,bottom=native_bounds(window)
        _,_,target_x,target_y=centered_rect(area,right-left,bottom-top)
        # Start from Tk's current outer-position offsets and correct using the
        # measured native frame, including caption and Windows invisible borders.
        geo=str(window.geometry())
        import re
        match=re.fullmatch(r'\d+x\d+([+-][+-]?\d+)([+-][+-]?\d+)',geo)
        if match:
            x=int(match[1].lstrip('+'));y=int(match[2].lstrip('+'))
            window.geometry(absolute_geometry(window.winfo_width(),window.winfo_height(),x+target_x-left,y+target_y-top))
            window.update_idletasks()
    center_frame()
    previous=getattr(window,'_center_job',None)
    if previous:window.after_cancel(previous)
    def settled():
        window._center_job=None;center_frame()
    window._center_job=window.after(80,settled)
    if not getattr(window,'_center_cleanup_bound',False):
        def cleanup(event):
            if event.widget==window and getattr(window,'_center_job',None):
                window.after_cancel(window._center_job);window._center_job=None
        window.bind('<Destroy>',cleanup,add='+');window._center_cleanup_bound=True
    return area
