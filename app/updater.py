"""Canal HTTPS, validación de paquetes y reemplazo transaccional de archivos."""
from __future__ import annotations
from contextlib import contextmanager
import hashlib, json, os, re, shutil, stat, subprocess, sys, tempfile, time, urllib.parse, urllib.request, uuid, zipfile
from pathlib import Path, PurePosixPath

PRODUCT = 'AnimationLoverManager'
EXE = 'AnimationLoverManager.exe'
HELPER = 'ActualizarAnimationLover.exe'
CHANNEL = 'https://github.com/neyen-quan/animation-lover-manager/releases/latest/download/latest.json'
HOSTS = {'github.com','release-assets.githubusercontent.com','objects.githubusercontent.com','github-releases.githubusercontent.com'}
MAX_ARCHIVE = 700 * 1024**2
MAX_TOTAL = 1800 * 1024**2
MAX_FILES = 12000
class UpdateError(ValueError): pass

def version(v):
    if not isinstance(v,str) or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)',v): raise UpdateError('Versión inválida.')
    return tuple(map(int,v.split('.')))

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024**2),b''): h.update(block)
    return h.hexdigest()

def valid_url(url):
    try:
        u=urllib.parse.urlsplit(url)
        return u.scheme=='https' and u.hostname in HOSTS and not u.username and not u.password and u.port in (None,443) and not u.fragment
    except ValueError:return False

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not valid_url(newurl): raise UpdateError('Redirección fuera de GitHub.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def download(url,destination,limit=MAX_ARCHIVE,progress=None):
    if not valid_url(url):raise UpdateError('Usá una URL HTTPS de GitHub.')
    opener=urllib.request.build_opener(Redirect())
    req=urllib.request.Request(url,headers={'User-Agent':PRODUCT+'-Updater','Accept':'application/octet-stream'})
    dest=Path(destination); dest.parent.mkdir(parents=True,exist_ok=True)
    try:
        with opener.open(req,timeout=45) as response,open(dest,'wb') as f:
            total=int(response.headers.get('Content-Length',0)); count=0
            if total>limit:raise UpdateError('El archivo supera el tamaño permitido.')
            while block:=response.read(256*1024):
                count+=len(block)
                if count>limit:raise UpdateError('La descarga supera el tamaño permitido.')
                f.write(block)
                if progress:progress(count,total)
            f.flush();os.fsync(f.fileno())
    except Exception:
        dest.unlink(missing_ok=True);raise
    return dest

def check(channel,installed):
    version(installed)
    if not valid_url(channel) or not urllib.parse.urlsplit(channel).path.endswith('/latest.json'):raise UpdateError('El canal debe ser una URL HTTPS de GitHub terminada en /latest.json.')
    with tempfile.TemporaryDirectory() as tmp:
        feed=json.loads(download(channel+('&' if '?' in channel else '?')+'check='+str(time.time_ns()),Path(tmp)/'latest.json',256*1024).read_text(encoding='utf-8-sig'))
    if feed.get('schema')!=1 or feed.get('product')!=PRODUCT:raise UpdateError('El canal corresponde a otro producto.')
    version(feed.get('version'))
    if version(feed['version'])<=version(installed):return {'current':True,'version':feed['version'],'installed':installed}
    patches=feed.get('patches',[])
    candidate=next((p for p in patches if p.get('from')==installed and p.get('to')==feed['version']),None) or feed.get('full')
    if not isinstance(candidate,dict) or not valid_url(candidate.get('url','')) or not re.fullmatch('[a-f0-9]{64}',candidate.get('sha256','')):raise UpdateError('No hay un paquete íntegro compatible en el canal.')
    return {'current':False,'version':feed['version'],'installed':installed,'asset':candidate,'notes':feed.get('notes','')}

def safe_path(value):
    if not isinstance(value,str) or not value or '\\' in value or ':' in value or '\x00' in value or len(value)>220:raise UpdateError('Ruta no permitida.')
    parts=value.split('/')
    if any(not p or p in ('.','..') or p.endswith((' ','.')) or re.fullmatch(r'(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?',p) for p in parts):raise UpdateError('Ruta no permitida.')
    if value in (EXE,HELPER):return value
    if parts[0] not in ('_internal','assets') or len(parts)<2:raise UpdateError('El paquete intenta modificar datos ajenos a la aplicación.')
    if any(p.casefold() in ('manager.sqlite3','backups','attachments','.env') for p in parts):raise UpdateError('El paquete intenta modificar datos personales.')
    return value

def inventory(value):
    if not isinstance(value,list) or not value or len(value)>MAX_FILES:raise UpdateError('Inventario inválido.')
    result={};total=0;seen=set()
    for f in value:
        path=safe_path(f.get('path'));fold=path.casefold()
        if fold in seen or not re.fullmatch('[a-f0-9]{64}',f.get('sha256','')):raise UpdateError('Inventario duplicado o hash inválido.')
        if type(f.get('size')) is not int or not 0<=f['size']<=MAX_ARCHIVE:raise UpdateError('Tamaño inválido.')
        total+=f['size'];seen.add(fold);result[path]=f
    if total>MAX_TOTAL:raise UpdateError('Paquete descomprimido demasiado grande.')
    return result

def validate_package(path,installed,expected_hash=None,expected_to=None):
    version(installed)
    path=Path(path)
    if path.stat().st_size>MAX_ARCHIVE:raise UpdateError('Paquete demasiado grande.')
    if expected_hash and digest(path)!=expected_hash:raise UpdateError('SHA-256 del ZIP incorrecto.')
    with zipfile.ZipFile(path) as z:
        entries=z.infolist();names=[x.filename for x in entries]
        if len(names)>MAX_FILES+1 or len(names)!=len(set(n.casefold() for n in names)):raise UpdateError('ZIP con entradas duplicadas.')
        if 'manifest.json' not in names or z.getinfo('manifest.json').file_size>4*1024**2:raise UpdateError('Falta el manifiesto.')
        m=json.loads(z.read('manifest.json'))
        if m.get('schema')!=1 or m.get('product')!=PRODUCT or m.get('kind') not in ('patch','full'):raise UpdateError('Paquete de otro producto o formato.')
        if version(m.get('to'))<=version(installed) or (expected_to and m['to']!=expected_to):raise UpdateError('Versión de destino incorrecta.')
        if m['kind']=='patch' and m.get('from')!=installed:raise UpdateError('El parche no corresponde a la versión instalada.')
        if m['kind']=='full' and m.get('from')!='*':raise UpdateError('Versión de origen incorrecta.')
        files=inventory(m.get('files'));target=inventory(m.get('inventory'))
        if not {EXE,HELPER}<=target.keys():raise UpdateError('Faltan ejecutables obligatorios.')
        removed=m.get('delete',[])
        if not isinstance(removed,list) or len(removed)>MAX_FILES or len(set(removed))!=len(removed):raise UpdateError('Lista de eliminación inválida.')
        for rel in removed:
            safe_path(rel)
            if rel.casefold() in {p.casefold() for p in target}:raise UpdateError('Eliminación contradictoria.')
        if m['kind']=='full' and (files!=target or removed):raise UpdateError('Paquete completo inconsistente.')
        if set(names)!={'manifest.json'}|{'files/'+p for p in files}:raise UpdateError('Archivos no declarados en el ZIP.')
        total=0
        for rel,record in files.items():
            if target.get(rel)!=record:raise UpdateError('Inventario de destino inconsistente.')
            zi=z.getinfo('files/'+rel);total+=zi.file_size
            if stat.S_ISLNK(zi.external_attr>>16) or zi.flag_bits&1 or zi.file_size!=record['size'] or total>MAX_TOTAL:raise UpdateError('Entrada ZIP inválida.')
            h=hashlib.sha256()
            with z.open(zi) as f:
                for block in iter(lambda:f.read(1024**2),b''):h.update(block)
            if h.hexdigest()!=record['sha256']:raise UpdateError('Integridad interna incorrecta: '+rel)
    return m

def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.tmp')
    with open(temp,'w',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

def destination(root,rel):
    safe_path(rel);root=Path(root).resolve();p=root/rel
    # Rechazar enlaces y junctions existentes que escapen a la carpeta del programa.
    cur=p
    while cur!=root:
        if cur.is_symlink() or (hasattr(cur,'is_junction') and cur.is_junction()):raise UpdateError('La instalación contiene un enlace no permitido.')
        cur=cur.parent
    if root not in p.resolve().parents:raise UpdateError('Ruta fuera de la instalación.')
    return p

def installed_version(root,fallback):
    p=Path(root)/'installation.json'
    if not p.exists():return fallback
    info=json.loads(p.read_text(encoding='utf-8'))
    if info.get('product')!=PRODUCT:raise UpdateError('La instalación pertenece a otro producto.')
    version(info.get('version'));return info['version']

def _apply_transaction(package,root,installed,backup,health=None,expected_hash=None,expected_to=None):
    root=Path(root).resolve();backup=Path(backup).resolve()
    if root==backup or root in backup.parents:raise UpdateError('El respaldo debe estar fuera de la instalación.')
    if installed_version(root,installed)!=installed:raise UpdateError('La instalación cambió mientras se preparaba la actualización.')
    m=validate_package(package,installed,expected_hash,expected_to)
    target={f['path']:f for f in m['inventory']};changed={f['path']:f for f in m['files']}
    old_info=root/'installation.json';old_bytes=old_info.read_bytes() if old_info.exists() else None
    old_inventory={}
    if old_bytes:
        old_inventory={x['path']:x for x in json.loads(old_bytes).get('files',[])}
    for rel in m['delete']:
        if rel not in old_inventory:raise UpdateError('Eliminación fuera del inventario instalado.')
    # La parte no incluida en un parche tiene que coincidir con el destino.
    for rel,record in target.items():
        p=destination(root,rel)
        if rel not in changed and (not p.is_file() or digest(p)!=record['sha256']):raise UpdateError('La base instalada está modificada. Instalá el paquete completo.')
    backup.mkdir(parents=True,exist_ok=False);journal=[]
    with tempfile.TemporaryDirectory(prefix='alm-stage-') as tmp:
        stage=Path(tmp)
        with zipfile.ZipFile(package) as z:
            for rel in changed:
                p=stage/rel;p.parent.mkdir(parents=True,exist_ok=True)
                with z.open('files/'+rel) as src,open(p,'wb') as dst:shutil.copyfileobj(src,dst)
        try:
            for rel in list(changed)+m['delete']:
                p=destination(root,rel);existed=p.exists()
                if existed:
                    if not p.is_file():raise UpdateError('El destino no es un archivo.')
                    save=backup/rel;save.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,save)
                journal.append((rel,existed))
                if rel in changed:
                    p.parent.mkdir(parents=True,exist_ok=True)
                    temp=p.with_name(p.name+'.alm-new');shutil.copy2(stage/rel,temp);os.replace(temp,p)
                else:p.unlink(missing_ok=True)
            for rel,record in target.items():
                if digest(destination(root,rel))!=record['sha256']:raise UpdateError('La comprobación posterior falló: '+rel)
            atomic_json(old_info,{'product':PRODUCT,'version':m['to'],'files':m['inventory']})
            if health:health(m['to'])
        except Exception:
            for rel,existed in reversed(journal):
                p=destination(root,rel)
                p.with_name(p.name+'.alm-new').unlink(missing_ok=True)
                if existed:
                    if not p.exists() or digest(p)!=digest(backup/rel):shutil.copy2(backup/rel,p)
                else:p.unlink(missing_ok=True)
            if old_bytes is None:old_info.unlink(missing_ok=True)
            else:old_info.write_bytes(old_bytes)
            raise
    return m

@contextmanager
def install_lock(root):
    path=Path(root)/'.alm-update.lock'
    with open(path,'a+b') as f:
        if f.seek(0,2)==0:f.write(b'0');f.flush()
        f.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as e:raise UpdateError('Ya hay otra actualización en esta instalación.') from e
        try:yield
        finally:
            f.seek(0)
            if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(f,fcntl.LOCK_UN)

def apply_transaction(package,root,installed,backup,health=None,expected_hash=None,expected_to=None):
    with install_lock(root):
        return _apply_transaction(package,root,installed,backup,health,expected_hash,expected_to)

def wait_pid(pid,timeout=90):
    if not pid:return
    if os.name!='nt':raise UpdateError('Instalación automática disponible en Windows.')
    import ctypes
    from ctypes import wintypes
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
    k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];k.WaitForSingleObject.restype=wintypes.DWORD
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=k.OpenProcess(0x100000,False,int(pid))
    if not handle:
        if ctypes.get_last_error()==87:return
        raise UpdateError('No se pudo esperar el cierre del programa.')
    try:
        if k.WaitForSingleObject(handle,int(timeout*1000))!=0:raise UpdateError('El programa no se cerró a tiempo.')
    finally:k.CloseHandle(handle)

