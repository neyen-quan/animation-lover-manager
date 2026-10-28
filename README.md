# Animation Lover Manager

Aplicación de escritorio personal para Windows. Configurá los nombres del equipo en Ajustes antes de crear tarjetas; se guardan únicamente en tu PC. **Versión 0.1.0 de desarrollo**, todavía no una versión final lista para uso diario.

## Lo que funciona en esta entrega

- Tarjetas de tareas, ideas, roadmap y notas; responsables, autor, fechas y prioridades.
- Edición manual, vista del día, búsqueda textual, filtros por persona y recientes.
- Actualizaciones mediante modelo local de Ollama: texto, imágenes con modelos compatibles y audios transcritos con faster-whisper.
- Grabación con dos finales: transcribir o transcribir e interpretar.
- Papelera, deshacer transacciones, historial y copias SQLite con versiones.
- Reunión semanal anclada al martes: se crea la siguiente al completar la anterior.
- Mensaje editable para copiar; las últimas 20 ediciones se guardan localmente como futuras referencias de estilo.
- Finanzas reservada para una ampliación posterior.

## Inicio en Windows

1. Instalar Python 3.12 (incluyendo Tcl/Tk y el lanzador `py`).
2. Descargar el código o clonar el repositorio.
3. Ejecutar `Iniciar.bat`. Instala dependencias en `.venv` y abre la aplicación.
4. Para interpretar entradas, instalar Ollama y descargar un modelo compatible con el hardware. En Ajustes escribir exactamente el nombre que muestra `ollama list`. La aplicación se comunica solamente con `127.0.0.1:11434`. No necesita una API paga ni utiliza automáticamente la suscripción ChatGPT.
5. La primera transcripción descarga el modelo Whisper `small`. Requiere conexión durante esa descarga; luego procesa localmente en CPU. El rendimiento depende del equipo.

La configuración de IA y la grabación real deben probarse en la PC de destino antes de usar datos importantes. La interfaz puede usarse manualmente sin Ollama.

También se prepara un paquete Windows desde **Actions → Windows · pruebas y aplicación → Artifacts**. Descargar y extraer el ZIP completo; abrir `AnimationLoverManager.exe` dentro de la carpeta. Es un paquete de desarrollo, sin firma de Windows. La compilación solo está disponible si el workflow termina correctamente.

## Datos y respaldo

La base de datos se guarda en `%LOCALAPPDATA%/AnimationLoverManager/manager.sqlite3`. Nunca dentro del código. No incluir datos, adjuntos, claves ni respaldos en commits.

Se guarda un respaldo después de cada transacción y se conservan los últimos 30. En Ajustes puede elegirse una carpeta sincronizada por Google Drive para que el cliente de Drive la suba. Esto no es una conexión directa con la API de Drive.

Para recuperar un respaldo: cerrar la aplicación, conservar una copia completa de la carpeta de datos y sustituir `manager.sqlite3` por el respaldo elegido; retirar los archivos `manager.sqlite3-wal` y `manager.sqlite3-shm` de esa carpeta después de haberla copiado y con la aplicación cerrada. Los adjuntos conservados están en una carpeta independiente; todavía falta incorporarlos a un respaldo integral.

## Límites actuales y trabajo pendiente

Ver [ROADMAP](docs/ROADMAP.md). Esta entrega todavía **no** incluye el bot, actualización automática de ejecutables, arrastrar archivos, búsqueda semántica, aplicación del estilo aprendido ni una instalación guiada de modelos. El botón Versiones abre las publicaciones oficiales. No se ejecutan paquetes descargados automáticamente.

La calidad de las propuestas de IA no se ha validado con un modelo real en este entorno. Los cambios pueden deshacerse. Si falta el modelo o una dependencia, el programa explica el error y conserva la entrada.

## Desarrollo

`python -m unittest discover -s tests -v`

`python -m app.main`

La persistencia está en `app/core.py`, la interpretación en `app/ai.py` y la interfaz en `app/main.py`. Las integraciones futuras deberán reutilizar el mismo servicio de operaciones y validación.
