import os,sys,tempfile,time,unittest
from unittest.mock import patch
from app.core import fresh
from app.board import table_pages

class PaginationTests(unittest.TestCase):
 def test_all_tasks_reachable_across_mixed_groups(self):
  items=[]
  for i in range(53):
   d=fresh(f'Tarea {i}');d['status']=['Pendiente','En curso','Esperando','Terminado'][i%4];items.append(d)
  for height in [210,350,600]:
   pages=table_pages(items,height,1)
   self.assertEqual({d['id'] for page in pages for d in page},{d['id'] for d in items})
   self.assertEqual(sum(map(len,pages)),len(items));self.assertGreater(len(pages),1)

@unittest.skipUnless(sys.platform=='win32' or os.getenv('DISPLAY'),'Requiere escritorio')
class CaptureTests(unittest.TestCase):
 def test_text_dates_normalize_or_ask_without_losing_personal_draft(self):
  import json
  from pathlib import Path
  from app.main import App
  from app.core import PEOPLE,ALIASES
  people=list(PEOPLE);aliases=dict(ALIASES)
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
   app=App()
   def settle():
    end=time.monotonic()+5
    while app.busy and time.monotonic()<end:app.update();time.sleep(.01)
    app.update();self.assertFalse(app.busy)
   try:
    path=Path(folder)/'test.almproject'
    path.write_text(json.dumps(dict(product='AnimationLoverProject',schema=1,project=dict(id='date-test',name='Proyecto personal',personal=True),expenses=[])))
    app.projects.import_project(app.projects.preview_import(path));app.switch_project('date-test')
    text='Preparar material y revisar las ideas pendientes.'
    app.show_capture();app.input.insert('1.0',text);app.update();app.save_draft()
    proposals={'creates':[dict(title='Preparar material',planned='2 026-10-29',deadline='2026-11-01'),dict(title='Revisar ideas',planned='2026-02-30',deadline='2026-11-01')]}
    with patch('app.main.interpret',return_value=proposals),patch('app.main.messagebox.showinfo') as info,patch('app.main.messagebox.showerror') as error:
     app.process();settle()
     self.assertEqual(app.store.items(),[]);error.assert_not_called();info.assert_called_once()
     self.assertIn('fecha prevista',info.call_args.args[1])
     self.assertTrue(app.capture_visible)
     self.assertEqual(app.input.get('1.0','end').strip(),text)
     self.assertEqual(app.store.setting('draft'),text)
    proposals['creates'][1]['planned']='2026-10-29'
    with patch('app.main.interpret',return_value=proposals),patch('app.main.messagebox.showerror') as error:
     app.process();settle();error.assert_not_called()
    self.assertEqual(len(app.store.items()),2)
    for task in app.store.items():
     self.assertEqual(task['planned'],'2026-10-29');self.assertEqual(task['owners'],[app.store.people()[0]])
    self.assertEqual(app.store.setting('draft'),'');self.assertFalse(app.capture_visible)
    self.assertEqual(app.root_store.items(),[])
   finally:app.close();PEOPLE[:]=people;ALIASES.clear();ALIASES.update(aliases)
 def test_draft_success_ambiguity_and_failure(self):
  from app.main import App
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
   app=App()
   def settle():
    deadline=time.monotonic()+5
    while app.busy and time.monotonic()<deadline:app.update();time.sleep(.01)
    app.update();self.assertFalse(app.busy)
   try:
    app.show_capture();app.input.insert('1.0','Una idea de prueba');app.update();app.hide_capture();app.show_capture()
    self.assertEqual(app.input.get('1.0','end').strip(),'Una idea de prueba')
    with patch('app.main.interpret',return_value={'creates':[{'title':'Idea organizada'}]}):
     app.process();self.assertFalse(app.capture_visible);settle()
    self.assertEqual(app.store.items()[0]['title'],'Idea organizada');self.assertFalse(app.capture_visible)
    self.assertEqual(app.store.setting('draft'),'')
    app.show_capture();app.input.insert('1.0','Avanzar la tarea');app.update()
    with patch('app.main.interpret',return_value={'questions':['¿Qué tarea?']}),patch('app.main.messagebox.showinfo'):
     app.process();settle()
    self.assertTrue(app.capture_visible);self.assertEqual(app.input.get('1.0','end').strip(),'Avanzar la tarea')
    with patch('app.main.interpret',side_effect=RuntimeError('Servidor no disponible')),patch('app.main.messagebox.showerror'):
     app.process();settle()
    self.assertTrue(app.capture_visible);self.assertEqual(app.store.setting('draft'),'Avanzar la tarea')
   finally:app.close()
 def test_board_pages_fit_without_scrollbars(self):
  from app.main import App
  from tkinter import ttk
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
   app=App()
   try:
    tasks=[]
    for i in range(35):
     d=fresh(f'Tarea {i}');d['status']=['Pendiente','En curso','Esperando','Terminado'][i%4];tasks.append(d)
    app.store.apply(tasks);app.change_view('Todas');app.geometry('1100x740');app.update()
    # Windows applies/clamps native geometry asynchronously; wait for the
    # initial centering pass before measuring each page's visible bounds.
    until=time.monotonic()+.2
    while time.monotonic()<until:app.update();time.sleep(.01)
    for mode in ['table','cards']:
     app.set_layout(mode);app.update();board=app.board
     seen=set()
     for index in range(len(board.pages)):
      board.page=index;board.render();app.update()
      self.assertEqual(board.canvas.yview(),(0.0,1.0));self.assertEqual(board.canvas.xview(),(0.0,1.0))
      for hit in board.hits:
       if hit[4]=='item':
        seen.add(hit[5]);self.assertGreaterEqual(hit[1],0);self.assertLessEqual(hit[3],board.canvas.winfo_height())
     self.assertEqual(seen,{d['id'] for d in tasks})
     self.assertFalse(any(isinstance(w,ttk.Scrollbar) for w in board.winfo_children()))
   finally:app.close()
