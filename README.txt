REINO VIVO v1.1 CORREGIDA — SISTEMA DIVINO

Esta versión corrige el bloqueo de interfaz que dejaba la pantalla en “Cargando...” y mostraba guiones cuando el JavaScript no llegaba a ejecutarse correctamente.

CORRECCIONES
- Se eliminaron secuencias de salto de línea mal formadas que provocaban un error de sintaxis JavaScript y detenían toda la aplicación.
- La interfaz ahora muestra un mensaje de error visible y un botón de reintento si la API no responde.
- Las llamadas a la API tienen un tiempo máximo de espera de 10 segundos y muestran el motivo del fallo.
- La página ahora carga también el panel Dios después de cargar correctamente el mundo.
- Se actualizó el título HTML a v1.1.
- Se añadieron Procfile y render.yaml para facilitar un despliegue correcto en Render usando el puerto PORT.

SISTEMA DIVINO
- Intervenciones inmediatas: riqueza, muerte, salvación, cartas, conflictos, conocimiento, relaciones, recursos y clima.
- Intervenciones futuras programadas.
- Historial divino.
- Cartas con destinatarios concretos.
- Fenómenos climáticos.
- Los NPC no conocen al usuario como entidad externa.

TECNOLOGÍA
- FastAPI + Uvicorn
- SQLite como base de prototipo heredada de v0.9
- Frontend HTML/CSS/JavaScript responsive
- world.db se genera al iniciar si no existe.

EJECUCIÓN LOCAL
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
Abrir / en el navegador.

RENDER
Build Command:
pip install -r requirements.txt

Start Command:
uvicorn server:app --host 0.0.0.0 --port $PORT

IMPORTANTE
La prueba realizada antes de entregar esta versión es local: servidor, API, base de datos, JavaScript y endpoints principales. No se puede afirmar desde aquí que tu servicio concreto de Render esté actualizado hasta que se despliegue este ZIP.
