import json,os,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch

@unittest.skipUnless(sys.platform=='win32' or os.getenv('DISPLAY'),'Requiere escritorio')
class ProjectAppearanceTests(unittest.TestCase):
    def test_chooser_direct_selection_green_theme_and_exact_return(self):
        import tkinter as tk
        from tkinter import ttk
        from app.main import App
        from app.theme import BG,SURFACE,GREEN_PALETTE
        from app.core import PEOPLE,ALIASES
        people=list(PEOPLE);aliases=dict(ALIASES)
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'LOCALAPPDATA':tmp}):
            app=App()
            try:
                path=Path(tmp)/'project.almproject'
                path.write_text(json.dumps(dict(product='AnimationLoverProject',schema=1,project=dict(id='personal-test',name='Proyecto personal',personal=True),expenses=[])))
                app.projects.import_project(app.projects.preview_import(path));app.update()
                self.assertIsInstance(app.project_selector,tk.Canvas)
                self.assertEqual(app.cget('background'),BG)
                app.project_selector.invoke();app.update();picker=app.project_picker
                self.assertEqual(set(picker.cards),{'main','personal-test'})
                self.assertEqual(picker.grab_current(),picker)
                if os.getenv('ALM_SCREENSHOT'):
                    from PIL import ImageGrab
                    ImageGrab.grab().save(os.environ['ALM_SCREENSHOT'].replace('.png','-project-chooser.png'))
                picker.cards['personal-test'].invoke();app.update()
                self.assertEqual(app.project_id,'personal-test');self.assertFalse(picker.winfo_exists())
                self.assertEqual(app.cget('background'),GREEN_PALETTE[BG])
                self.assertEqual(app.board.canvas.cget('background'),GREEN_PALETTE[SURFACE])
                self.assertEqual(ttk.Style(app).lookup('Accent.TButton','background'),GREEN_PALETTE['#626fe0'])
                app.nav_buttons['Hoy'].over(True);app.board.render();app.update()
                self.assertEqual(app.board.canvas.cget('background'),GREEN_PALETTE[SURFACE])
                app.finance();app.update()
                self.assertEqual(ttk.Style(app).lookup('Finance.Treeview','fieldbackground'),GREEN_PALETTE[SURFACE])
                app.change_view('Hoy');app.show_capture();app.update()
                self.assertEqual(app.cget('background'),GREEN_PALETTE[BG]);app.hide_capture();app.update()
                until=time.monotonic()+.15
                while time.monotonic()<until:app.update();time.sleep(.01)
                if os.getenv('ALM_SCREENSHOT'):
                    from PIL import ImageGrab
                    ImageGrab.grab().save(os.environ['ALM_SCREENSHOT'].replace('.png','-green-project.png'))
                app.project_selector.invoke();app.update();app.project_picker.cards['main'].invoke();app.update()
                self.assertEqual(app.project_id,'main');self.assertEqual(app.cget('background'),BG)
                self.assertEqual(app.board.canvas.cget('background'),SURFACE)
                self.assertEqual(ttk.Style(app).lookup('Accent.TButton','background'),'#626fe0')
                app.project_selector.invoke();app.update();app.project_picker.destroy();app.update()
                self.assertEqual(app.project_id,'main')
            finally:app.close();PEOPLE[:]=people;ALIASES.clear();ALIASES.update(aliases)