def worker(jobfile):
    jobfile=Path(jobfile);job=json.loads(jobfile.read_text());base=jobfile.parent;root=Path(job['root'])
    atomic_json(base/'ready.json',{'ready':True})
    deadline=time.monotonic()+45
    while not (base/'go').exists():
        if time.monotonic()>deadline:return 2
        time.sleep(.1)
    result={'id':base.name,'success':False,'from':job['from'],'to':job['to']}
    child=None
    try:
        wait_pid(job.get('pid'))
        def health(ver):
            nonlocal child
            ack=base/'healthy.json'
            child=subprocess.Popen([str(root/EXE),'--update-health',str(ack),'--expected-version',ver],cwd=root)
            end=time.monotonic()+40
            while time.monotonic()<end:
                if ack.exists() and json.loads(ack.read_text()).get('version')==ver:return
                if child.poll() is not None:break
                time.sleep(.2)
            if child.poll() is None:child.terminate();child.wait(timeout=15)
            raise UpdateError('La aplicación nueva no confirmó el inicio; se restauró la versión anterior.')
        apply_transaction(job['package'],root,job['from'],base/'backup',health,job.get('sha256'),job['to'])
        result['success']=True
        result['child_pid']=child.pid if child else None
    except Exception as e:
        result['error']=str(e)
        try:subprocess.Popen([str(root/EXE)],cwd=root)
        except OSError:pass
    atomic_json(base/'result.json',result)
    atomic_json(Path(job['data'])/'last-update.json',result)
    return 0 if result['success'] else 1

