import sys
sys._alm_helper = True
from app.updater import worker
if '--worker' in sys.argv:
    raise SystemExit(worker(sys.argv[sys.argv.index('--worker')+1]))
else:
    from app.update_dialog import bootstrap
    bootstrap()
