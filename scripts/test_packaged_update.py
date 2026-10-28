"""Prueba Windows: helper real, reemplazo, reinicio y datos conservados."""
import json,os,shutil,sqlite3,subprocess,sys,tempfile,time,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import __version__
from app.updater import EXE,HELPER,PRODUCT,atomic_json,digest,prepare_job
from app.core import Store,fresh,PEOPLE
from app.finance import Finance,entry,totals

def stop_child(root,pid=None):
    if pid:
        subprocess.run(['taskkill','/PID',str(pid),'/T','/F'],capture_output=True)
        from app.updater import wait_pid
        wait_pid(pid,20)
        return
    # Solo procesos cuyo ejecutable esté dentro de la instalación temporal de prueba.
    escaped=str(root/EXE).replace("'","''")
    script=f"Get-CimInstance Win32_Process | Where-Object {{ $_.ExecutablePath -eq '{escaped}' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"
    subprocess.run(['powershell','-NoProfile','-Command',script],check=True,capture_output=True)

def main():
    if os.name!='nt':return
    distribution=Path(sys.argv[1]).resolve();package=Path(sys.argv[2]).resolve()
    with tempfile.TemporaryDirectory() as folder:
        base=Path(folder);root=base/'installed'
        if len(sys.argv)>3:
            from app.updater import safe_path,inventory
            root.mkdir()
            with zipfile.ZipFile(sys.argv[3]) as z:
                for entry in z.infolist():
                    if entry.is_dir():continue
                    prefix=PRODUCT+'/'
                    if not entry.filename.startswith(prefix):raise ValueError('Paquete base incorrecto')
                    rel=entry.filename[len(prefix):]
                    if rel!='installation.json':safe_path(rel)
                    dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(entry))
            base_info=json.loads((root/'installation.json').read_text())
            assert base_info['product']==PRODUCT
            for rel,record in inventory(base_info['files']).items():assert digest(root/rel)==record['sha256']
        else:shutil.copytree(distribution,root)
        data=base/'profile';os.environ['LOCALAPPDATA']=str(data)
        info=json.loads((root/'installation.json').read_text());installed=info['version'] if len(sys.argv)>3 else '0.1.9';info['version']=installed;atomic_json(root/'installation.json',info)
        store=Store();card=fresh('Prueba de conservación');store.apply([card]);store.setting('model','modelo-de-prueba');store.setting('draft','borrador conservado');db=store.path
        finance=Finance(store);proof=base/'proof.txt';proof.write_text('Synthetic finance receipt')
        expense=entry('Gasto');expense.update(description='Synthetic expense',person=PEOPLE[0],funding='Bolsillo personal',amount=1250,attachments=[finance.attachment(proof)])
        finance.save([expense]);store.db.close()
        before=digest(db)
        # Copia independiente del helper para simular la llamada de la aplicación.
        import app.updater as updater
        sys._alm_helper=False
        jobdir=prepare_job(package,root,installed,db.parent,expected_to=__version__)
        (jobdir/'go').write_text('go')
        end=time.monotonic()+110
        try:
            while not (jobdir/'result.json').exists():
                if time.monotonic()>end:raise RuntimeError('El actualizador no terminó.')
                time.sleep(.3)
            result=json.loads((jobdir/'result.json').read_text());assert result['success'],result
            assert (jobdir/'healthy.json').exists()
            check=Store(db);assert check.get(card['id'])['title']==card['title'];assert check.setting('model')=='modelo-de-prueba';assert check.setting('draft')=='borrador conservado';f=Finance(check);assert totals(f.rows())['debt_total']==1250;assert (f.media/expense['attachments'][0]['file']).read_text()=='Synthetic finance receipt';check.db.close()
            assert json.loads((root/'installation.json').read_text())['version']==__version__
            assert (jobdir/'backup'/EXE).exists()
            print('Actualización con helper real, reinicio confirmado y datos conservados.')
        finally:
            receipt=json.loads((jobdir/'result.json').read_text()) if (jobdir/'result.json').exists() else {}
            stop_child(root,receipt.get('child_pid'));time.sleep(3)
if __name__=='__main__':main()
