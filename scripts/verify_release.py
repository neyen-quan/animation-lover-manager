"""Verificar los bytes publicados, no solo la existencia de la release."""
import hashlib,json,sys,tempfile,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.updater import download,digest,validate_package
feed=json.loads(Path(sys.argv[1]).read_text());version=feed['version']
with tempfile.TemporaryDirectory() as tmp:
    for entry in [feed['full'],feed['installer'],feed['bootstrap']]+feed['patches']:
        p=download(entry['url'],Path(tmp)/'verify.zip')
        assert digest(p)==entry['sha256'],entry['url']
        if entry is feed['full'] or 'from' in entry:validate_package(p,entry.get('from','0.0.0'),entry['sha256'],version)
    url=feed['full']['url'].rsplit('/',1)[0]+'/latest.json'
    actual=json.loads(download(url,Path(tmp)/'latest.json',256*1024).read_text())
    assert actual==feed
from app.updater import check,CHANNEL
assert check(CHANNEL,'0.0.0')['version']==version
print('Archivos publicados, producto, versiones y hashes verificados.')
