"""Project-local databases; the existing main database remains in place."""
import copy
import datetime as dt
import json
import re
import shutil
import tempfile
from pathlib import Path
from .core import Store
from .finance import Finance, entry, validate, totals

MAIN=dict(id='main',name='Animation Lover',personal=False)
PROVIDERS=['Higgsfield','Wavespeed','Kling','VideoForge','Otras']

class Projects:
    def __init__(self, root):
        self.root=root;self.stores={'main':root};self.backup_warning=''
        self.root.backup_hook=self.backup_others

    def list(self):return [dict(MAIN)]+copy.deepcopy(self.root.setting('projects') or [])
    def descriptor(self,id):
        found=next((p for p in self.list() if p['id']==id),None)
        if not found:raise ValueError('Proyecto desconocido.')
        return found
    def open(self,id):
        self.descriptor(id)
        if id not in self.stores:
            store=Store(self.root.path.parent/'projects'/id/'manager.sqlite3')
            store.shared_store=self.root;store.project_id=id;store.backup_hook=self.backup_others
            self.stores[id]=store
        return self.stores[id]
    def context(self,id):
        p=self.descriptor(id);s=self.open(id)
        return dict(id=id,name=p['name'],personal=p['personal'],description=s.setting('project_context') or '',
                    other_projects=[v['name'] for v in self.list() if v['id']!=id],owner=s.people()[0],platforms=s.setting('finance_platforms') or ['Fanvue','Patreon'])
    def backup_others(self,source):
        # Each snapshot is complete for its own project. Main includes the registry.
        for p in self.list():
            store=self.open(p['id'])
            if store is not source:store.backup(notify=False)
    def backup_all(self):
        for p in self.list():self.open(p['id']).backup(notify=False)
    def close(self):
        for store in self.stores.values():store.db.close()

    def preview_import(self,path):
        path=Path(path)
        if path.stat().st_size>1024*1024:raise ValueError('Configuración demasiado grande.')
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('product')!='AnimationLoverProject' or data.get('schema')!=1:raise ValueError('Archivo de proyecto incorrecto.')
        p=data.get('project',{});id=p.get('id','');name=p.get('name','')
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',id) or id=='main':raise ValueError('Identificador de proyecto inválido.')
        if not isinstance(name,str) or not name.strip() or len(name)>60:raise ValueError('Nombre de proyecto inválido.')
        if id in [v['id'] for v in self.list()] or name.casefold() in [v['name'].casefold() for v in self.list()]:raise ValueError('Ese proyecto ya está cargado. No se duplicaron datos.')
        if p.get('personal') is not True:raise ValueError('Esta importación debe corresponder a un proyecto personal.')
        owner=self.root.people()[0]
        categories=p.get('categories',['Créditos IA','Suscripciones','Infra','APIs','Otros'])
        if not isinstance(categories,list) or not categories or any(not isinstance(v,str) or not v.strip() or len(v)>60 for v in categories) or len({v.casefold() for v in categories})!=len(categories):raise ValueError('Categorías inválidas.')
        providers=p.get('providers',PROVIDERS)
        if not isinstance(providers,list) or not providers or any(not isinstance(v,str) or not v.strip() or len(v)>60 for v in providers):raise ValueError('Proveedores inválidos.')
        platforms=p.get('platforms',['Fanvue'])
        if not isinstance(platforms,list) or not platforms or any(v not in ('Fanvue','Patreon') for v in platforms):raise ValueError('Plataformas inválidas.')
        rows=[]
        for n,item in enumerate(data.get('expenses',[])):
            if not isinstance(item,dict):raise ValueError('Gasto inicial inválido.')
            d=entry('Gasto');d.update(id='opening-'+str(n+1),person=owner,funding='Bolsillo personal',
                description=item.get('description',''),amount=item.get('cents'),category=item.get('category','Otros'),
                provider=item.get('provider',''),notes='Gasto histórico pagado de bolsillo. Fecha de carga; fecha original no informada.')
            d=validate(d,[owner],categories,providers=providers,require_provider=True,platforms=platforms)
            if d['category']=='Créditos IA' and (not d.get('provider') or d['provider'] not in providers):raise ValueError('Falta el proveedor de créditos IA.')
            rows.append(d)
        # Do not allow arbitrary database, filesystem, executable or attachment paths.
        return dict(project=dict(id=id,name=name.strip(),personal=True),owner=owner,categories=categories,
                    providers=providers,platforms=platforms,context=str(p.get('context',''))[:5000],entries=rows)

    def import_project(self, prepared):
        p=prepared['project'];self.descriptor('main')
        if any(v['id']==p['id'] or v['name'].casefold()==p['name'].casefold() for v in self.list()):raise ValueError('El proyecto ya existe.')
        parent=self.root.path.parent/'projects';parent.mkdir(exist_ok=True)
        destination=parent/p['id']
        if destination.exists():raise ValueError('Ya hay una carpeta para ese proyecto. No se reemplazó nada.')
        stage=Path(tempfile.mkdtemp(prefix='.import-',dir=parent));store=None
        try:
            store=Store(stage/'manager.sqlite3')
            for key,value in [('people',[prepared['owner']]),('personal',True),('project_name',p['name']),
                              ('finance_categories',prepared['categories']),('finance_providers',prepared['providers']),
                              ('finance_platforms',prepared['platforms']),('require_provider',True),('project_context',prepared['context'])]:store.setting(key,value)
            finance=Finance(store)
            if prepared['entries']:finance.save(prepared['entries'])
            store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.db.close();store=None
            # A staged backup has no useful final paths; the final backup follows publication.
            shutil.rmtree(stage/'backups',ignore_errors=True)
            stage.replace(destination)
            try:self.root.setting('projects',(self.root.setting('projects') or [])+[p])
            except Exception:shutil.rmtree(destination);raise
            self.backup_warning=''
            try:self.backup_all()
            except Exception as e:self.backup_warning='Proyecto guardado localmente; falta el respaldo: '+str(e)
            return p
        finally:
            if store is not None:store.db.close()
            if stage.exists():shutil.rmtree(stage)
