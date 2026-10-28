"""Persistencia local. Ningún dato de uso se guarda en el repositorio."""
from contextlib import closing
import calendar, copy, datetime as dt, json, os, sqlite3, uuid
from pathlib import Path
PEOPLE = ['Persona 1','Persona 2','Persona 3','Persona 4','Persona 5']
KINDS = ['Tarea','Idea','Roadmap','Nota']
STATES = ['Pendiente','En curso','Esperando','Terminado']
ALIASES = {}
def today(): return dt.date.today()
def person(value):
    value=str(value).strip()
    return next((p for p in PEOPLE if p.lower()==value.lower()), ALIASES.get(value.lower()))
def date_value(value):
    if len(value)==7:
        y,m=map(int,value.split('-')); return dt.date(y,m,calendar.monthrange(y,m)[1]).isoformat()
    return dt.date.fromisoformat(value).isoformat()
def validate(data):
    d=copy.deepcopy(data)
    if not str(d.get('title','')).strip(): raise ValueError('Falta el título.')
    if d.get('kind') not in KINDS or d.get('status') not in STATES: raise ValueError('Categoría o estado inválido.')
    d['author']=person(d.get('author',PEOPLE[0]))
    if not d['author']: raise ValueError('Autor desconocido.')
    d['owners']=[person(p) for p in d.get('owners',[])]
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
        self.db=sqlite3.connect(self.path)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS history (seq INTEGER PRIMARY KEY, stamp TEXT, before TEXT, after TEXT, undone INTEGER DEFAULT 0)')
        self.db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        self.db.commit()
    def setting(self,key,value=None):
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
        old=self.setting('people') or list(PEOPLE)
        used=self.db.execute('SELECT EXISTS(SELECT 1 FROM items) OR EXISTS(SELECT 1 FROM history)').fetchone()[0]
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
            aliases={key:mapping.get(value,value) for key,value in (self.setting('aliases') or {}).items()}
            for key,value in [('people',names),('aliases',aliases)]:
                self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,json.dumps(value,ensure_ascii=False)))
        return mapping
    def apply(self,items):
        items=[validate(d) for d in items]
        ids=[d['id'] for d in items]
        if len(ids)!=len(set(ids)): raise ValueError('Actualización duplicada.')
        before={id:self.get(id) for id in ids}
        # Una reunión completada produce una única siguiente ocurrencia.
        for d in list(items):
            old=before[d['id']]
            if d.get('recurrence')=='tuesday' and d['status']=='Terminado' and (not old or old['status']!='Terminado'):
                next_date=today()+dt.timedelta(days=(1-today().weekday())%7 or 7)
                n=fresh('Reunión semanal'); n.update(recurrence='tuesday',owners=[PEOPLE[0]],planned=next_date.isoformat(),deadline=next_date.isoformat())
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
    def backup(self,folder=None):
        folder=Path(folder or self.setting('backup_folder') or self.path.parent/'backups'); folder.mkdir(parents=True,exist_ok=True)
        path=folder/(dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
        with closing(sqlite3.connect(path)) as target: self.db.backup(target)
        backups=sorted(folder.glob('*.sqlite3'))
        for p in backups[:-30]: p.unlink()
        return path
