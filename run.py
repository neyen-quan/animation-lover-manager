import os, sys, tempfile
if '--smoke-test' in sys.argv:
    # Ejercita Tk real en Windows sin tocar los datos del usuario.
    with tempfile.TemporaryDirectory() as root:
        os.environ['LOCALAPPDATA'] = root
        from app.main import App
        app = App()
        app.update()
        app.change_view('Todas')
        app.update()
        assert app.winfo_width() > 100
        app.close()
    print('Interfaz inicializada correctamente')
else:
    from app.main import App
    App().mainloop()
