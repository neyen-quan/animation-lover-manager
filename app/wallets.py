"""Private team address book. Stores public receiving addresses, never keys."""
import json
import re
from pathlib import Path

NETWORK = 'USDT · BEP20 / BSC'
SETTING = 'finance_wallets'
DRAFTS = 'finance_wallet_drafts'


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
    def values(self):return self.store.setting(SETTING) or {}
    def drafts(self):return self.store.setting(DRAFTS) or {}
    def draft(self,person,value):
        if person not in self.people():raise ValueError('Persona desconocida.')
        drafts=self.drafts()
        if value==self.values().get(person,''):drafts.pop(person,None)
        else:drafts[person]=value
        self.store.setting(DRAFTS,drafts)
    def save(self,values,*,replace=True):
        if not isinstance(values,dict) or not values:raise ValueError('No hay billeteras para guardar.')
        if any(p not in self.people() for p in values):raise ValueError('Persona desconocida.')
        checked={p:address(v) for p,v in values.items()}
        current=self.values();drafts=self.drafts()
        for p,value in checked.items():
            if not replace and current.get(p) and current[p].lower()!=value.lower():
                raise ValueError('Ya hay otra billetera guardada para '+p+'. Revisala en su campo antes de reemplazarla.')
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
        if not isinstance(data,dict) or data.get('product')!='AnimationLoverWallets' or data.get('schema')!=1 or data.get('project')!='main' or data.get('network')!='USDT BEP20 / BSC':
            raise ValueError('El archivo no es una configuración de billeteras de Animation Lover.')
        values=data.get('wallets')
        if not isinstance(values,dict) or not values:raise ValueError('No hay billeteras para cargar.')
        names={p.casefold():p for p in self.people()};checked={}
        for name,value in values.items():
            person=names.get(name.casefold())
            if not person or person in checked:raise ValueError('Persona desconocida o repetida: '+name)
            checked[person]=address(value)
            if not checked[person]:raise ValueError('El archivo contiene una dirección vacía.')
        return checked