def prepare_job(package,root,installed,data,expected_hash=None,expected_to=None,pid=None):
    if os.name!='nt':raise UpdateError('La instalación automática requiere Windows.')
    root=Path(root).resolve();data=Path(data).resolve()
    if not (root/EXE).is_file():raise UpdateError('Elegí la carpeta que contiene '+EXE)
    m=validate_package(package,installed,expected_hash,expected_to)
    base=data/'updates'/str(uuid.uuid4());base.mkdir(parents=True)
    staged=base/'package.zip';shutil.copy2(package,staged)
    # Se ejecuta una copia independiente para poder reemplazar también el actualizador.
    helper=Path(sys.executable) if getattr(sys,'_alm_helper',False) else root/HELPER
    if not helper.is_file():raise UpdateError('Falta el componente de actualización.')
    runner=base/HELPER;shutil.copy2(helper,runner)
    job={'root':str(root),'data':str(data),'package':str(staged),'from':installed,'to':m['to'],'sha256':digest(staged),'pid':pid}
    atomic_json(base/'job.json',job)
    proc=subprocess.Popen([str(runner),'--worker',str(base/'job.json')],cwd=base,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    end=time.monotonic()+20
    while not (base/'ready.json').exists():
        if proc.poll() is not None or time.monotonic()>end:raise UpdateError('El actualizador no pudo iniciar. El programa seguirá abierto.')
        time.sleep(.1)
    return base
