"""USD ledger. Integer cents, explicit cash recognition, immutable audit trail."""
import copy
import datetime as dt
import hashlib
import json
import re
import shutil
import uuid
import zipfile
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

CATEGORIES = ['Créditos IA', 'Suscripciones', 'Infraestructura', 'APIs', 'Otros']
KINDS = ['Retiro', 'Gasto', 'Reintegro', 'Reparto', 'Traspaso personal', 'Insight']
PLATFORMS = ['Fanvue', 'Patreon']
EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.pdf', '.txt', '.ogg', '.opus', '.wav', '.mp3', '.m4a'}

def cents(value):
    try:
        raw = str(value).strip().replace(',', '.')
        n = Decimal(raw)
        if not n.is_finite() or n < 0 or n > Decimal('999999999'): raise ValueError()
        return int((n * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        raise ValueError('Ingresá un importe USD válido, sin separadores de miles.') from None

def usd(n):
    return f'USD {n / 100:,.2f}'

def entry(kind='Gasto'):
    return dict(id=str(uuid.uuid4()), kind=kind, date=dt.date.today().isoformat(),
                description='', person='', recipient='', platform='', category='Otros',
                funding='Caja', amount=0, fee=0, gross=0, received=False,
                include_pending=False, reference='', notes='', attachments=[], void=False,
                period=dt.date.today().strftime('%Y-%m'), subscribers=None, revision=0, source_id='')

def validate(data, people, categories):
    d = copy.deepcopy(data)
    if d.get('kind') not in KINDS: raise ValueError('Tipo de movimiento inválido.')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', d.get('id', '')): raise ValueError('Identificador inválido.')
    dt.date.fromisoformat(d['date'])
    if not str(d.get('description', '')).strip(): raise ValueError('Indicá el concepto del movimiento.')
    for key in ('amount', 'fee', 'gross'):
        if type(d.get(key)) is not int or not 0 <= d[key] <= 99999999900:
            raise ValueError('Importes inválidos. Usá montos positivos en USD.')
    for key in ('received', 'include_pending', 'void'):
        if type(d.get(key)) is not bool: raise ValueError('Estado inválido.')
    if d['kind'] in ('Retiro', 'Insight') and d.get('platform') not in PLATFORMS:
        raise ValueError('Seleccioná Fanvue o Patreon.')
    if d['kind'] == 'Retiro' and d['gross'] - d['fee'] != d['amount']:
        raise ValueError('El bruto menos la comisión debe coincidir con el neto.')
    if d['kind'] in ('Gasto', 'Reintegro', 'Reparto', 'Traspaso personal') and d.get('person') not in people:
        raise ValueError('Seleccioná una persona del equipo.')
    if d['kind'] == 'Gasto':
        if d.get('funding') not in ('Caja', 'Bolsillo personal'): raise ValueError('Indicá quién financió el gasto.')
        if d.get('category') not in categories: raise ValueError('Seleccioná una categoría válida.')
    if d['kind'] == 'Traspaso personal':
        if d.get('recipient') not in people or d['recipient'] == d['person']:
            raise ValueError('Indicá quién recibió el pago personal, distinto del emisor.')
    if d.get('source_id') and (d['kind'] != 'Reintegro' or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', d['source_id'])):
        raise ValueError('Vínculo de reintegro inválido.')
    if d['kind'] == 'Insight':
        if not re.fullmatch(r'\d{4}-\d{2}', d.get('period', '')): raise ValueError('Usá período AAAA-MM.')
        dt.date.fromisoformat(d['period'] + '-01')
        if d.get('subscribers') is not None and (type(d['subscribers']) is not int or d['subscribers'] < 0):
            raise ValueError('Cantidad de suscriptores inválida.')
    elif not d['amount']: raise ValueError('El importe debe ser mayor a cero.')
    for a in d.get('attachments', []):
        if not re.fullmatch(r'[0-9a-f]{64}\.[a-z0-9]+', a.get('file', '')) or Path(a['file']).suffix not in EXTENSIONS or a.get('sha256') != a['file'].split('.')[0]:
            raise ValueError('Comprobante inválido.')
    return d

def totals(rows):
    out = dict(cash=0, arrived=0, anticipated=0, pending=0, expenses=0, fees=0,
               withdrawals=0, reimbursements=0, distributions=0, debt={}, paid={}, categories={})
    def debt(p, n): out['debt'][p] = out['debt'].get(p, 0) + n
    for d in rows:
        if d.get('void'): continue
        n = d['amount']; k = d['kind']
        if k == 'Retiro':
            out['fees'] += d['fee']
            if d['received'] or d['include_pending']:
                out['cash'] += n; out['withdrawals'] += n
            if d['received']: out['arrived'] += n
            else:
                out['pending'] += n
                if d['include_pending']: out['anticipated'] += n
        elif k == 'Gasto':
            out['expenses'] += n
            out['categories'][d['category']] = out['categories'].get(d['category'], 0) + n
            if d['funding'] == 'Caja': out['cash'] -= n; out['arrived'] -= n
            else: debt(d['person'], n)
        elif k in ('Reintegro', 'Reparto'):
            out['cash'] -= n; out['arrived'] -= n
            if k == 'Reintegro': debt(d['person'], -n); out['reimbursements'] += n
            else:
                out['distributions'] += n
                out['paid'][d['person']] = out['paid'].get(d['person'], 0) + n
        elif k == 'Traspaso personal':
            debt(d['person'], n); debt(d['recipient'], -n)
    out['debt_total'] = sum(out['debt'].values())
    out['free'] = out['cash'] - out['debt_total']
    return out

def outstanding(rows):
    """Allocate legacy settlements and explicit links without changing historical rows.

    Personal transfers settle the recipient's oldest claims and create a claim for
    the sender. Legacy unlinked reimbursements also settle oldest claims. Explicit
    reimbursements reserve their own source before those unlinked payments.
    """
    active=sorted((d for d in rows if not d['void']),key=lambda d:(d['date'],d['id']))
    claims={d['id']:dict(person=d['person'],amount=d['amount'],remaining=d['amount'])
            for d in active if (d['kind']=='Gasto' and d['funding']=='Bolsillo personal') or d['kind']=='Traspaso personal'}
    def consume(person,amount,source=None):
        if source:
            if source not in claims or claims[source]['person']!=person:
                raise ValueError('El gasto vinculado al reintegro no corresponde a esa persona.')
            candidates=[claims[source]]
        else:candidates=[c for c in claims.values() if c['person']==person]
        for c in candidates:
            n=min(amount,c['remaining']);c['remaining']-=n;amount-=n
        if amount:raise ValueError('El reintegro o la compensación supera lo pendiente del gasto o la persona.')
    for d in active:
        if d['kind']=='Traspaso personal':consume(d['recipient'],d['amount'])
    reimbursements=[d for d in active if d['kind']=='Reintegro']
    for d in sorted(reimbursements,key=lambda d:not bool(d.get('source_id'))):
        consume(d['person'],d['amount'],d.get('source_id'))
    return claims

class Finance:
    def __init__(self, store):
        self.store = store; self.db = store.db
        self.media = store.path.parent / 'finance_receipts'; self.media.mkdir(exist_ok=True)
        self.db.execute('CREATE TABLE IF NOT EXISTS finance (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS finance_history (seq INTEGER PRIMARY KEY, stamp TEXT, before TEXT, after TEXT)')
        self.db.commit()
        self.backup_warning = ''

    def people(self):
        from .core import PEOPLE
        return self.store.setting('people') or PEOPLE

    def categories(self): return self.store.setting('finance_categories') or list(CATEGORIES)
    def rows(self): return [json.loads(r[0]) for r in self.db.execute('SELECT data FROM finance')]
    def get(self, id): return next((d for d in self.rows() if d['id'] == id), None)

    def attachment(self, path):
        p = Path(path)
        if p.suffix.lower() not in EXTENSIONS: raise ValueError('Formato de comprobante no admitido.')
        if p.stat().st_size > 30 * 1024 * 1024: raise ValueError('Cada comprobante debe pesar menos de 30 MB.')
        raw = p.read_bytes(); digest = hashlib.sha256(raw).hexdigest(); name = digest + p.suffix.lower()
        dest = self.media / name
        if not dest.exists():
            temp = dest.with_suffix('.tmp'); temp.write_bytes(raw); temp.replace(dest)
        return dict(file=name, name=p.name, sha256=digest)

    def duplicates(self, d):
        files = {a['sha256'] for a in d['attachments']}
        return [x for x in self.rows() if x['id'] != d['id'] and not x['void'] and
                ((files & {a['sha256'] for a in x['attachments']}) or
                 (d['reference'] and x['reference'] == d['reference'] and x['platform'] == d['platform']) or
                 (x['date'], x['kind'], x['amount'], x['person'], x['platform'], x['description'].casefold()) ==
                 (d['date'], d['kind'], d['amount'], d['person'], d['platform'], d['description'].casefold()))]

    def save(self, changes):
        checked = [validate(d, self.people(), self.categories()) for d in changes]
        if len({d['id'] for d in checked}) != len(checked): raise ValueError('Movimiento repetido en el lote.')
        old = {d['id']: self.get(d['id']) for d in checked}
        for d in checked:
            previous = old[d['id']]
            if previous and previous.get('revision', 0) != d.get('revision', 0):
                raise ValueError('El movimiento cambió. Cerralo y volvé a abrirlo.')
            for a in d['attachments']:
                p = self.media / a['file']
                if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != a['sha256']:
                    raise ValueError('Falta un comprobante o su integridad no coincide.')
            d['revision'] = d.get('revision', 0) + 1
        combined = {d['id']: d for d in self.rows()}; combined.update({d['id']: d for d in checked})
        active = [d for d in combined.values() if not d['void']]
        t = totals(active)
        if t['cash'] < 0: raise ValueError('La caja quedaría negativa. Revisá los ingresos y los gastos.')
        if any(n < 0 for n in t['debt'].values()): raise ValueError('El reintegro o traspaso supera la deuda con esa persona.')
        outstanding(active)
        insights = [(d['period'], d['platform']) for d in active if d['kind'] == 'Insight']
        if len(insights) != len(set(insights)): raise ValueError('Ya hay insights de esa plataforma y mes. Abrí ese registro para actualizarlo.')
        with self.db:
            for d in checked:
                self.db.execute('INSERT OR REPLACE INTO finance VALUES (?,?)', (d['id'], json.dumps(d, ensure_ascii=False)))
            self.db.execute('INSERT INTO finance_history(stamp,before,after) VALUES (?,?,?)',
                            (dt.datetime.now().isoformat(), json.dumps(old, ensure_ascii=False), json.dumps(checked, ensure_ascii=False)))
        self.backup_warning = ''
        try: self.store.backup()
        except Exception as e: self.backup_warning = 'Guardado localmente. No se pudo respaldar: ' + str(e)
        return checked

    def reimbursement(self, source_id=None, person=None):
        rows=self.rows()
        if source_id:
            source=self.get(source_id);claim=outstanding(rows).get(source_id)
            if not source or not claim:raise ValueError('Elegí un gasto pagado de bolsillo o un adelanto personal.')
            amount=claim['remaining'];person=claim['person'];description='Reintegro · '+source['description']
        else:
            if person not in self.people():raise ValueError('Seleccioná una persona.')
            amount=totals(rows)['debt'].get(person,0);description='Reintegro de gastos adelantados'
        d=entry('Reintegro');d.update(person=person,amount=amount,source_id=source_id or '',description=description)
        return d

    def pay_reimbursement(self, proposal, paths=()):
        """Commit the reviewed payment once, rejecting a stale amount."""
        existing=self.get(proposal['id'])
        if existing:
            if existing['kind']=='Reintegro' and not existing['void']:return existing
            raise ValueError('El registro de reintegro cambió. Volvé a abrirlo.')
        current=self.reimbursement(proposal.get('source_id'),proposal['person'])
        if not current['amount']:raise ValueError('Ese reintegro ya está saldado.')
        if current['amount']!=proposal['amount']:raise ValueError('El saldo cambió. Volvé a abrir Reintegrar para ver el monto actual.')
        d=copy.deepcopy(proposal)
        d['attachments']=[self.attachment(p) for p in paths]
        return self.save([d])[0]

    def confirm(self, id):
        d = self.get(id)
        if not d or d['kind'] != 'Retiro' or d['void']: raise ValueError('Seleccioná un retiro activo.')
        if d['received']: return
        d['received'] = True
        self.save([d])

    def rename_category(self, old, new):
        new = new.strip()
        categories = self.categories()
        if not new or len(new) > 60: raise ValueError('Ingresá un nombre de categoría de hasta 60 caracteres.')
        if any(x.casefold() == new.casefold() for x in categories if x != old): raise ValueError('Ya existe esa categoría.')
        categories = [new if x == old else x for x in categories] if old else categories + [new]
        before={};after=[]
        with self.db:
            for d in self.rows():
                if old and d['category'] == old:
                    before[d['id']]=copy.deepcopy(d)
                    d['category'] = new; d['revision'] += 1;after.append(d)
                    self.db.execute('UPDATE finance SET data=? WHERE id=?', (json.dumps(d, ensure_ascii=False), d['id']))
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('finance_categories', json.dumps(categories)))
            self.db.execute('INSERT INTO finance_history(stamp,before,after) VALUES (?,?,?)',(dt.datetime.now().isoformat(),json.dumps(before,ensure_ascii=False),json.dumps(after,ensure_ascii=False)))
        self.store.backup()

    def read_import(self, path):
        """Read a data-only starting ledger, never execute/extract arbitrary ZIP paths."""
        if self.rows(): raise ValueError('El punto de partida solo se importa con Finanzas vacío.')
        with zipfile.ZipFile(path) as z:
            if sum(i.file_size for i in z.infolist()) > 100 * 1024 * 1024: raise ValueError('Archivo demasiado grande.')
            if len(z.namelist()) != len(set(z.namelist())): raise ValueError('Archivo con entradas duplicadas.')
            manifest = json.loads(z.read('finance.json'))
            if manifest.get('product') != 'AnimationLoverFinance' or manifest.get('schema') != 1: raise ValueError('Formato de importación incorrecto.')
            rows = [validate(d, self.people(), self.categories()) for d in manifest['entries']]
            for d in rows:
                for a in d['attachments']:
                    raw = z.read('receipts/' + a['file'])
                    if hashlib.sha256(raw).hexdigest() != a['sha256']: raise ValueError('Comprobante dañado.')
                    dest = self.media / a['file']
                    if not dest.exists(): dest.write_bytes(raw)
        return rows
