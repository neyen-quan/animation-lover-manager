import copy
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from app.core import Store, PEOPLE, fresh
from app.finance import Finance, entry, cents, totals

class FinanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'manager.sqlite3');self.f=Finance(self.store)
    def tearDown(self):self.store.db.close();self.tmp.cleanup()
    def item(self,kind,amount,**values):
        d=entry(kind);d.update(description=kind,amount=cents(amount),person=PEOPLE[0]);d.update(values);return d
    def test_rounding_and_reject_nonfinite(self):
        self.assertEqual(cents('59.865'),5987)
        self.assertEqual(cents('26,50'),2650)
        for n in ['NaN','Infinity','-1','1,234.56']:
            with self.assertRaises(ValueError):cents(n)
    def test_withdrawal_pending_confirm_is_idempotent(self):
        d=self.item('Retiro','90',gross=10000,fee=1000,platform='Fanvue')
        self.f.save([d]);self.assertEqual(totals(self.f.rows())['cash'],0)
        self.f.confirm(d['id']);self.f.confirm(d['id'])
        self.assertEqual(totals(self.f.rows())['cash'],9000)
        d=self.item('Retiro','40',gross=4050,fee=50,platform='Patreon',include_pending=True)
        self.f.save([d]);self.assertEqual(totals(self.f.rows())['cash'],13000)
        self.f.confirm(d['id']);t=totals(self.f.rows());self.assertEqual(t['cash'],13000);self.assertEqual(t['anticipated'],0)
    def test_personal_company_transfer_reimbursement_not_double_expense(self):
        rows=[self.item('Retiro','500',gross=50000,platform='Patreon',received=True),self.item('Gasto','80',funding='Caja',category='Créditos IA'),self.item('Gasto','70',funding='Bolsillo personal'),self.item('Traspaso personal','20',person=PEOPLE[1],recipient=PEOPLE[0])]
        self.f.save(rows);t=totals(self.f.rows());self.assertEqual(t['cash'],42000);self.assertEqual(t['expenses'],15000);self.assertEqual(t['debt'],{PEOPLE[0]:5000,PEOPLE[1]:2000})
        self.f.save([self.item('Reintegro','50')]);t=totals(self.f.rows());self.assertEqual(t['cash'],37000);self.assertEqual(t['expenses'],15000);self.assertEqual(t['debt_total'],2000)
        before=self.f.rows()
        with self.assertRaises(ValueError):self.f.save([self.item('Reintegro','1')])
        self.assertEqual(self.f.rows(),before)
    def test_edit_void_history_and_stale_revision(self):
        d=self.item('Gasto','20',funding='Bolsillo personal');self.f.save([d]);d=self.f.get(d['id']);old=copy.deepcopy(d)
        d['amount']=3000;self.f.save([d])
        with self.assertRaises(ValueError):self.f.save([old])
        d=self.f.get(d['id']);d['void']=True;self.f.save([d]);self.assertEqual(totals(self.f.rows())['expenses'],0)
        self.assertEqual(self.f.db.execute('SELECT COUNT(*) FROM finance_history').fetchone()[0],3)
    def test_receipt_backup_is_self_contained_and_detects_duplicates(self):
        p=Path(self.tmp.name)/'proof.txt';p.write_text('Synthetic receipt')
        a=self.f.attachment(p);d=self.item('Gasto','20',funding='Bolsillo personal',attachments=[a]);self.f.save([d])
        other=self.item('Gasto','21',funding='Bolsillo personal',attachments=[a]);self.assertEqual(len(self.f.duplicates(other)),1)
        backup=sorted((Path(self.tmp.name)/'backups/Finanzas').glob('*.zip'))[-1]
        with zipfile.ZipFile(backup) as z:
            self.assertEqual(z.read('finance_receipts/'+a['file']),p.read_bytes())
            restore=Path(self.tmp.name)/'restored';z.extractall(restore)
        with closing(sqlite3.connect(restore/'manager.sqlite3')) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM finance').fetchone()[0],1)
        p=self.f.media/a['file'];p.write_text('corrupted')
        with self.assertRaises(ValueError):self.f.save([other])
    def test_bad_batch_does_not_mutate_and_backup_error_is_not_save_failure(self):
        good=self.item('Gasto','20',funding='Bolsillo personal');bad=self.item('Retiro','20',gross=2000,fee=10,platform='Fanvue')
        with self.assertRaises(ValueError):self.f.save([good,bad])
        self.assertEqual(self.f.rows(),[])
        with patch.object(self.store,'backup',side_effect=OSError('offline')):self.f.save([good])
        self.assertEqual(len(self.f.rows()),1);self.assertIn('Guardado',self.f.backup_warning)
    def test_insights_do_not_change_cash_or_duplicate_month(self):
        d=self.item('Insight','700',platform='Fanvue');self.f.save([d]);self.assertEqual(totals(self.f.rows())['cash'],0)
        with self.assertRaises(ValueError):self.f.save([self.item('Insight','800',platform='Fanvue')])
    def test_private_import_once_and_safe_receipt_paths(self):
        d=self.item('Retiro','25',gross=2500,platform='Fanvue',received=True)
        p=Path(self.tmp.name)/'start.almfinance'
        with zipfile.ZipFile(p,'w') as z:z.writestr('finance.json',json.dumps(dict(product='AnimationLoverFinance',schema=1,entries=[d])))
        self.f.save(self.f.read_import(p));self.assertEqual(totals(self.f.rows())['cash'],2500)
        with self.assertRaises(ValueError):self.f.read_import(p)
    def test_roster_rename_preserves_financial_liabilities(self):
        self.f.save([self.item('Gasto','20',funding='Bolsillo personal')]);names=[f'Integrante {i}' for i in range(len(PEOPLE))]
        self.store.rename_people(names);self.assertEqual(totals(self.f.rows())['debt'],{names[0]:2000})

@unittest.skipUnless(sys.platform=='win32' or os.getenv('DISPLAY'),'Requiere escritorio')
class FinanceGuiTests(unittest.TestCase):
    def test_workspace_forms_navigation_and_scaling(self):
        import tkinter as tk
        from app.main import App
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'LOCALAPPDATA':tmp}):
            app=App()
            try:
                app.finance();app.update();view=app.finance_view
                d=entry('Gasto');d.update(description='Suscripción de prueba',person=PEOPLE[0],funding='Bolsillo personal',amount=1200)
                view.ledger.save([d]);view.refresh();app.update()
                for size in ['1000x680','780x520']:
                    app.geometry(size);app.update()
                    for section in ['Resumen','Movimientos','Por persona','Insights mensuales']:
                        view.show(section);app.update()
                        self.assertGreater(view.table.winfo_height(),25)
                        self.assertLessEqual(view.open_button.winfo_rooty()+view.open_button.winfo_height(),app.winfo_rooty()+app.winfo_height())
                app.geometry('1100x760');view.show('Resumen');app.update()
                for kind in ['Retiro','Gasto','Reintegro','Reparto','Insight']:
                    w=view.edit(entry(kind));app.update();self.assertEqual(w.state(),'normal');w.destroy()
                app.change_view('Hoy');app.update();self.assertTrue(app.content.winfo_ismapped());self.assertFalse(view.winfo_ismapped())
                app.finance();app.update()
                if os.getenv('ALM_SCREENSHOT'):
                    from PIL import ImageGrab
                    ImageGrab.grab().save(os.environ['ALM_SCREENSHOT'].replace('.png','-finance.png'))
            finally:app.close()
