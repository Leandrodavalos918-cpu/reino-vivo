REINO VIVO v1.2 — CRÓNICA PROFUNDA + SISTEMA DIVINO

Esta versión continúa sobre v1.1.

NOVEDAD PRINCIPAL
- Crónica diaria profunda basada en el estado y los acontecimientos generados por la simulación.
- Cada avance temporal crea una crónica persistente del día.
- La crónica resume población, rutinas, demografía, economía, rutas, conflictos y acontecimientos concretos.
- Los acontecimientos individuales siguen disponibles por separado.
- La vista del observador incluye un bloque de información interna de la simulación.

SISTEMA DIVINO
- Intervenciones inmediatas y programadas.
- Cartas, conflictos, riqueza, conocimiento, relaciones, recursos y clima.
- Registro de intervenciones y consecuencias.

IMPORTANTE
- SQLite se mantiene como base de esta rama prototipo para conservar compatibilidad con las versiones actuales.
- PostgreSQL sigue siendo objetivo de la arquitectura final.
- Si se despliega sobre un mundo existente, la nueva tabla daily_chronicles se crea automáticamente.

PRUEBAS
- server.py compila correctamente.
- JavaScript pasa comprobación de sintaxis.
- El servidor FastAPI inicia correctamente.
- /api/world responde.
- /api/advance responde.
- Al avanzar un día se genera una crónica persistente de más de 2.000 caracteres en la prueba.
