import copy,json,os,sqlite3,sys,tempfile,time,unittest,zipfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from app.core import Store,PEOPLE,ALIASES,fresh
from app.projects import Projects
from app.finance import Finance,entry,totals

def config():
    return dict(product='AnimationLoverProject',schema=1,project=dict(id='personal-test',name='Proyecto personal',personal=True,
                categories=['Créditos IA','Suscripciones','Infra','APIs','Otros'],providers=['Proveedor A','Otras'],platforms=['Fanvue']),
                expenses=[dict(description='Servicio inicial',cents=1700,category='Créditos IA',provider='Proveedor A'),
                          dict(description='Suscripción inicial',cents=300,category='Suscripciones')])

class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.root=Store(self.base/'manager.sqlite3');self.projects=Projects(self.root)
    def tearDown(self):self.projects.close();self.temp.cleanup()
    def install(self):
        path=self.base/'project.almproject';path.write_text(json.dumps(config()));prepared=self.projects.preview_import(path);self.projects.import_project(prepared)
        return self.projects.open('personal-test')
    def test_separate_tasks_finances_settings_and_legacy_unchanged(self):
        task=fresh('Original');self.root.apply([task]);finance=Finance(self.root)
        d=entry('Gasto');d.update(person=self.root.people()[1],amount=1100,description='Original expense',funding='Bolsillo personal');finance.save([d])
        personal=self.install();before=copy.deepcopy(self.root.get(task['id']))
        p=fresh('Personal task',author=personal.people()[0]);personal.apply([p])
        self.assertEqual(self.root.get(task['id']),before);self.assertIsNone(self.root.get(p['id']));self.assertIsNone(personal.get(task['id']))
        self.assertEqual(personal.get(p['id'])['owners'],personal.people())
        self.assertEqual(totals(finance.rows())['debt_total'],1100)
        self.assertEqual(totals(Finance(personal).rows())['free'],-2000)
        personal.setting('draft','private draft');personal.setting('project_context','Personal guidance')
        self.assertIsNone(self.root.setting('draft'));self.assertIsNone(self.root.setting('project_context'))
        self.root.setting('model','local-model');self.assertEqual(personal.setting('model'),'local-model')
        personal.setting('model','new-local-model');self.assertEqual(self.root.setting('model'),'new-local-model')
        personal.undo();self.assertEqual(personal.items(),[]);self.assertEqual(self.root.get(task['id']),before)
    def test_project_import_rejected_without_partial_data_and_no_duplicate(self):
        path=self.base/'test.almproject'
        for id in ['../outside','main','UPPER','a/b']:
            value=config();value['project']['id']=id;path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):self.projects.preview_import(path)
        value=config();value['expenses'][0]['cents']='17';path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):self.projects.preview_import(path)
        self.assertEqual(len(self.projects.list()),1)
        self.install();path.write_text(json.dumps(config()))
        with self.assertRaises(ValueError):self.projects.preview_import(path)
        self.assertEqual(len(Finance(self.projects.open('personal-test')).rows()),2)
    def test_registry_failure_rolls_back_import_directory(self):
        path=self.base/'test.almproject';path.write_text(json.dumps(config()));prepared=self.projects.preview_import(path)
        self.root.db.execute("CREATE TRIGGER fail_projects BEFORE INSERT ON settings WHEN NEW.key='projects' BEGIN SELECT RAISE(ABORT,'test'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.projects.import_project(prepared)
        self.assertFalse((self.base/'projects/personal-test').exists());self.assertEqual(len(self.projects.list()),1)
    def test_backups_include_every_project_separately_and_receipts(self):
        personal=self.install();f=Finance(personal);p=self.base/'proof.txt';p.write_text('Private proof')
        d=f.rows()[0];d['attachments']=[f.attachment(p)];f.save([d])
        destination=self.base/'drive';self.root.setting('backup_folder',str(destination))
        personal.backup()
        self.assertTrue(list(destination.glob('*.sqlite3')))
        zips=list((destination/'Proyectos/personal-test/Finanzas').glob('*.zip'));self.assertTrue(zips)
        with zipfile.ZipFile(zips[-1]) as z:self.assertEqual(z.read('finance_receipts/'+d['attachments'][0]['file']),b'Private proof')
        self.assertEqual(personal.setting('backup_folder'),str(destination))
        with closing(sqlite3.connect(next(destination.glob('*.sqlite3')))) as db:
            self.assertIn('personal-test',db.execute("SELECT value FROM settings WHERE key='projects'").fetchone()[0])
    def test_provider_and_platform_constraints_are_project_local(self):
        personal=self.install();f=Finance(personal)
        d=entry('Gasto');d.update(person=personal.people()[0],description='Credits',amount=100,category='Créditos IA',funding='Bolsillo personal')
        with self.assertRaises(ValueError):f.save([d])
        d.update(provider='Otras')
        with self.assertRaises(ValueError):f.save([d])
        d['provider_other']='New provider';f.save([d])
        r=entry('Retiro');r.update(description='Unsupported source',platform='Patreon',gross=100,amount=100)
        with self.assertRaises(ValueError):f.save([r])
        self.assertEqual(Finance(self.root).platforms(),['Fanvue','Patreon'])

@unittest.skipUnless(sys.platform=='win32' or os.getenv('DISPLAY'),'Requiere escritorio')
class ProjectGuiTests(unittest.TestCase):
    def test_switch_preserves_both_drafts_finances_and_starts_main(self):
        from app.main import App
        people=list(PEOPLE);aliases=dict(ALIASES)
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App()
            try:
                path=Path(folder)/'test.almproject';path.write_text(json.dumps(config()));app.projects.import_project(app.projects.preview_import(path))
                app.project_selector.configure(values=[p['name'] for p in app.projects.list()])
                original=fresh('Main task');app.store.apply([original]);app.input.insert('1.0','Main draft');app.save_draft()
                self.assertTrue(app.switch_project('personal-test'));app.update()
                self.assertEqual(app.store.items(),[]);self.assertEqual(PEOPLE,[people[0]])
                self.assertFalse(app.nav_buttons['Por persona'].winfo_ismapped());self.assertFalse(app.people_filter.winfo_ismapped())
                app.input.insert('1.0','Personal draft');app.save_draft();personal_task=app.new_item();personal_task['title']='Personal task';app.store.apply([personal_task])
                app.finance();app.update();v=app.finance_view
                self.assertNotIn('Por persona',v.tabs);self.assertEqual(v.ledger.platforms(),['Fanvue']);self.assertEqual(v.balance['free'],-2000)
                c=v.capture('Gasto');app.update();c.box.insert('1.0','Personal finance draft');c.changed();app.update()
                self.assertTrue(app.switch_project('main'));app.update()
                self.assertEqual(app.store.items()[0]['id'],original['id']);self.assertEqual(app.input.get('1.0','end').strip(),'Main draft')
                self.assertTrue(app.nav_buttons['Por persona'].winfo_ismapped());self.assertEqual(len(PEOPLE),5)
                app.finance();app.update();self.assertEqual(app.finance_view.ledger.rows(),[])
                self.assertTrue(app.switch_project('personal-test'));app.finance();app.update()
                self.assertEqual(app.input.get('1.0','end').strip(),'Personal draft')
                self.assertEqual(c.box.get('1.0','end').strip(),'Personal finance draft')
                self.assertIs(app.finance_view,v);self.assertEqual(app.projects.context('personal-test')['other_projects'],['Animation Lover'])
                if os.getenv('ALM_SCREENSHOT'):
                    from PIL import ImageGrab
                    from app.windowing import place_window
                    v.leave_capture();place_window(app);app.update();ImageGrab.grab().save(os.environ['ALM_SCREENSHOT'].replace('.png','-personal-project.png'))
                app.close();app=None
                second=App()
                try:
                    self.assertEqual(second.project_id,'main');self.assertEqual(second.project_name.get(),'Animation Lover')
                    self.assertEqual(second.store.get(original['id'])['title'],'Main task')
                finally:second.close()
            finally:
                if app:app.close()
                PEOPLE[:]=people;ALIASES.clear();ALIASES.update(aliases)
    def test_project_switch_is_blocked_during_processing_or_open_edit(self):
        from app.main import App
        import tkinter as tk
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App()
            try:
                path=Path(folder)/'project.almproject';path.write_text(json.dumps(config()));app.projects.import_project(app.projects.preview_import(path))
                app.busy=True
                with patch('app.main.messagebox.showinfo'):self.assertFalse(app.switch_project('personal-test'))
                app.busy=False;window=tk.Toplevel(app);app.update()
                with patch('app.main.messagebox.showinfo'):self.assertFalse(app.switch_project('personal-test'))
                window.destroy();self.assertTrue(app.switch_project('personal-test'));app.update()
                with patch('app.main.interpret',return_value={'project_mismatch':True}),patch('app.main.messagebox.showinfo'):
                    app.input.insert('1.0','A task for a different project');app.process()
                    end=time.monotonic()+3
                    while app.busy and time.monotonic()<end:app.update();time.sleep(.02)
                self.assertEqual(app.store.items(),[])
            finally:app.close()
