"""Paquete completo para instalar, paquete verificable y delta de la versión anterior."""
import hashlib,json,sys,zipfile,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.updater import PRODUCT,EXE,HELPER,digest,safe_path,atomic_json
from app import __version__

def records(root):
    return [{'path':str(p.relative_to(root)).replace('\\','/'),'size':p.stat().st_size,'sha256':digest(p)} for p in sorted(root.rglob('*')) if p.is_file() and p.name!='installation.json']

def update_zip(root,out,files,all_files,old='*',deleted=None):
    manifest={'schema':1,'product':PRODUCT,'kind':'full' if old=='*' else 'patch','from':old,'to':__version__,'files':files,'inventory':all_files,'delete':deleted or []}
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('manifest.json',json.dumps(manifest))
        for f in files:z.write(root/f['path'],'files/'+f['path'])
    return manifest

def package(root,out,repo,previous=None):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    inventory=records(root)
    for r in inventory:safe_path(r['path'])
    assert {EXE,HELPER}<={r['path'] for r in inventory}
    atomic_json(root/'installation.json',{'product':PRODUCT,'version':__version__,'files':inventory})
    full_name=f'{PRODUCT}-Windows-{__version__}.zip'
    with zipfile.ZipFile(out/full_name,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():z.write(p,PRODUCT+'/'+p.relative_to(root).as_posix())
    update_name=f'{PRODUCT}-Actualizar-{__version__}.zip';update_zip(root,out/update_name,inventory,inventory)
    shutil.copy2(root/HELPER,out/HELPER)
    def asset(name):return {'url':f'https://github.com/{repo}/releases/download/v{__version__}/{name}','sha256':digest(out/name),'size':(out/name).stat().st_size}
    feed={'schema':1,'product':PRODUCT,'version':__version__,'notes':'Ventanas emergentes centradas en el monitor del gestor: captura, actualizaciones, ajustes y tarjetas.','full':asset(update_name),'installer':asset(full_name),'patches':[],'bootstrap':asset(HELPER)}
    if previous and Path(previous).exists():
        with zipfile.ZipFile(previous) as z:
            candidate=[p for p in z.namelist() if p.endswith('/installation.json')]
            if len(candidate)!=1:raise ValueError('La versión anterior no tiene inventario único.')
            old=json.loads(z.read(candidate[0]))
        if old['product']!=PRODUCT:raise ValueError('Producto anterior incorrecto.')
        oldfiles={f['path']:f for f in old['files']};newfiles={f['path']:f for f in inventory}
        changed=[f for f in inventory if oldfiles.get(f['path'])!=f]
        deleted=sorted(set(oldfiles)-set(newfiles))
        name=f'{PRODUCT}-Parche-{old["version"]}-a-{__version__}.zip'
        update_zip(root,out/name,changed,inventory,old['version'],deleted)
        entry=asset(name);entry.update({'from':old['version'],'to':__version__});feed['patches'].append(entry)
    atomic_json(out/'latest.json',feed)
    sums={p.name:digest(p) for p in sorted(out.iterdir()) if p.suffix in ('.zip','.exe')}
    (out/'SHA256SUMS.txt').write_text(''.join(f'{v}  {k}\n' for k,v in sums.items()))
    for p in out.glob('*.zip'):
        with zipfile.ZipFile(p) as z:assert z.testzip() is None
    return feed
if __name__=='__main__':
    root,out,repo=sys.argv[1:4]
    previous=sys.argv[4] if len(sys.argv)>4 else None
    print(json.dumps(package(root,out,repo,previous),indent=2))
