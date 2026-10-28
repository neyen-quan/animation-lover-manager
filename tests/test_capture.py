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
