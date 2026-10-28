import os,sys,tempfile,json
from pathlib import Path
if '--smoke-test' in sys.argv:
    with tempfile.TemporaryDirectory() as root:
        os.environ['LOCALAPPDATA']=root
        from app.main import App
        app=App();app.update();app.change_view('Todas');app.update()
        assert app.winfo_width()>100
        app.close()
else:
    from app.main import App
    from app import __version__
    app=App()
    if '--update-health' in sys.argv:
        from app.updater import atomic_json
        ack=Path(sys.argv[sys.argv.index('--update-health')+1])
        expected=sys.argv[sys.argv.index('--expected-version')+1]
        if expected!=__version__:app.destroy();raise SystemExit(3)
        app.after(700,lambda:atomic_json(ack,{'version':__version__,'ready':True}))
    app.mainloop()
