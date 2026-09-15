REINO VIVO v0.8
Capa física del mundo: geografía, territorios, ciudades, barrios, propiedades, recursos y rutas.

Instalación local/Render: mantener los mismos archivos y comando de la versión anterior.
Esta versión migra una base v0.7 existente sin borrar world.db. Si no existe base, crea el mundo inicial.

Endpoints nuevos:
GET /api/layers
GET /api/cities/{city_id}
