import copy,os,sys,tempfile,unittest
from types import SimpleNamespace
from app.board import initials,avatar_color,due_label,group_for
from app.core import fresh,PEOPLE

class BoardHelpers(unittest.TestCase):
 def test_labels(self):
  self.assertEqual(initials('Ana García'),'AG');self.assertEqual(due_label('2026-10-30'),'30 oct')
  self.assertEqual(avatar_color('Equipo'),avatar_color('Equipo'))
  task=fresh('Prueba');task.update(planned='2020-01-01',deadline='2020-01-01')
  self.assertEqual(group_for(task),'Vencidas');task['status']='Terminado';self.assertEqual(group_for(task),'Terminadas')

@unittest.skipUnless(sys.platform=='win32' or os.getenv('DISPLAY'),'Requiere escritorio')
class BoardInteractions(unittest.TestCase):
 def test_table_cards_hover_selection_and_filter_preserve_tasks(self):
  from app.main import App
  with tempfile.TemporaryDirectory() as tmp:
   os.environ['LOCALAPPDATA']=tmp;app=App()
   try:
    tasks=[]
    for title,status,kind in [('Preparar material','Pendiente','Tarea'),('Revisar propuesta','En curso','Idea'),('Organizar referencias','Esperando','Roadmap'),('Entrega revisada','Terminado','Nota')]:
     d=fresh(title);d.update(status=status,kind=kind,summary='Resumen de prueba para revisar la organización visual del tablero.',owners=[PEOPLE[0]],priority='Alta');tasks.append(d)
    app.store.apply(tasks);app.change_view('Todas');app.update();board=app.board
    before=copy.deepcopy(app.store.items());opened=[];board.on_open=lambda:opened.append(board.selected_id)
    hit=next(h for h in board.hits if h[4]=='item')
    self.assertGreater(hit[2]-hit[0],100)
    event=SimpleNamespace(x=(hit[0]+hit[2])/2,y=(hit[1]+hit[3])/2,x_root=100,y_root=100)
    board.motion(event);self.assertEqual(board.hover_id,hit[5]);board.click(event);self.assertEqual(app.selected(),hit[5])
    board.double_click(event);self.assertEqual(opened,[hit[5]])
    app.set_layout('cards');app.update();hit=next(h for h in board.hits if h[4]=='item')
    event=SimpleNamespace(x=(hit[0]+hit[2])/2,y=(hit[1]+hit[3])/2,x_root=100,y_root=100)
    board.motion(event);board.click(event);self.assertEqual(opened[-1],hit[5])
    self.assertEqual(app.store.items(),before)
    app.search.set('Revisar propuesta');app.update();self.assertEqual([d['title'] for d in board.items],['Revisar propuesta'])
    app.search.set('');app.set_layout('table');app.update()
    self.assertEqual(app.store.items(),before);self.assertEqual(app.store.setting('board_layout'),'table')
    app.editor(tasks[0]);app.update()
    from tkinter import ttk
    import tkinter as tk
    window=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel) and w.state()!='withdrawn')
    def walk(w):
     for child in w.winfo_children():
      yield child
      yield from walk(child)
    widgets=list(walk(window))
    title=next(w for w in widgets if isinstance(w,ttk.Entry) and not isinstance(w,ttk.Combobox))
    title.delete(0,'end');title.insert(0,'Material preparado')
    save=next(w for w in widgets if isinstance(w,ttk.Button) and w.cget('text')=='Guardar cambios');save.invoke();app.update()
    updated=app.store.get(tasks[0]['id']);self.assertEqual(updated['title'],'Material preparado');self.assertEqual(updated['owners'],tasks[0]['owners']);self.assertEqual(updated['summary'],tasks[0]['summary'])
    if os.getenv('ALM_SCREENSHOT'):
     import time
     from PIL import ImageGrab
     app.geometry(f'{min(1340,app.winfo_screenwidth()-80)}x{min(860,app.winfo_screenheight()-100)}');app.update();app.update()
     time.sleep(.1);app.update();ImageGrab.grab().save(os.environ['ALM_SCREENSHOT'].replace('.png','-table.png'))
     app.set_layout('cards');app.update();time.sleep(.1);app.update();ImageGrab.grab().save(os.environ['ALM_SCREENSHOT'].replace('.png','-cards.png'))
   finally:app.close()
if __name__=='__main__':unittest.main()
