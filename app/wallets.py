"""Private team address book. Stores public receiving addresses, never keys."""
import json
import re
from pathlib import Path

NETWORK = 'USDT · BEP20 / BSC'
SETTING = 'finance_wallets'
DRAFTS = 'finance_wallet_drafts'


def empty_profile():return {'crypto':{'asset':'','network':'','address':''},'kast':''}


def profile(value,*,check=False):
    """Read old address-only records without modifying their stored originals."""
    if isinstance(value,str):
        if check:value=address(value)
        result=empty_profile()
        if value:result['crypto']={'asset':'USDT','network':'BEP20 / BSC','address':value}
        return result
    if not isinstance(value,dict) or set(value)-{'crypto','kast'}:raise ValueError('Perfil de pago inválido.')
    crypto=value.get('crypto',{})
    if not isinstance(crypto,dict) or set(crypto)-{'asset','network','address'}:raise ValueError('Datos de cripto inválidos.')
    result=empty_profile()
    for key in result['crypto']:
        text=crypto.get(key,'')
        if not isinstance(text,str):raise ValueError('Completá los datos de cripto con texto.')
        result['crypto'][key]=text.strip() if check else text
    kast=value.get('kast','')
    if not isinstance(kast,str):raise ValueError('Completá el usuario de Kast con texto.')
    result['kast']=kast.strip() if check else kast
    if check:
        c=result['crypto']
        if any(c.values()) and not all(c.values()):raise ValueError('Para guardar Cripto, completá moneda, red y billetera. También podés dejar los tres campos vacíos y guardar solo Kast.')
        for key,limit in [('asset',32),('network',80),('address',256)]:
            if len(c[key])>limit or any(not char.isprintable() for char in c[key]):raise ValueError('Revisá el campo de '+{'asset':'moneda','network':'red','address':'billetera'}[key]+'.')
        if any(char.isspace() for char in c['address']):raise ValueError('La dirección de billetera no puede contener espacios.')
        if c['address'] and re.sub(r'[^a-z0-9]','',c['network'].lower()) in ('bep20','bsc','bep20bsc','bnbsmartchain'):
            c['address']=address(c['address'])
        if len(result['kast'])>200 or any(char.isspace() or not char.isprintable() for char in result['kast']):raise ValueError('Revisá el usuario de Kast: debe ir sin espacios ni saltos de línea.')
    return result


def address(value):
    if not isinstance(value,str):raise ValueError('Pegá una dirección de billetera.')
    value=value.strip()
    if value and not re.fullmatch(r'0x[0-9a-fA-F]{40}',value):
        raise ValueError('La dirección debe empezar por 0x y tener 40 caracteres hexadecimales después. Revisá la dirección USDT BEP20 / BSC que te pasaron.')
    return value


class WalletBook:
    def __init__(self,store):
        if store.project_id!='main' or store.setting('personal'):
            raise ValueError('Las billeteras del equipo corresponden a Animation Lover.')
        self.store=store;self.backup_warning=''
    def people(self):return self.store.people()
    def values(self):return {p:profile(v) for p,v in (self.store.setting(SETTING) or {}).items()}
    def drafts(self):return {p:profile(v) for p,v in (self.store.setting(DRAFTS) or {}).items()}
    def draft(self,person,value):
        if person not in self.people():raise ValueError('Persona desconocida.')
        drafts=self.drafts()
        value=profile(value)
        if value==self.values().get(person,empty_profile()):drafts.pop(person,None)
        else:drafts[person]=value
        self.store.setting(DRAFTS,drafts)
    def save(self,values,*,replace=True):
        if not isinstance(values,dict) or not values:raise ValueError('No hay billeteras para guardar.')
        if any(p not in self.people() for p in values):raise ValueError('Persona desconocida.')
        checked={p:profile(v,check=True) for p,v in values.items()}
        current=self.values();drafts=self.drafts()
        for p,value in checked.items():
            if not replace:
                old=current.get(p,empty_profile());merged=profile(old)
                for key,text in value['crypto'].items():
                    if text and old['crypto'][key] and old['crypto'][key]!=text:raise ValueError('Ya hay otros datos de cripto para '+p+'. Revisá su perfil antes de reemplazarlos.')
                    if text:merged['crypto'][key]=text
                if value['kast'] and old['kast'] and value['kast']!=old['kast']:raise ValueError('Ya hay otro usuario de Kast para '+p+'. Revisá su perfil antes de reemplazarlo.')
                if value['kast']:merged['kast']=value['kast']
                value=merged
            current[p]=value;drafts.pop(p,None)
        with self.store.db:
            for key,value in ((SETTING,current),(DRAFTS,drafts)):
                self.store.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,json.dumps(value,ensure_ascii=False)))
        self.backup_warning=''
        try:self.store.backup()
        except Exception as error:self.backup_warning='Billeteras guardadas localmente. Respaldo pendiente: '+str(error)
    def read_import(self,path):
        path=Path(path)
        if path.stat().st_size>65536:raise ValueError('El archivo de billeteras es demasiado grande.')
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,dict) or data.get('product')!='AnimationLoverWallets' or data.get('schema') not in (1,2) or data.get('project')!='main' or (data['schema']==1 and data.get('network')!='USDT BEP20 / BSC'):
            raise ValueError('El archivo no es una configuración de billeteras de Animation Lover.')
        values=data.get('wallets')
        if not isinstance(values,dict) or not values:raise ValueError('No hay billeteras para cargar.')
        names={p.casefold():p for p in self.people()};checked={}
        for name,value in values.items():
            person=names.get(name.casefold())
            if not person or person in checked:raise ValueError('Persona desconocida o repetida: '+name)
            if data['schema']==1 and not isinstance(value,str):raise ValueError('El archivo de billeteras anterior debe contener direcciones de texto.')
            checked[person]=profile(value,check=True)
            if checked[person]==empty_profile():raise ValueError('El archivo contiene un perfil vacío.')
        return checked
