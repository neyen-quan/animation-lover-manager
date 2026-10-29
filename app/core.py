"""Persistencia local. Ningún dato de uso se guarda en el repositorio."""
from contextlib import closing
import calendar, copy, datetime as dt, json, os, sqlite3, uuid, zipfile
from pathlib import Path
DEFAULT_PEOPLE = ['Persona 1','Persona 2','Persona 3','Persona 4','Persona 5']
PEOPLE = list(DEFAULT_PEOPLE)
SHARED_SETTINGS = {'model','backup_folder','update_channel','update_result_seen'}
KINDS = ['Tarea','Idea','Roadmap','Nota']
STATES = ['Pendiente','En curso','Esperando','Terminado']
ALIASES = {}
def today(): return dt.date.today()
def person(value,people=None,aliases=None):
    people=PEOPLE if people is None else people;aliases=ALIASES if aliases is None else aliases
    value=str(value).strip()
    return next((p for p in people if p.lower()==value.lower()), aliases.get(value.lower()))
def date_value(value):
    if len(value)==7:
        y,m=map(int,value.split('-')); return dt.date(y,m,calendar.monthrange(y,m)[1]).isoformat()
    return dt.date.fromisoformat(value).isoformat()
def validate(data,people=None,aliases=None):
    people=PEOPLE if people is None else people
    d=copy.deepcopy(data)
    if not str(d.get('title','')).strip(): raise ValueError('Falta el título.')
    if d.get('kind') not in KINDS or d.get('status') not in STATES: raise ValueError('Categoría o estado inválido.')
    d['author']=person(d.get('author',people[0]),people,aliases)
    if not d['author']: raise ValueError('Autor desconocido.')
    d['owners']=[person(p,people,aliases) for p in d.get('owners',[])]
    if None in d['owners']: raise ValueError('Responsable desconocido.')
    for key in ['planned','deadline']: d[key]=date_value(d[key])
    if d['planned']>d['deadline']: raise ValueError('La fecha prevista debe ser anterior o igual al límite.')
    if d.get('priority') not in ['Baja','Media','Alta','Máxima']: raise ValueError('Prioridad inválida.')
    return d

def fresh(title='',author=None):
    author=author or PEOPLE[0]
    return dict(id=str(uuid.uuid4()),title=title,summary='',kind='Tarea',status='Pendiente',author=author,owners=[],priority='Media',planned=today().isoformat(),deadline=(today()+dt.timedelta(days=7)).isoformat(),pending=[],completed=[],questions=[],parent='',dependencies=[],attachments=[],recurrence=None,deleted=False,updated=dt.datetime.now().isoformat())
def urgency(d):
    if d['status']=='Terminado': return 0
    if d['deadline']<today().isoformat(): return 3
    if d['planned']<today().isoformat(): return 2
    return 1

