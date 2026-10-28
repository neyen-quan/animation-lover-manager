import os,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(sys.platform=='win32' or os.getenv('DISPLAY'),'Requiere escritorio')
class PopupCenteringTests(unittest.TestCase):
 def test_all_dialogs_center_after_map_and_capture_reopens_centered(self):
  import tkinter as tk
  from app.main import App
  from app.core import fresh
  from app.update_dialog import UpdateDialog
  from app.windowing import choose_area,native_bounds,work_areas
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
   app=App()
   def settle():
    until=time.monotonic()+.16
    while time.monotonic()<until:app.update();time.sleep(.01)
   def assert_centered(window):
    settle()
    point=(app.winfo_rootx()+app.winfo_width()/2,app.winfo_rooty()+app.winfo_height()/2)
    areas=work_areas() or [(0,0,app.winfo_screenwidth(),app.winfo_screenheight(),True)]
    area=choose_area(areas,point);left,top,right,bottom=native_bounds(window)
    self.assertLessEqual(abs((left+right)-(area[0]+area[2])),4,window.title())
    self.assertLessEqual(abs((top+bottom)-(area[1]+area[3])),4,window.title())
    self.assertGreaterEqual(left,area[0]);self.assertGreaterEqual(top,area[1])
    self.assertLessEqual(right,area[2]);self.assertLessEqual(bottom,area[3])
   try:
    # Parent deliberately off-center: popups must center on its monitor.
    settle();app.geometry('900x640+40+40');settle();main_position=native_bounds(app)
    app.show_capture();assert_centered(app.capture_window)
    app.input.insert('1.0','Borrador conservado');app.hide_capture()
    app.capture_window.geometry('840x540+0+0');app.show_capture();assert_centered(app.capture_window)
    self.assertEqual(app.input.get('1.0','end').strip(),'Borrador conservado');app.hide_capture()
    d=fresh('Tarjeta de prueba');app.store.apply([d]);app.change_view('Todas');app.board.selection_set(d['id'])
    for action in [lambda:app.editor(d),app.settings,app.history,app.notify]:
     action();settle()
     window=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel) and w.state()!='withdrawn')
     assert_centered(window)
     if os.getenv('ALM_SCREENSHOT') and window.title()=='Ajustes':
      from PIL import ImageGrab
      ImageGrab.grab().save(os.environ['ALM_SCREENSHOT'].replace('.png','-settings-contrast.png'))
     window.destroy()
    dialog=UpdateDialog(app,app.store,'0.3.3',Path(folder));assert_centered(dialog)
    if os.getenv('ALM_SCREENSHOT'):
     from PIL import ImageGrab
     ImageGrab.grab().save(os.environ['ALM_SCREENSHOT'].replace('.png','-update-centered.png'))
    dialog.destroy()
    self.assertEqual(native_bounds(app),main_position)
   finally:app.close()
