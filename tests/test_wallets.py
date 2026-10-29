from contextlib import closing
import json,os,sqlite3,sys,tempfile,time,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from app.core import Store,PEOPLE,ALIASES
from app.finance import Finance,totals
from app.wallets import WalletBook,SETTING,DRAFTS,profile,empty_profile

FIRST='0x'+'12'*20
SECOND='0x'+'ab'*20

class WalletTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'test.sqlite3');self.book=WalletBook(self.store)
    def tearDown(self):self.store.db.close();self.tmp.cleanup()
    def test_save_reopen_backup_and_rename_preserve_address_owner(self):
        Finance(self.store);p=self.store.people()[0]
        before=totals(Finance(self.store).rows())
        self.book.draft(p,'partial');self.book.save({p:FIRST})
        self.assertEqual(self.book.drafts(),{});self.assertEqual(self.book.values(),{p:profile(FIRST)})
        self.assertEqual(totals(Finance(self.store).rows()),before)
        zips=list((self.store.path.parent/'backups/Finanzas').glob('*.zip'))
        with zipfile.ZipFile(zips[-1]) as z:
            db_path=Path(self.tmp.name)/'restore.sqlite3';db_path.write_bytes(z.read('manager.sqlite3'))
        with closing(sqlite3.connect(db_path)) as db:
            self.assertEqual(json.loads(db.execute('SELECT value FROM settings WHERE key=?',(SETTING,)).fetchone()[0]),{p:profile(FIRST)})
        second=Store(self.store.path)
        try:self.assertEqual(WalletBook(second).values(),{p:profile(FIRST)})
        finally:second.db.close()
        self.book.draft(p,'new draft');names=self.store.people();names[0]='Renamed person'
        self.store.rename_people(names)
        self.assertEqual(self.book.values(),{names[0]:profile(FIRST)});self.assertEqual(self.book.drafts(),{names[0]:profile('new draft')})
        with self.assertRaises(ValueError):self.store.rename_people(['Solo'])
    def test_validation_import_conflict_and_other_project_isolation(self):
        people=self.store.people();self.book.save({people[0]:FIRST})
        for bad in ('0xabc','0x'+'z'*40,'a seed phrase',None):
            with self.assertRaises(ValueError):self.book.save({people[1]:bad})
        path=Path(self.tmp.name)/'initial.almwallets'
        value=dict(product='AnimationLoverWallets',schema=1,project='main',network='USDT BEP20 / BSC',wallets={people[1]:SECOND})
        path.write_text(json.dumps(value));self.book.save(self.book.read_import(path),replace=False)
        self.assertEqual(self.book.values(),{people[0]:profile(FIRST),people[1]:profile(SECOND)})
        with self.assertRaises(ValueError):self.book.save({people[2]:FIRST,people[0]:SECOND},replace=False)
        self.assertNotIn(people[2],self.book.values())
        value['project']='personal';path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):self.book.read_import(path)
        other=Store(Path(self.tmp.name)/'other.sqlite3');other.project_id='personal'
        try:
            with self.assertRaises(ValueError):WalletBook(other)
            self.assertIsNone(other.setting(SETTING))
        finally:other.db.close()
        self.book.save({people[0]:''});self.assertEqual(self.book.values()[people[0]],empty_profile())
    def test_backup_failure_does_not_undo_local_save(self):
        p=self.store.people()[0]
        with patch.object(self.store,'backup',side_effect=OSError('offline')):self.book.save({p:FIRST})
        self.assertEqual(self.book.values()[p],profile(FIRST));self.assertIn('Respaldo pendiente',self.book.backup_warning)

    def test_legacy_addresses_and_drafts_preserved_before_edit(self):
        p,q=self.store.people()[:2]
        self.store.setting(SETTING,{p:FIRST,q:''});self.store.setting(DRAFTS,{p:SECOND})
        self.assertEqual(self.book.values()[p],profile(FIRST))
        self.assertEqual(self.book.drafts()[p],profile(SECOND))
        self.assertEqual(self.store.setting(SETTING)[p],FIRST)
        updated=profile(FIRST);updated['kast']='@team.member';self.book.save({p:updated})
        self.assertEqual(self.book.values()[p],updated);self.assertEqual(self.book.values()[q],empty_profile())

    def test_crypto_kast_or_both_and_import_without_erasing_other_method(self):
        people=self.store.people();crypto={'crypto':{'asset':'USDT','network':'TRON / TRC20','address':'T'+'a'*33},'kast':''}
        kast={'crypto':empty_profile()['crypto'],'kast':'@team.member'}
        both=profile(crypto);both['kast']='another.member'
        self.book.save({people[0]:crypto,people[1]:kast,people[2]:both})
        self.assertEqual(self.book.values(),dict(zip(people[:3],[crypto,kast,both])))
        path=Path(self.tmp.name)/'new.almwallets'
        data=dict(product='AnimationLoverWallets',schema=2,project='main',wallets={people[0]:kast})
        path.write_text(json.dumps(data));self.book.save(self.book.read_import(path),replace=False)
        self.assertEqual(self.book.values()[people[0]]['crypto'],crypto['crypto'])
        self.assertEqual(self.book.values()[people[0]]['kast'],kast['kast'])
        partial=empty_profile();partial['crypto']['asset']='USDC'
        self.book.draft(people[3],partial)
        with self.assertRaises(ValueError):self.book.save({people[3]:partial})
        self.assertEqual(self.book.drafts()[people[3]],partial)
        self.assertNotIn(people[3],self.book.values())

