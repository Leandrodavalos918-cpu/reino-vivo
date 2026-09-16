REINO VIVO v1.2.2 — Modo Dios + SQLite Lock Fix

Hotfix basado en v1.2.1.

Cambios principales:
- Las intervenciones manuales de Modo Dios comparten el mismo bloqueo de simulación que los ticks autónomos.
- Se evita la condición de carrera que provocaba: sqlite3.OperationalError: database is locked
- Las intervenciones programadas también quedan protegidas contra escrituras concurrentes.
- Se mantiene WAL + busy_timeout de SQLite.
- Probado localmente con 10 intervenciones simultáneas de Dar riqueza: 10/10 respuestas HTTP 200 y cambios de riqueza aplicados correctamente.

Render:
Build: pip install -r requirements.txt
Start: uvicorn server:app --host 0.0.0.0 --port $PORT
