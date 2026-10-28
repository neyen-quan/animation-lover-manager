import json,os,re,subprocess,sys,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import __version__
from app.updater import version,PRODUCT,EXE
version(__version__)
tag='v'+__version__
requested=os.getenv('REQUESTED_TAG','')
if requested and requested!=tag:raise ValueError('El tag solicitado y la versión del código no coinciden.')
if os.getenv('GITHUB_REF_TYPE')=='tag' and os.getenv('GITHUB_REF_NAME')!=tag:raise ValueError('El tag no coincide con la versión.')
repo=os.environ['GITHUB_REPOSITORY']
r=subprocess.run(['gh','release','view',tag,'--repo',repo,'--json','isDraft,assets'],capture_output=True,text=True)
complete=False
if r.returncode==0:
    d=json.loads(r.stdout);names={a['name'] for a in d['assets']}
    complete=not d['isDraft'] and {'latest.json',f'{PRODUCT}-Windows-{__version__}.zip',f'{PRODUCT}-Actualizar-{__version__}.zip','SHA256SUMS.txt','ActualizarAnimationLover.exe'}<=names
publish=not complete or bool(requested)
with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write(f'publish={str(publish).lower()}\nversion={__version__}\ntag={tag}\n')
print('Publicar' if publish else 'La versión ya está publicada; no se genera otra release.',tag)
