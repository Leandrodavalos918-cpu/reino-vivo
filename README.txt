REINO VIVO v1.1 — SISTEMA DIVINO

Construido sobre la base de v0.9. Esta versión añade una capa de Dios/Observador externo.

NUEVO
- Panel 👁️ Dios en la interfaz.
- Intervenciones divinas sin permisos internos del mundo: matar/salvar personas, riqueza, cartas, conflictos, conocimiento, relaciones, recursos y clima.
- Cartas con destinatarios concretos y entrega inmediata o programada.
- Intervenciones futuras programadas por día del mundo.
- Historial de intervenciones y consecuencias registradas.
- Fenómenos climáticos divinos con duración.
- Las intervenciones no hacen que los NPC conozcan al usuario; se registran como causas desconocidas desde su perspectiva.
- Las consecuencias siguen siendo resueltas por la simulación: economía, información, relaciones, política, etc.

IMPORTANTE
- El proyecto sigue usando SQLite como prototipo heredado de v0.9. La migración final a PostgreSQL y worker persistente queda para una fase posterior.
- No se incluye world.db; se genera al iniciar para no sobrescribir el mundo local.

EJECUCIÓN
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
Abrir / en el navegador.
