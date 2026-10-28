import tempfile, unittest, datetime as dt
from pathlib import Path
from app.core import Store,fresh,today,person,date_value,urgency
class CoreTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'test.sqlite3')
 def tearDown(self):self.s.db.close();self.tmp.cleanup()
 def test_partial_update_undo_and_restart(self):
  d=fresh('Videos');d['pending']=['Editar','Publicar'];self.s.apply([d]);d['pending']=['Publicar'];d['owners']=['Persona 1'];self.s.apply([d]);self.s.undo();self.assertEqual(self.s.get(d['id'])['pending'],['Editar','Publicar'])
  second=Store(self.s.path);self.assertEqual(len(second.items()),1);second.db.close()
 def test_invalid_batch_atomic(self):
  a=fresh('Bien');b=fresh('Mal');b['deadline']='no';self.assertRaises(ValueError,self.s.apply,[a,b]);self.assertEqual(self.s.items(),[])
 def test_meeting_no_duplicate_and_undo(self):
  d=fresh('Reunión');d['recurrence']='tuesday';self.s.apply([d]);d['status']='Terminado';self.s.apply([d]);self.assertEqual(len(self.s.items()),2);self.s.apply([d]);self.assertEqual(len(self.s.items()),2);self.s.undo();self.s.undo();self.assertEqual(len(self.s.items()),1)
 def test_alias_month_and_overdue(self):
  self.assertEqual(person('Persona 1'),'Persona 1');self.assertEqual(date_value('2028-02'),'2028-02-29');d=fresh('A');d['deadline']='2020-01-01';self.assertEqual(urgency(d),3);d['status']='Terminado';self.assertEqual(urgency(d),0)
 def test_backup_restorable(self):
  d=fresh('Persistir');self.s.apply([d]);p=self.s.backup();other=Store(p);self.assertEqual(other.get(d['id'])['title'],'Persistir');other.db.close()
if __name__=='__main__':unittest.main()
