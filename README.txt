REINO VIVO v1.0

Construido sobre la arquitectura de Reino Vivo v0.9.

Incluye lo anterior de v0.9 y añade:
- Fuerzas militares oficiales con unidades, comandantes y soldados individuales.
- Guardias privados con contratos y lealtad.
- Mercado básico de mercenarios.
- Equipamiento individual con calidad, condición, valor y procedencia.
- Suministros, entrenamiento, moral, disciplina, caballos y presupuesto de unidades.
- Incidentes de seguridad generados por condiciones locales.
- Casos judiciales con investigación, evidencia, incertidumbre y corrupción.
- Campañas y batallas emergentes; no existe una guerra guionizada obligatoria.
- Bajas individuales con consecuencias para los NPC.
- Nuevas capas de interfaz para ejército, seguridad, justicia y guerra.
- Endpoints /api/military y /api/security.

REGLA DE MIGRACIÓN
La aplicación conserva la base de datos existente. Si se abre sobre un world.db de v0.9, crea las nuevas tablas y datos militares sin borrar el mundo existente.
Si no existe world.db, crea el mundo inicial de 2.000 habitantes y toda la estructura v0.9 + v1.0.

EJECUCIÓN
1. Instalar dependencias:
   pip install -r requirements.txt
2. Ejecutar:
   uvicorn server:app --host 0.0.0.0 --port 8000
3. Abrir en el navegador la dirección indicada por el servidor.

IMPORTANTE
El archivo world.db se genera automáticamente al iniciar y NO se incluye en el ZIP para mantener la distribución limpia.
