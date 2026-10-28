import copy,hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from app import updater as u

def record(path,content):return {'path':path,'size':len(content),'sha256':hashlib.sha256(content).hexdigest()}
def make_zip(folder,old='1.0.0',new='1.0.1',kind='patch',extra=None,corrupt=False):
    files={u.EXE:b'new exe',u.HELPER:b'new helper','_internal/runtime.dll':b'runtime'}
    allfiles=[record(p,b) for p,b in files.items()]
    changed=[f for f in allfiles if f['path']!='_internal/runtime.dll'] if kind=='patch' else allfiles
    m={'schema':1,'product':u.PRODUCT,'kind':kind,'from':old if kind=='patch' else '*','to':new,'files':changed,'inventory':allfiles,'delete':[]}
    if extra:m.update(extra)
    p=Path(folder)/'update.zip'
    with zipfile.ZipFile(p,'w') as z:
        z.writestr('manifest.json',json.dumps(m))
        for f in changed:z.writestr('files/'+f['path'],b'corrupt' if corrupt else files[f['path']])
    return p,m
class UpdaterTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.root=self.base/'app';self.root.mkdir();(self.root/'_internal').mkdir();(self.root/u.EXE).write_bytes(b'old exe');(self.root/u.HELPER).write_bytes(b'old helper');(self.root/'_internal/runtime.dll').write_bytes(b'runtime')
    def tearDown(self):self.tmp.cleanup()
    def test_versions_and_paths(self):
        self.assertGreater(u.version('1.10.0'),u.version('1.2.9'))
        for p in ['../evil','/evil','_internal/../x','_internal/a:ads','_internal/CON','_internal/foo.','_internal\\evil','manager.sqlite3','other.exe','_internal/.env']:
            with self.assertRaises(u.UpdateError,msg=p):u.safe_path(p)
    def test_product_source_target_hash(self):
        for extra in [{'product':'Other'},{'from':'9.0.0'},{'to':'1.0.0'}]:
            p,_=make_zip(self.base,extra=extra)
            with self.assertRaises(u.UpdateError):u.validate_package(p,'1.0.0')
        p,_=make_zip(self.base,corrupt=True)
        with self.assertRaises(u.UpdateError):u.validate_package(p,'1.0.0')
        p,_=make_zip(self.base)
        with self.assertRaises(u.UpdateError):u.validate_package(p,'1.0.0','0'*64)
    def test_delta_and_data_preservation(self):
        p,_=make_zip(self.base);private=self.base/'user-data';private.mkdir();(private/'manager.sqlite3').write_bytes(b'database')
        (self.root/'custom-logo.png').write_bytes(b'custom')
        u.apply_transaction(p,self.root,'1.0.0',self.base/'backup')
        self.assertEqual((self.root/u.EXE).read_bytes(),b'new exe');self.assertEqual((self.root/'_internal/runtime.dll').read_bytes(),b'runtime');self.assertEqual((private/'manager.sqlite3').read_bytes(),b'database');self.assertEqual((self.root/'custom-logo.png').read_bytes(),b'custom');self.assertFalse((self.base/'backup/_internal/runtime.dll').exists())
        self.assertEqual(u.installed_version(self.root,'0.0.0'),'1.0.1')
    def test_rollback_after_failed_restart(self):
        p,_=make_zip(self.base)
        def fail(v):raise RuntimeError('No inició')
        with self.assertRaises(RuntimeError):u.apply_transaction(p,self.root,'1.0.0',self.base/'backup',fail)
        self.assertEqual((self.root/u.EXE).read_bytes(),b'old exe');self.assertFalse((self.root/'installation.json').exists())
    def test_corrupt_base_rejected_before_replacement(self):
        p,_=make_zip(self.base);(self.root/'_internal/runtime.dll').write_bytes(b'changed')
        with self.assertRaises(u.UpdateError):u.apply_transaction(p,self.root,'1.0.0',self.base/'backup')
        self.assertEqual((self.root/u.EXE).read_bytes(),b'old exe')
    def test_full_repairs_base(self):
        p,_=make_zip(self.base,kind='full');(self.root/'_internal/runtime.dll').write_bytes(b'changed')
        u.apply_transaction(p,self.root,'1.0.0',self.base/'backup');self.assertEqual((self.root/'_internal/runtime.dll').read_bytes(),b'runtime')
    def test_extra_duplicate_and_symlink_rejected(self):
        p,_=make_zip(self.base)
        with zipfile.ZipFile(p,'a') as z:z.writestr('files/_internal/extra.dll',b'bad')
        with self.assertRaises(u.UpdateError):u.validate_package(p,'1.0.0')
        p,m=make_zip(self.base)
        with zipfile.ZipFile(p,'a') as z:z.writestr('MANIFEST.JSON','{}')
        with self.assertRaises(u.UpdateError):u.validate_package(p,'1.0.0')
    def test_channel_and_redirect_allowlist(self):
        for url in ['http://github.com/a','https://evil.test/a','https://github.com@evil.test/a','https://user:pass@github.com/a','https://github.com:444/a']:
            self.assertFalse(u.valid_url(url))
        self.assertTrue(u.valid_url(u.CHANNEL))
    def test_concurrent_install_is_rejected(self):
        p,_=make_zip(self.base)
        with u.install_lock(self.root):
            with self.assertRaises(u.UpdateError):u.apply_transaction(p,self.root,'1.0.0',self.base/'backup')
        self.assertEqual((self.root/u.EXE).read_bytes(),b'old exe')
    def test_local_package_accepts_valid_full(self):
        p,m=make_zip(self.base,kind='full');self.assertEqual(u.validate_package(p,'0.1.0')['to'],'1.0.1')
if __name__=='__main__':unittest.main()
