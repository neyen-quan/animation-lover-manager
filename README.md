# Animation Lover Manager

Gestor personal para Windows: ideas, tareas, roadmap y notas. Los datos del equipo y las tareas se guardan en el perfil local del usuario, nunca en el repositorio.

## Instalar o actualizar

**Instalación nueva:** en [Releases](https://github.com/neyen-quan/animation-lover-manager/releases/latest), descargar `AnimationLoverManager-Windows-VERSION.zip`, extraer la carpeta completa y ejecutar `AnimationLoverManager.exe`. El paquete incluye Python y dependencias; no hace falta instalar Python en la PC.

**Desde una versión con actualizador:** Actualizar programa → Buscar actualizaciones → Descargar e instalar. Se conserva la ubicación del ejecutable y, por tanto, los accesos directos y anclados existentes. El instalador no cambia el perfil ni los archivos personales. La URL del canal puede cambiarse en la ventana de actualizaciones. También permite instalar un ZIP de actualización local (no el ZIP de instalación nueva).

**Transición única desde 0.1.0:** su botón Versiones solo abre el navegador; ese código no puede instalar una actualización. Desde esa página descargar únicamente `ActualizarAnimationLover.exe`, cerrar el programa anterior y ejecutar ese asistente. Seleccionar el `AnimationLoverManager.exe` original. El asistente consulta GitHub, verifica y descarga el paquete, y actualiza en la misma carpeta. No es necesario volver a descargar manualmente la aplicación completa. Desde entonces se usa el botón interno.

## Tablero visual

Modo oscuro con tabla agrupada por estado y vista de tarjetas sobre la misma información. La selección, los filtros y la alternancia de vistas no modifican las tareas. Las filas se abren con doble clic; las tarjetas, con un clic. Al pasar el mouse se resalta el elemento y aparece información ampliada; el menú de tres puntos ofrece las acciones existentes.

La entrada de voz, texto y archivos se abre desde **Soltar idea**. La captura puede plegarse para dedicar la ventana al tablero. Las barras de desplazamiento aparecen cuando el contenido lo necesita.

## Integridad y recuperación

El canal predeterminado es `https://github.com/neyen-quan/animation-lover-manager/releases/latest/download/latest.json`.

Se verifican HTTPS y redirecciones de GitHub, SHA-256 del ZIP, producto, versiones, rutas permitidas, tamaños, duplicados e inventario interno. SHA-256 verifica integridad; la confianza del canal depende de la cuenta y los permisos de publicación de GitHub, no es una firma independiente.

Se descarga el delta de la versión instalada si existe; en caso contrario se ofrece un paquete completo compatible. El delta contiene solo archivos modificados y dependencias nuevas, además de un inventario del destino. La base sin cambios debe coincidir antes de instalar. Archivos no declarados y datos personales no se eliminan.

El helper se ejecuta fuera de la instalación, espera el cierre, respalda lo reemplazado y verifica el reinicio. Si falla la escritura o el programa nuevo no confirma el inicio, revierte los archivos. No cierres Windows durante esa operación. Respaldos y resultados quedan en `%LOCALAPPDATA%/AnimationLoverManager/updates/` y `last-update.json`.

Un ZIP local es una elección explícita del usuario: se verifica su estructura e integridad interna, pero no acredita por sí solo quién lo creó. Usar paquetes oficiales.

## IA local

Instalar Ollama, descargar un modelo local compatible y escribir su nombre exacto en Ajustes. La aplicación usa `127.0.0.1:11434`; no llama a APIs pagas ni utiliza automáticamente una suscripción de ChatGPT. Imágenes requieren un modelo con visión. La primera transcripción descarga Whisper `small`; luego trabaja en CPU. El rendimiento y la calidad se verifican en el equipo de destino.

## Datos

SQLite, configuración y borrador: `%LOCALAPPDATA%/AnimationLoverManager/`. Los adjuntos de tareas se conservan solo cuando se marca esa opción. Finanzas conserva los comprobantes asociados por defecto. Copias SQLite después de cada cambio, con 30 versiones; en Ajustes se puede elegir una carpeta sincronizada por Drive. Finanzas agrega copias ZIP autocontenidas (base SQLite y comprobantes) en la subcarpeta `Finanzas` de ese destino. Los adjuntos de tareas todavía no se incluyen en esas copias. No hay restauración gráfica: con el programa cerrado, guardar primero una copia del perfil actual y restaurar juntos `manager.sqlite3` y `finance_receipts` desde el ZIP elegido, quitando los archivos WAL/SHM antiguos. La copia de Finanzas contiene también las tareas y la configuración de ese momento.

## Desarrollo y publicación

Python 3.12 en Windows. Dependencias directas y herramientas de compilación fijadas en `requirements.txt` y `requirements-build.txt`.

```powershell
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
python -m app.main
```

La versión se define en `app/__init__.py`. Un commit en main con versión nueva activa el workflow Windows: pruebas, interfaz en varias escalas, compilación, paquete completo, delta, helper, `latest.json`, tag y release. Si la versión ya está publicada completamente, otro commit con la misma versión ejecuta las pruebas pero no crea otra release.

La publicación se prepara como borrador; se suben todos los archivos antes de habilitarla como latest. Después se descargan y verifican los hashes publicados. No crear releases manuales desde la web.

Para recuperar una publicación fallida: Actions → Windows · verificar y publicar → Run workflow, usando el workflow de main e indicando el tag que se debe recompilar. Esto usa la definición actual del workflow para compilar el código del tag; no se necesita repetir un job viejo. Si el defecto está en el código de ese tag, corregir main e incrementar versión.

No subir bases SQLite, preferencias personales, adjuntos, tokens ni claves. Licencia MIT para este código; las dependencias conservan sus propias licencias.

## Finanzas

Todos los importes son USD y se guardan como centavos enteros. La caja es virtual y representa solo el dinero del negocio. `Retiro` registra bruto, comisión y neto; por defecto no ingresa en caja hasta confirmar recepción. La opción explícita de contar un retiro en tránsito lo incluye una sola vez. `Gasto` distingue caja y bolsillo personal; el segundo genera una deuda con la persona. `Reintegro` reduce caja y deuda sin duplicar el gasto. `Reparto` registra pagos de ganancias sin porcentajes automáticos. Los pagos entre integrantes reasignan deuda sin mover caja.

Finanzas → Registrar acepta texto, imágenes pegadas/adjuntas y audios. Ollama propone campos que siempre se revisan antes de guardar; las imágenes requieren un modelo local con visión. Un PDF se puede conservar como comprobante, pero para interpretarlo se necesita una captura o transcripción de sus datos. El modelo puede equivocarse: verificar importes, fechas y plataforma en la revisión.

Los insights mensuales registran ingresos informados y suscriptores por plataforma, con sus capturas, sin modificar caja. Los campos de texto permiten conservar métricas adicionales. El día 1 se muestran las plataformas pendientes del mes anterior.

Más opciones ofrece categorías editables, desglose de gastos, historial, respaldo e importación del punto de partida. El archivo privado `.almfinance` es un ZIP de datos (manifest `finance.json`, schema 1, product `AnimationLoverFinance`, entries con centavos y receipts por SHA-256). Solo se importa con el libro vacío, valida equipo, comprobantes y saldos, y muestra una confirmación del resumen antes de escribir. Nunca subir archivos de importación o comprobantes reales al repositorio público.
