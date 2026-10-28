"""Prueba Windows: helper real, reemplazo, reinicio y datos conservados."""
import json,os,shutil,sqlite3,subprocess,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import __version__
from app.updater import EXE,HELPER,PRODUCT,atomic_json,digest,prepare_job
from app.core import Store,fresh

def stop_child(root):
    # Solo procesos cuyo ejecutable esté dentro de la instalación temporal de prueba.
    escaped=str(root/EXE).replace("'","''")
    script=f"Get-CimInstance Win32_Process | Where-Object {{ $_.ExecutablePath -eq '{escaped}' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"
    subprocess.run(['powershell','-NoProfile','-Command',script],check=True,capture_output=True)

def main():
    if os.name!='nt':return
    distribution=Path(sys.argv[1]).resolve();package=Path(sys.argv[2]).resolve()
    with tempfile.TemporaryDirectory() as folder:
        base=Path(folder);root=base/'installed';shutil.copytree(distribution,root)
        data=base/'profile';os.environ['LOCALAPPDATA']=str(data)
        info=json.loads((root/'installation.json').read_text());info['version']='0.1.9';atomic_json(root/'installation.json',info)
        store=Store();card=fresh('Prueba de conservación');store.apply([card]);store.setting('model','modelo-de-prueba');store.setting('draft','borrador conservado');db=store.path;store.db.close()
        before=digest(db)
        # Copia independiente del helper para simular la llamada de la aplicación.
        import app.updater as updater
        sys._alm_helper=False
        jobdir=prepare_job(package,root,'0.1.9',db.parent,expected_to=__version__)
        (jobdir/'go').write_text('go')
        end=time.monotonic()+110
        try:
            while not (jobdir/'result.json').exists():
                if time.monotonic()>end:raise RuntimeError('El actualizador no terminó.')
                time.sleep(.3)
            result=json.loads((jobdir/'result.json').read_text());assert result['success'],result
            assert (jobdir/'healthy.json').exists()
            check=Store(db);assert check.get(card['id'])['title']==card['title'];assert check.setting('model')=='modelo-de-prueba';assert check.setting('draft')=='borrador conservado';check.db.close()
            assert json.loads((root/'installation.json').read_text())['version']==__version__
            assert (jobdir/'backup'/EXE).exists()
            print('Actualización con helper real, reinicio confirmado y datos conservados.')
        finally:
            stop_child(root);time.sleep(3)
if __name__=='__main__':main()
