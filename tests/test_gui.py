import os,sys,tempfile,unittest
from pathlib import Path
@unittest.skipUnless(sys.platform=='win32' or os.getenv('DISPLAY'),'Requiere escritorio')
class LayoutTests(unittest.TestCase):
 def test_controls_reachable_at_dpi_scales(self):
  import faulthandler
  faulthandler.dump_traceback_later(30,repeat=True)
  from app.main import App
  with tempfile.TemporaryDirectory() as tmp:
   os.environ['LOCALAPPDATA']=tmp;app=App()
   try:
    for scaling in [1.333,1.667,2.0,2.667]:
     print('Escala de interfaz:',scaling,flush=True)
     app.tk.call('tk','scaling',scaling);app.geometry('1000x680');app.update()
     print('Geometría estabilizada',flush=True)
     self.assertLessEqual(app.update_button.winfo_rootx()+app.update_button.winfo_width(),app.winfo_rootx()+app.winfo_width())
     app.area.canvas.yview_moveto(1);app.update()
     for button in [app.interpret_button,app.selected_button]:
      self.assertGreaterEqual(button.winfo_rooty(),app.area.canvas.winfo_rooty()-1)
      self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),app.area.canvas.winfo_rooty()+app.area.canvas.winfo_height()+1)
    app.tk.call('tk','scaling',1.333);app.geometry('1180x820');app.update();app.area.canvas.yview_moveto(0);app.update()
    if os.getenv('ALM_SCREENSHOT'):
     from PIL import ImageGrab
     ImageGrab.grab().save(os.environ['ALM_SCREENSHOT'])
   finally:app.close();faulthandler.cancel_dump_traceback_later()
if __name__=='__main__':unittest.main()