class Store:
    def __init__(self,path=None):
        root=Path(os.getenv('LOCALAPPDATA',Path.home()/'.local/share'))/'AnimationLoverManager'
        self.path=Path(path) if path else root/'manager.sqlite3'
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.shared_store=None;self.project_id='main';self.backup_hook=None
        self.db=sqlite3.connect(self.path)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS history (seq INTEGER PRIMARY KEY, stamp TEXT, before TEXT, after TEXT, undone INTEGER DEFAULT 0)')
        self.db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        self.db.commit()
    def people(self):return self.setting('people') or list(DEFAULT_PEOPLE)
    def setting(self,key,value=None):
        if self.shared_store is not None and key in SHARED_SETTINGS:return self.shared_store.setting(key,value)
        if value is not None:
            with self.db: self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,json.dumps(value)))
            return value
        r=self.db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        return json.loads(r[0]) if r else None
    def items(self,deleted=False):
        return [d for (v,) in self.db.execute('SELECT data FROM items') if (d:=json.loads(v)).get('deleted',False)==deleted]
    def get(self,id):
        r=self.db.execute('SELECT data FROM items WHERE id=?',(id,)).fetchone()
        return json.loads(r[0]) if r else None
    def rename_people(self,names):
        names=[str(n).strip() for n in names]
        if not names or any(not n or ',' in n or n.casefold()=='todos' for n in names):
            raise ValueError('Ingresá un nombre por línea, sin comas ni el nombre reservado Todos.')
        if len({n.casefold() for n in names})!=len(names):
            raise ValueError('Ingresá nombres distintos para cada persona.')
        old=self.people()
        used=self.db.execute('SELECT EXISTS(SELECT 1 FROM items) OR EXISTS(SELECT 1 FROM history)').fetchone()[0]
        has_finance=self.db.execute("SELECT 1 FROM sqlite_master WHERE name='finance'").fetchone()
        if has_finance:used=used or self.db.execute('SELECT EXISTS(SELECT 1 FROM finance)').fetchone()[0]
        if used and len(names)!=len(old):
            raise ValueError('Para conservar las asignaciones, mantené la cantidad de personas y reemplazá cada nombre en su misma línea.')
        mapping=dict(zip(old,names))
        # Keep an independent local recovery copy even if Drive is unavailable.
        self.backup(folder=self.path.parent/'backups')
        def remap(data):
            if data is None:return None
            data=copy.deepcopy(data)
            if 'author' in data:data['author']=mapping.get(data['author'],data['author'])
            if 'owners' in data:data['owners']=[mapping.get(p,p) for p in data['owners']]
            return data
        with self.db:
            for id,value in self.db.execute('SELECT id,data FROM items').fetchall():
                self.db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(remap(json.loads(value)),ensure_ascii=False),id))
            for seq,before,after in self.db.execute('SELECT seq,before,after FROM history').fetchall():
                before={id:remap(d) for id,d in json.loads(before).items()}
                after=[remap(d) for d in json.loads(after)]
                self.db.execute('UPDATE history SET before=?,after=? WHERE seq=?',(json.dumps(before,ensure_ascii=False),json.dumps(after,ensure_ascii=False),seq))
            if has_finance:
                for id,value in self.db.execute('SELECT id,data FROM finance').fetchall():
                    data=json.loads(value)
                    for key in ('person','recipient'):data[key]=mapping.get(data.get(key,''),data.get(key,''))
                    data['revision']=data.get('revision',0)+1
                    self.db.execute('UPDATE finance SET data=? WHERE id=?',(json.dumps(data,ensure_ascii=False),id))
            aliases={key:mapping.get(value,value) for key,value in (self.setting('aliases') or {}).items()}
            for key,value in [('people',names),('aliases',aliases)]:
                self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,json.dumps(value,ensure_ascii=False)))
        return mapping
    def apply(self,items):
        prepared=copy.deepcopy(items)
        if self.setting('personal'):
            for d in prepared:d['author']=self.people()[0];d['owners']=[self.people()[0]]
        items=[validate(d,self.people(),self.setting('aliases') or {}) for d in prepared]
        ids=[d['id'] for d in items]
        if len(ids)!=len(set(ids)): raise ValueError('Actualización duplicada.')
        before={id:self.get(id) for id in ids}
        # Una reunión completada produce una única siguiente ocurrencia.
        for d in list(items):
            old=before[d['id']]
            if d.get('recurrence')=='tuesday' and d['status']=='Terminado' and (not old or old['status']!='Terminado'):
                next_date=today()+dt.timedelta(days=(1-today().weekday())%7 or 7)
                n=fresh('Reunión semanal',author=self.people()[0]); n.update(recurrence='tuesday',owners=[self.people()[0]],planned=next_date.isoformat(),deadline=next_date.isoformat())
                items.append(n); before[n['id']]=None
        with self.db:
            for d in items:
                d['updated']=dt.datetime.now().isoformat()
                self.db.execute('INSERT OR REPLACE INTO items VALUES (?,?)',(d['id'],json.dumps(d,ensure_ascii=False)))
            self.db.execute('INSERT INTO history(stamp,before,after) VALUES (?,?,?)',(dt.datetime.now().isoformat(),json.dumps(before),json.dumps(items)))
        self.backup()
    def undo(self):
        r=self.db.execute('SELECT seq,before FROM history WHERE undone=0 ORDER BY seq DESC LIMIT 1').fetchone()
        if not r: return
        with self.db:
            for id,d in json.loads(r[1]).items():
                if d is None: self.db.execute('DELETE FROM items WHERE id=?',(id,))
                else: self.db.execute('INSERT OR REPLACE INTO items VALUES (?,?)',(id,json.dumps(d)))
            self.db.execute('UPDATE history SET undone=1 WHERE seq=?',(r[0],))
        self.backup()
    def backup(self,folder=None,notify=True):
        explicit=folder is not None
        if folder is None:
            configured=self.setting('backup_folder')
            folder=Path(configured) if configured else self.path.parent/'backups'
            if configured and self.project_id!='main':folder=folder/'Proyectos'/self.project_id
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        path=folder/(dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
        with closing(sqlite3.connect(path)) as target: self.db.backup(target)
        # A self-contained copy pairs this exact database snapshot with immutable receipts.
        media=self.path.parent/'finance_receipts'
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE name='finance'").fetchone():
            dest=folder/'Finanzas';dest.mkdir(exist_ok=True)
            final=dest/(path.stem+'.zip');temp=dest/(path.stem+'.tmp')
            try:
                with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
                    z.write(path,'manager.sqlite3')
                    if media.exists():
                        for receipt in sorted(media.iterdir()):
                            if receipt.is_file() and receipt.suffix!='.tmp':z.write(receipt,'finance_receipts/'+receipt.name)
                temp.replace(final)
            finally:temp.unlink(missing_ok=True)
            for old in sorted(dest.glob('*.zip'))[:-30]:old.unlink()
        backups=sorted(folder.glob('*.sqlite3'))
        for p in backups[:-30]: p.unlink()
        if notify and self.backup_hook and not explicit:self.backup_hook(self)
        return path
