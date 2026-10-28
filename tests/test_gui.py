import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

@unittest.skipUnless(sys.platform=='win32' or os.getenv('DISPLAY'),'Requiere escritorio')
class LayoutTests(unittest.TestCase):
 def test_controls_reachable_without_main_scroll_and_capture_is_popup(self):
  from app.main import App
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'LOCALAPPDATA':tmp}):
   app=App()
   try:
    for scaling in [1.333,1.667,2.0,2.667]:
     app.tk.call('tk','scaling',scaling);app.geometry('1000x680');app.update()
     app.show_capture();app.update()
     self.assertEqual(app.capture_window.state(),'normal')
     self.assertEqual(app.capture.winfo_toplevel(),app.capture_window)
     for button in [app.interpret_button,app.selected_button]:
      self.assertGreaterEqual(button.winfo_rooty(),app.capture_window.winfo_rooty())
      self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),app.capture_window.winfo_rooty()+app.capture_window.winfo_height())
     app.hide_capture();app.update()
     self.assertEqual(app.capture_window.state(),'withdrawn')
     self.assertLessEqual(app.task_actions.winfo_rooty()+app.task_actions.winfo_height(),app.winfo_rooty()+app.winfo_height())
     self.assertGreater(app.board.canvas.winfo_height(),100)
     self.assertLessEqual(app.update_button.winfo_rootx()+app.update_button.winfo_width(),app.winfo_rootx()+app.winfo_width())
     self.assertEqual(app.board.canvas.yview(),(0.0,1.0))
    from app.update_dialog import UpdateDialog
    dialog=UpdateDialog(app,app.store,'0.3.2',Path(tmp))
    for scaling in [1.333,2.0,2.667]:
     app.tk.call('tk','scaling',scaling);app.update();dialog.area.canvas.yview_moveto(1);app.update()
     self.assertLessEqual(dialog.local_btn.winfo_rooty()+dialog.local_btn.winfo_height(),dialog.area.canvas.winfo_rooty()+dialog.area.canvas.winfo_height()+1)
    dialog.destroy()
    app.tk.call('tk','scaling',1.333)
    from app.windowing import place_window
    place_window(app);app.update()
    if os.getenv('ALM_SCREENSHOT'):
     from PIL import ImageGrab
     ImageGrab.grab().save(os.environ['ALM_SCREENSHOT'])
     app.show_capture();app.update();ImageGrab.grab().save(os.environ['ALM_SCREENSHOT'].replace('.png','-capture.png'));app.hide_capture()
   finally:app.close()
if __name__=='__main__':unittest.main()
