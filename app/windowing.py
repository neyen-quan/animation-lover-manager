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


def place_window(window,width=1340,height=860,parent=None):
    areas=work_areas() or [(0,0,window.winfo_screenwidth(),window.winfo_screenheight(),True)]
    point=(parent.winfo_rootx()+parent.winfo_width()/2,parent.winfo_rooty()+parent.winfo_height()/2) if parent else None
    area=choose_area(areas,point)
    width=min(width,area[2]-area[0]-48);height=min(height,area[3]-area[1]-80)
    window.geometry(f'{max(1,width)}x{max(1,height)}');window.update_idletasks()
    window.deiconify();window.update_idletasks()
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes as w
        user=ctypes.windll.user32
        user.GetAncestor.argtypes=[w.HWND,w.UINT];user.GetAncestor.restype=w.HWND
        user.GetWindowRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)]
        user.SetWindowPos.argtypes=[w.HWND,w.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.UINT]
        handle=user.GetAncestor(window.winfo_id(),2)
        rect=w.RECT()
        if user.GetWindowRect(handle,ctypes.byref(rect)):
            _,_,x,y=centered_rect(area,rect.right-rect.left,rect.bottom-rect.top)
            user.SetWindowPos(handle,None,x,y,0,0,0x0001|0x0004|0x0010)
    else:
        _,_,x,y=centered_rect(area,width,height)
        window.geometry(f'{width}x{height}+{x}+{y}')
    return area
