import copy
from contextlib import closing
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core import ALIASES, PEOPLE, Store, fresh


class PeopleTests(unittest.TestCase):
    def setUp(self):
        self.people=list(PEOPLE);self.aliases=dict(ALIASES)
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.tmp.name)/'manager.sqlite3')

    def tearDown(self):
        self.store.db.close();self.tmp.cleanup()
        PEOPLE[:]=self.people;ALIASES.clear();ALIASES.update(self.aliases)

    def test_rename_preserves_items_trash_history_undo_and_recovery_copy(self):
        a=fresh('Referencia de Persona 1');a.update(owners=[PEOPLE[1]],summary='Texto original Persona 2')
        b=fresh('Descartada',author=PEOPLE[2]);b.update(deleted=True,owners=[PEOPLE[0]])
        self.store.apply([a,b]);a['pending']=['Revisar'];self.store.apply([a])
        self.store.setting('aliases',{'apodo':PEOPLE[1]})
        names=[f'Integrante {i+1}' for i in range(len(PEOPLE))]
        self.store.rename_people(names);PEOPLE[:]=names
        self.assertEqual(self.store.get(a['id'])['owners'],[names[1]])
        self.assertEqual(self.store.items(deleted=True)[0]['author'],names[2])
        self.assertEqual(self.store.get(a['id'])['summary'],'Texto original Persona 2')
        self.assertEqual(self.store.setting('aliases'),{'apodo':names[1]})
        self.store.undo();restored=self.store.get(a['id'])
        self.assertEqual(restored['pending'],[]);self.assertEqual(restored['owners'],[names[1]])
        self.store.apply([restored])  # New roster must still validate after undo.
        second=Store(self.store.path)
        try:self.assertEqual(second.setting('people'),names)
        finally:second.db.close()
        recoverable=False
        for path in (self.store.path.parent/'backups').glob('*.sqlite3'):
            with closing(sqlite3.connect(path)) as db:
                value=db.execute('SELECT data FROM items WHERE id=?',(a['id'],)).fetchone()
                recoverable|=bool(value and json.loads(value[0])['author']==self.people[0])
        self.assertTrue(recoverable)

    def test_invalid_roster_does_not_change_existing_data(self):
        d=fresh('Conservar');d['deleted']=True;self.store.apply([d])
        before=copy.deepcopy(self.store.get(d['id']))
        for names in [[],['A'],['A','a','C','D','E'],['A','Todos','C','D','E'],['A','B,C','D','E','F']]:
            with self.assertRaises(ValueError):self.store.rename_people(names)
            self.assertEqual(self.store.get(d['id']),before)
            self.assertIsNone(self.store.setting('people'))

    def test_migration_failure_rolls_back_tasks_history_and_settings(self):
        d=fresh('Conservar');self.store.apply([d])
        before=list(self.store.db.execute('SELECT before,after FROM history'))
        self.store.db.execute("CREATE TRIGGER fail_roster BEFORE INSERT ON settings WHEN NEW.key='people' BEGIN SELECT RAISE(ABORT,'test rollback'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.store.rename_people([f'Integrante {i}' for i in range(len(PEOPLE))])
        self.assertEqual(self.store.get(d['id'])['author'],d['author'])
        self.assertEqual(list(self.store.db.execute('SELECT before,after FROM history')),before)
        self.assertIsNone(self.store.setting('people'))


@unittest.skipUnless(sys.platform=='win32' or os.getenv('DISPLAY'),'Requiere escritorio')
class TeamSettingsTests(unittest.TestCase):
    def test_save_team_with_existing_task_and_backup_folder_feedback(self):
        import tkinter as tk
        from tkinter import ttk
        from app.main import App
        people=list(PEOPLE);aliases=dict(ALIASES)
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App()
            try:
                d=fresh('Conservar tarjeta');d['owners']=[PEOPLE[1]];app.store.apply([d]);app.author.set(PEOPLE[1]);app.filter_person.set(PEOPLE[1])
                app.settings();app.update()
                window=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel) and w.state()!='withdrawn')
                def walk(widget):
                    for child in widget.winfo_children():
                        yield child
                        yield from walk(child)
                widgets=list(walk(window))
                roster=next(w for w in widgets if isinstance(w,tk.Text))
                names=[f'Integrante {i+1}' for i in range(len(PEOPLE))]
                roster.delete('1.0','end');roster.insert('1.0','\n'.join(names))
                save=next(w for w in widgets if isinstance(w,ttk.Button) and w.cget('text')=='Guardar equipo local')
                with patch('app.main.messagebox.askyesno',return_value=True),patch('app.main.messagebox.showinfo'):
                    save.invoke()
                self.assertEqual(app.store.get(d['id'])['owners'],[names[1]])
                self.assertEqual(app.author.get(),names[1]);self.assertEqual(app.filter_person.get(),names[1])
                self.assertEqual(tuple(app.author_box.cget('values')),tuple(names))
                backup_button=next(w for w in widgets if isinstance(w,ttk.Button) and str(w.cget('text')).startswith('Carpeta de respaldo'))
                target=Path(folder)/'synced-backups'
                with patch('app.main.filedialog.askdirectory',return_value=str(target)),patch('app.main.messagebox.showinfo') as info:
                    backup_button.invoke();self.assertTrue(info.called)
                self.assertTrue(list(target.glob('*.sqlite3')))
                self.assertEqual(app.store.setting('backup_folder'),str(target))
                invalid=Path(folder)/'not-a-folder';invalid.write_text('file')
                with patch('app.main.filedialog.askdirectory',return_value=str(invalid)),patch('app.main.messagebox.showerror') as error:
                    backup_button.invoke();self.assertTrue(error.called)
                self.assertEqual(app.store.setting('backup_folder'),str(target))
                window.destroy()
            finally:
                app.close();PEOPLE[:]=people;ALIASES.clear();ALIASES.update(aliases)