@unittest.skipUnless(sys.platform=='win32' or os.getenv('DISPLAY'),'Requiere escritorio')
class WalletGuiTests(unittest.TestCase):
    def test_fields_copy_persistence_project_isolation_and_layout(self):
        from app.main import App
        from app.windowing import place_window
        people=list(PEOPLE);aliases=dict(ALIASES)
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'LOCALAPPDATA':tmp}):
            app=App()
            try:
                app.finance();view=app.finance_view;view.show('Billeteras');app.update();wallets=view.wallet_view
                self.assertEqual(list(wallets.person_buttons),app.store.people())
                self.assertTrue(wallets.winfo_ismapped());self.assertFalse(view.table.winfo_ismapped())
                p=app.store.people()[0]
                for key,value in profile(FIRST)['crypto'].items():wallets.fields[key].set(value)
                wallets.fields['kast'].set('@test.member');wallets.save();wallets.copy('address')
                self.assertEqual(app.clipboard_get(),FIRST)
                wallets.copy('kast');self.assertEqual(app.clipboard_get(),'@test.member')
                both=profile(FIRST);both['kast']='@test.member'
                self.assertEqual(wallets.book.values(),{p:both})
                q=app.store.people()[1];wallets.person_buttons[q].invoke();wallets.fields['kast'].set('@kast.only');wallets.save()
                self.assertEqual(wallets.book.values()[q]['crypto'],empty_profile()['crypto'])
                wallets.fields['kast'].set('partial draft')
                self.assertEqual(wallets.book.drafts()[q]['kast'],'partial draft')
                view.show('Resumen');app.update();self.assertTrue(view.table.winfo_ismapped())
                view.show('Billeteras');app.update();self.assertEqual(wallets.fields['kast'].get(),'partial draft')
                wallets.person_buttons[p].invoke();self.assertEqual(wallets.fields['address'].get(),FIRST)
                for size in ('1000x680','780x520'):
                    app.geometry(size);app.update()
                    until=time.monotonic()+.15
                    while time.monotonic()<until:app.update();time.sleep(.01)
                    for widget in wallets.controls+list(wallets.person_buttons.values())+[wallets.save_button,wallets.import_button,wallets.note]:
                        self.assertGreaterEqual(widget.winfo_rooty(),app.winfo_rooty())
                        self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),app.winfo_rooty()+app.winfo_height())
                        self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),app.winfo_rootx()+app.winfo_width())
                if os.getenv('ALM_SCREENSHOT'):
                    from PIL import ImageGrab
                    place_window(app);app.update();ImageGrab.grab().save(os.environ['ALM_SCREENSHOT'].replace('.png','-wallets.png'))
                path=Path(tmp)/'personal.almproject'
                path.write_text(json.dumps(dict(product='AnimationLoverProject',schema=1,project=dict(id='wallet-test',name='Personal project',personal=True),expenses=[])))
                app.projects.import_project(app.projects.preview_import(path));app.switch_project('wallet-test');app.finance();app.update()
                self.assertNotIn('Billeteras',app.finance_view.tabs);self.assertIsNone(app.store.setting(SETTING))
                app.switch_project('main');app.finance();view.show('Billeteras');app.update()
                self.assertEqual(wallets.book.values()[p],both)
                wallets.select(q);self.assertEqual(wallets.fields['kast'].get(),'partial draft')
            finally:app.close();PEOPLE[:]=people;ALIASES.clear();ALIASES.update(aliases)
