import copy
import tempfile
import unittest
from pathlib import Path
from app.ai import prepare_task_dates
from app.core import Store, date_value, fresh


class TaskDateTests(unittest.TestCase):
    def test_noisy_model_dates_save_and_updates_keep_other_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'test.sqlite3')
            try:
                task=fresh('Organizar contenido')
                response={'creates':[{'title':task['title'],'planned':'2 026-10-29','deadline':'2026 – 11'}]}
                original=copy.deepcopy(response)
                prepared=prepare_task_dates(response)
                self.assertEqual(prepared['questions'],[])
                self.assertEqual(response,original)
                task.update(prepared['creates'][0]);task['pending']=['Revisar ideas','Preparar material']
                store.apply([task])
                saved=store.get(task['id'])
                self.assertEqual(saved['planned'],'2026-10-29')
                self.assertEqual(saved['deadline'],'2026-11-30')
                update={'updates':[{'id':task['id'],'patch':{'planned':' 2026 - 11 - 01 '}}]}
                prepared=prepare_task_dates(update,store.items())
                self.assertEqual(prepared['questions'],[])
                saved.update(prepared['updates'][0]['patch']);store.apply([saved])
                updated=store.get(task['id'])
                self.assertEqual(updated['planned'],'2026-11-01')
                for key in ('deadline','pending','author','owners','completed'):
                    self.assertEqual(updated[key],task[key])
            finally:store.db.close()

    def test_invalid_dates_ask_and_never_guess_today(self):
        for value in ('2026-02-30','2026-13','29/10/2026','mañana',None,20261029,''):
            with self.subTest(value=value):
                result=prepare_task_dates({'creates':[{'title':'Revisar material','planned':value}]})
                self.assertTrue(result['questions'])
                self.assertIn('fecha prevista',result['questions'][0])
                self.assertIn('Revisar material',result['questions'][0])
                self.assertEqual(result['creates'][0]['planned'],value)
                with self.assertRaises(ValueError):date_value(value)
        self.assertEqual(date_value(' 2\u00a0028 ‑ 02 '),'2028-02-29')

    def test_update_dates_are_checked_against_existing_deadline(self):
        task=fresh('Publicar');task.update(planned='2026-10-29',deadline='2026-10-30')
        result=prepare_task_dates({'updates':[{'id':task['id'],'patch':{'planned':'2026-11-01'}}]},[task])
        self.assertTrue(result['questions'])
        self.assertIn('después',result['questions'][0])
        unchanged=prepare_task_dates({'updates':[{'id':task['id'],'patch':{'summary':'Avance'}}]},[task])
        self.assertEqual(unchanged['questions'],[])
        self.assertEqual(unchanged['updates'][0]['patch'],{'summary':'Avance'})

    def test_invalid_batch_is_atomic_and_error_is_in_spanish(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'test.sqlite3')
            try:
                first=fresh('Primera');second=fresh('Segunda');second['deadline']='2026-02-30'
                with self.assertRaisesRegex(ValueError,'fecha límite.*Segunda'):
                    store.apply([first,second])
                self.assertEqual(store.items(),[])
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM history').fetchone()[0],0)
            finally:store.db.close()
