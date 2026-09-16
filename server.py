from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3, random, os, time, asyncio, threading, math, json

SIM_LOCK = threading.Lock()
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "world.db")
app = FastAPI(title="Reino Vivo v1.2 — Crónica Profunda y Sistema Divino")

MALE = ["Aren","Bran","Corvin","Edric","Garen","Hugo","Ivar","Jon","Kael","Lucan","Marek","Nolan","Oren","Perrin","Ronan","Tomas","Dario","León","Mateo","Silas"]
FEMALE = ["Aelia","Brina","Celia","Fiona","Gwen","Isla","Lena","Mara","Neria","Olia","Rhea","Selene","Talia","Una","Vera","Yara","Elia","Nora","Livia","Mira"]
SURNAMES = ["Valen","Ríos","Montes","Alvar","Seren","Dorn","Vega","Luar","Cantos","Ravel","Neris","Ferrer","Solano","Mares","Tovar"]
JOBS = ["agricultor","artesano","mercader","pescador","minero","soldado","guardia","constructor","curandero","escriba","panadero","carpintero","tejedor","cocinero","marinero"]
GOALS = ["fundar una familia","acumular riqueza","ganar prestigio","proteger a su familia","aprender un oficio","viajar","tener hijos","conseguir una propiedad","mejorar su posición social"]
FEARS = ["pobreza","guerra","enfermedad","perder a un familiar","deudas","soledad","deshonra","perder su hogar"]
BELIEFS = ["tradición","honor","familia","fortuna","naturaleza","ley","comunidad"]
TRAITS = ["prudente","ambicioso","generoso","desconfiado","sociable","reservado","valiente","temeroso","honesto","calculador","religioso","curioso"]


def db():
    # SQLite en Render puede recibir lecturas y escrituras simultáneas.
    # WAL + busy_timeout reduce bloqueos entre el motor autónomo y las peticiones HTTP.
    c = sqlite3.connect(DB, timeout=60, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA busy_timeout=60000")
    return c


def add_col(c, table, col, typ, default=None):
    cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}
    if col not in cols:
        clause = f"ALTER TABLE {table} ADD COLUMN {col} {typ}"
        if default is not None:
            clause += f" DEFAULT {default}"
        c.execute(clause)


def init():
    c = db()
    # Activar WAL una sola vez para permitir lectores mientras el motor escribe.
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS world(id INTEGER PRIMARY KEY CHECK(id=1), year INTEGER, day INTEGER, speed INTEGER, paused INTEGER, last_real REAL);
    CREATE TABLE IF NOT EXISTS kingdoms(id INTEGER PRIMARY KEY, name TEXT, ruler TEXT, ruler_title TEXT, gold INTEGER, stability INTEGER);
    CREATE TABLE IF NOT EXISTS people(
        id INTEGER PRIMARY KEY, name TEXT, sex TEXT, age INTEGER, kingdom_id INTEGER, job TEXT,
        wealth INTEGER, status TEXT, alive INTEGER, education INTEGER, reputation INTEGER,
        goal TEXT, fear TEXT, belief TEXT, mother_id INTEGER, father_id INTEGER, partner_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS relationships(id INTEGER PRIMARY KEY AUTOINCREMENT, a_id INTEGER, b_id INTEGER, kind TEXT, strength INTEGER, UNIQUE(a_id,b_id,kind));
    CREATE TABLE IF NOT EXISTS knowledge(id INTEGER PRIMARY KEY AUTOINCREMENT, person_id INTEGER, subject TEXT, content TEXT, certainty INTEGER, source TEXT);
    CREATE TABLE IF NOT EXISTS parties(id INTEGER PRIMARY KEY AUTOINCREMENT, kingdom_id INTEGER, name TEXT, ideology TEXT, influence INTEGER, support INTEGER);
    CREATE TABLE IF NOT EXISTS party_members(id INTEGER PRIMARY KEY AUTOINCREMENT, party_id INTEGER, person_id INTEGER, role TEXT, loyalty INTEGER, UNIQUE(party_id,person_id));
    CREATE TABLE IF NOT EXISTS offices(id INTEGER PRIMARY KEY AUTOINCREMENT, kingdom_id INTEGER, title TEXT, person_id INTEGER, power INTEGER);
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, world_day INTEGER, title TEXT, description TEXT, importance INTEGER);
    CREATE TABLE IF NOT EXISTS daily_chronicles(id INTEGER PRIMARY KEY AUTOINCREMENT, world_day INTEGER UNIQUE, title TEXT, narrative TEXT, divine_summary TEXT DEFAULT '', created_at REAL);
    CREATE TABLE IF NOT EXISTS regions(id INTEGER PRIMARY KEY, kingdom_id INTEGER, name TEXT, terrain TEXT, climate TEXT, elevation INTEGER, fertility INTEGER, security INTEGER, description TEXT);
    CREATE TABLE IF NOT EXISTS cities(id INTEGER PRIMARY KEY, region_id INTEGER, kingdom_id INTEGER, name TEXT, city_type TEXT, population_target INTEGER, wealth INTEGER, security INTEGER, walls INTEGER, port INTEGER, founded_year INTEGER, description TEXT);
    CREATE TABLE IF NOT EXISTS districts(id INTEGER PRIMARY KEY, city_id INTEGER, name TEXT, district_type TEXT, wealth INTEGER, security INTEGER, population INTEGER, description TEXT);
    CREATE TABLE IF NOT EXISTS properties(id INTEGER PRIMARY KEY AUTOINCREMENT, city_id INTEGER, district_id INTEGER, owner_id INTEGER, name TEXT, property_type TEXT, value INTEGER, condition INTEGER, workers INTEGER, security INTEGER, production TEXT, history TEXT);
    CREATE TABLE IF NOT EXISTS resources(id INTEGER PRIMARY KEY AUTOINCREMENT, region_id INTEGER, resource_type TEXT, quantity INTEGER, quality INTEGER, extraction INTEGER);
    CREATE TABLE IF NOT EXISTS routes(id INTEGER PRIMARY KEY AUTOINCREMENT, from_city_id INTEGER, to_city_id INTEGER, route_type TEXT, distance INTEGER, safety INTEGER, capacity INTEGER, condition INTEGER);
    CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY AUTOINCREMENT, world_day INTEGER, kingdom_id INTEGER, type TEXT, title TEXT, status TEXT, intensity INTEGER, location TEXT, parties TEXT, cause TEXT, description TEXT);
    CREATE TABLE IF NOT EXISTS markets(id INTEGER PRIMARY KEY AUTOINCREMENT, city_id INTEGER, good TEXT, stock INTEGER, demand INTEGER, base_price INTEGER, price INTEGER, last_change INTEGER DEFAULT 0, UNIQUE(city_id,good));
    CREATE TABLE IF NOT EXISTS businesses(id INTEGER PRIMARY KEY AUTOINCREMENT, city_id INTEGER, owner_id INTEGER, name TEXT, business_type TEXT, capital INTEGER, workers INTEGER, stock INTEGER, revenue INTEGER, expenses INTEGER, active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS shipments(id INTEGER PRIMARY KEY AUTOINCREMENT, route_id INTEGER, good TEXT, quantity INTEGER, origin_city INTEGER, destination_city INTEGER, status TEXT, days_left INTEGER, price_paid INTEGER, owner_id INTEGER, created_day INTEGER);
    CREATE TABLE IF NOT EXISTS loans(id INTEGER PRIMARY KEY AUTOINCREMENT, borrower_id INTEGER, lender_id INTEGER, principal INTEGER, remaining INTEGER, interest INTEGER, status TEXT, created_day INTEGER);
    CREATE TABLE IF NOT EXISTS divine_interventions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, world_day INTEGER, action TEXT, target_type TEXT, target_id INTEGER,
        parameters TEXT, description TEXT, consequence TEXT DEFAULT '', created_at REAL
    );
    CREATE TABLE IF NOT EXISTS divine_schedules(
        id INTEGER PRIMARY KEY AUTOINCREMENT, execute_day INTEGER, action TEXT, target_type TEXT, target_id INTEGER,
        parameters TEXT, description TEXT, active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS letters(
        id INTEGER PRIMARY KEY AUTOINCREMENT, world_day INTEGER, sender TEXT, recipient_id INTEGER, content TEXT,
        delivered INTEGER DEFAULT 0, divine_origin INTEGER DEFAULT 1, delivery_day INTEGER, status TEXT DEFAULT 'programada'
    );
    CREATE TABLE IF NOT EXISTS divine_weather(
        id INTEGER PRIMARY KEY AUTOINCREMENT, start_day INTEGER, end_day INTEGER, region_id INTEGER, weather TEXT, intensity INTEGER,
        description TEXT, active INTEGER DEFAULT 1
    );
    """)
    # v0.7 additions. Safe on an existing v0.6 database.
    additions = [
        ("people","hunger","INTEGER",30),("people","energy","INTEGER",70),("people","social","INTEGER",55),("people","security","INTEGER",70),
        ("people","health","INTEGER",90),("people","morale","INTEGER",65),("people","trait","TEXT","'prudente'"),("people","secondary_trait","TEXT","'sociable'"),
        ("people","monthly_income","INTEGER",20),("people","monthly_expense","INTEGER",12),("people","home_quality","INTEGER",50),("people","routine","TEXT","'trabajo'"),
        ("people","memory","TEXT","''"),("people","last_action","TEXT","'descansó'"),("people","last_action_day","INTEGER",1),("people","birth_day","INTEGER",1),
        ("events","cause","TEXT","''"),("events","location","TEXT","''"),("events","actors","TEXT","''")
    ]
    for t,col,typ,d in additions: add_col(c,t,col,typ,d)

    if c.execute("SELECT COUNT(*) FROM world").fetchone()[0] == 0:
        c.execute("INSERT INTO world VALUES(1,247,1,1,0,?)", (time.time(),))
        c.execute("INSERT INTO kingdoms VALUES(1,'Aurelia','Elira I','Reina',100000,82)")
        c.execute("INSERT INTO kingdoms VALUES(2,'Valdoria','Darian II','Rey',100000,78)")
        random.seed(247)
        pid=1
        for k in (1,2):
            for i in range(1000):
                sex="M" if i<500 else "F"
                names=MALE if sex=="M" else FEMALE
                age=random.randint(1,75)
                adult=age>=15
                job=random.choice(JOBS) if adult else "estudiante"
                wealth=random.randint(10,500) if adult else random.randint(1,30)
                status="noble" if i<20 else ("real" if i<25 else "común")
                trait=random.choice(TRAITS); trait2=random.choice(TRAITS)
                income=random.randint(18,55) if adult else 0
                expense=random.randint(8,30) if adult else random.randint(1,5)
                c.execute("""INSERT INTO people(id,name,sex,age,kingdom_id,job,wealth,status,alive,education,reputation,goal,fear,belief,mother_id,father_id,partner_id,hunger,energy,social,security,health,morale,trait,secondary_trait,monthly_income,monthly_expense,home_quality,routine,memory,last_action,last_action_day,birth_day)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (pid,f"{random.choice(names)} {random.choice(SURNAMES)}",sex,age,k,job,wealth,status,1,random.randint(0,100),random.randint(0,100),random.choice(GOALS),random.choice(FEARS),random.choice(BELIEFS),None,None,None,
                 random.randint(5,55),random.randint(35,95),random.randint(30,90),random.randint(35,90),random.randint(60,100),random.randint(40,90),trait,trait2,income,expense,random.randint(25,85),job,"", "trabajó" if adult else "estudió",1,max(1,1-age)))
                pid+=1
        seed_families(c)
        seed_politics(c)
        add_event(c,1,"Nacimiento del Reino Vivo","Dos reinos comienzan una nueva era con 2.000 habitantes. Las primeras familias, oficios y alianzas políticas ya forman una red social en movimiento.",5,cause="condiciones iniciales",location="Aurelia y Valdoria")
    else:
        # Enrich existing v0.6 inhabitants without resetting the world.
        count=c.execute("SELECT COUNT(*) FROM people").fetchone()[0]
        if count:
            c.execute("UPDATE people SET hunger=COALESCE(hunger,30), energy=COALESCE(energy,70), social=COALESCE(social,55), security=COALESCE(security,70), health=COALESCE(health,90), morale=COALESCE(morale,65)")
            c.execute("UPDATE people SET trait=COALESCE(NULLIF(trait,''),?), secondary_trait=COALESCE(NULLIF(secondary_trait,''),?), monthly_income=CASE WHEN monthly_income IS NULL OR monthly_income=0 THEN CASE WHEN age>=15 THEN 25 ELSE 0 END ELSE monthly_income END, monthly_expense=CASE WHEN monthly_expense IS NULL OR monthly_expense=0 THEN CASE WHEN age>=15 THEN 12 ELSE 3 END ELSE monthly_expense END, home_quality=COALESCE(home_quality,50), routine=COALESCE(NULLIF(routine,''),job)" ,(random.choice(TRAITS),random.choice(TRAITS)))
    ensure_physical_world(c)
    ensure_economy(c)
    c.commit(); c.close()


def ensure_physical_world(c):
    # v0.8 builds a persistent physical layer without resetting an existing world.
    if c.execute("SELECT COUNT(*) FROM regions").fetchone()[0] == 0:
        region_defs=[
            (1,1,"Llanuras de Aurelia","llanura","templado",120,86,78,"Gran zona agrícola atravesada por ríos y caminos antiguos."),
            (2,1,"Bosque Alto","bosque","húmedo",420,62,72,"Bosques densos y colinas con madera, caza y minerales."),
            (3,1,"Costa de Puerto Alba","costa","marítimo",20,58,76,"Costa abierta con bahías, pesca y rutas marítimas."),
            (4,2,"Valle de Valdoria","llanura","templado",180,82,74,"Valle fértil donde se concentran granjas y aldeas."),
            (5,2,"Montes de Valdoria","montaña","frío de altura",900,48,68,"Cordillera rica en piedra y vetas minerales."),
            (6,2,"Bahía Gris","costa","marítimo",30,55,70,"Costa rocosa con puerto natural y actividad pesquera.")
        ]
        c.executemany("INSERT INTO regions VALUES(?,?,?,?,?,?,?,?,?)",region_defs)
        city_defs=[
            (1,1,1,"Puerto Alba","portuaria",420,78,76,1,1,220,"Puerto comercial y pesquero de Aurelia."),
            (2,1,1,"Río Claro","agrícola",340,65,80,0,0,225,"Ciudad agrícola junto a un gran río."),
            (3,2,1,"Bosque Alto","forestal",240,54,70,0,0,230,"Asentamiento forestal cercano a colinas minerales."),
            (4,4,2,"Corona","capital",430,82,78,1,0,218,"Capital administrativa y centro de la corte."),
            (5,5,2,"Monteluz","minera",250,61,67,1,0,228,"Ciudad de montaña dedicada a minería y metalurgia."),
            (6,6,2,"Bahía Gris","portuaria",300,63,71,1,1,224,"Puerto de Valdoria y puerta del comercio marítimo.")
        ]
        c.executemany("INSERT INTO cities VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",city_defs)
        districts=[
            (1,1,"Centro del Puerto","comercial",78,76,120,"Mercados, almacenes y casas de comerciantes."),(2,1,"Barrio de Pescadores","obrero",42,68,110,"Viviendas y talleres junto al muelle."),(3,1,"Colina Noble","noble",92,88,70,"Residencias de familias ricas y funcionarios."),
            (4,2,"Mercado del Río","comercial",65,80,115,"Mercado principal de granos y ganado."),(5,2,"Barrio de Granjeros","rural",48,78,150,"Casas de trabajadores agrícolas."),(6,2,"Plaza del Consejo","administrativo",76,84,75,"Oficinas y edificios públicos."),
            (7,3,"Barrio del Bosque","obrero",45,70,110,"Aserraderos, talleres y viviendas."),(8,3,"Camino Minero","industrial",52,65,80,"Ruta hacia canteras y vetas."),
            (9,4,"Distrito Real","noble",94,91,80,"Palacio, casas nobles y edificios de la corte."),(10,4,"Mercado Central","comercial",72,79,140,"Comercio mayorista y minorista."),(11,4,"Barrio Popular","obrero",40,67,150,"Zona densamente poblada de trabajadores."),
            (12,5,"Ciudad Alta","noble",70,74,70,"Residencias de propietarios mineros."),(13,5,"Barrio de Herreros","industrial",58,65,100,"Forjas y talleres metalúrgicos."),(14,5,"Campamento Minero","obrero",38,58,90,"Viviendas de mineros y transportistas."),
            (15,6,"Muelle Gris","comercial",66,72,105,"Muelle y almacenes portuarios."),(16,6,"Barrio de Marineros","obrero",45,64,100,"Tabernas y viviendas de tripulantes."),(17,6,"Plaza de la Bahía","administrativo",68,78,95,"Administración local y mercado.")
        ]
        c.executemany("INSERT INTO districts VALUES(?,?,?,?,?,?,?,?)",districts)
        res=[(1,1,"trigo",900,82,62),(2,1,"madera",500,76,45),(3,2,"pesca",650,80,58),(4,2,"madera",800,85,60),(5,2,"hierro",380,68,32),(6,3,"pescado",700,77,65),(7,4,"trigo",850,86,61),(8,5,"hierro",720,82,58),(9,5,"piedra",900,88,70),(10,6,"pescado",620,79,55),(11,6,"sal",400,74,42)]
        c.executemany("INSERT INTO resources(id,region_id,resource_type,quantity,quality,extraction) VALUES(?,?,?,?,?,?)",res)
        routes=[(1,2,"camino",95,82,180,78),(2,3,"camino",70,72,120,69),(1,3,"camino",110,74,120,72),(4,5,"camino montañoso",130,61,90,64),(5,6,"camino",150,66,110,68),(4,6,"carretera",125,73,150,76),(1,6,"marítima",210,69,220,73)]
        c.executemany("INSERT INTO routes(from_city_id,to_city_id,route_type,distance,safety,capacity,condition) VALUES(?,?,?,?,?,?,?)",routes)
        for cid in range(1,7):
            for did in [r[0] for r in districts if r[1]==cid]:
                for _ in range(5 if cid in (1,4) else 3):
                    owner=c.execute("SELECT id FROM people WHERE alive=1 AND kingdom_id=? ORDER BY RANDOM() LIMIT 1",(1 if cid<=3 else 2,)).fetchone()
                    owner_id=owner[0] if owner else None
                    typ=random.choice(["casa","taller","tienda","almacén","finca"]); val=random.randint(120,1600)
                    c.execute("INSERT INTO properties(city_id,district_id,owner_id,name,property_type,value,condition,workers,security,production,history) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(cid,did,owner_id,f"{typ.title()} {cid}-{did}-{random.randint(10,99)}",typ,val,random.randint(55,95),random.randint(0,8),random.randint(40,90),random.choice(["trigo","madera","pescado","metal","comercio","servicios","ninguna"]),"Propiedad registrada al inicio de la capa física."))
        # Place every existing inhabitant in a city and district if their schema does not yet have it.
    add_col(c,"people","city_id","INTEGER",None); add_col(c,"people","district_id","INTEGER",None); add_col(c,"people","property_id","INTEGER",None)
    missing=c.execute("SELECT id,kingdom_id FROM people WHERE city_id IS NULL AND alive=1").fetchall()
    city_by_k={1:[1,2,3],2:[4,5,6]}
    for person in missing:
        cid=random.choice(city_by_k[person["kingdom_id"]]); ds=[r[0] for r in c.execute("SELECT id FROM districts WHERE city_id=?",(cid,)).fetchall()]; did=random.choice(ds)
        c.execute("UPDATE people SET city_id=?,district_id=? WHERE id=?",(cid,did,person["id"]))
    # Sync city population counters from actual inhabitants.
    for cid in range(1,7):
        n=c.execute("SELECT COUNT(*) FROM people WHERE alive=1 AND city_id=?",(cid,)).fetchone()[0]
        c.execute("UPDATE cities SET population_target=? WHERE id=?",(max(n,1),cid))


def seed_families(c):
    for k in (1,2):
        males=[r["id"] for r in c.execute("SELECT id FROM people WHERE kingdom_id=? AND sex='M' AND age BETWEEN 20 AND 55",(k,))]
        females=[r["id"] for r in c.execute("SELECT id FROM people WHERE kingdom_id=? AND sex='F' AND age BETWEEN 20 AND 50",(k,))]
        random.shuffle(males); random.shuffle(females)
        for a,b in zip(males[:170],females[:170]):
            if random.random()<.55:
                c.execute("UPDATE people SET partner_id=? WHERE id=?",(b,a)); c.execute("UPDATE people SET partner_id=? WHERE id=?",(a,b))
                strength=random.randint(45,90)
                c.execute("INSERT OR IGNORE INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?)",(a,b,"pareja",strength))
                c.execute("INSERT OR IGNORE INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?)",(b,a,"pareja",strength))
        # A few friendship links create a social network from day one.
        adults=[r["id"] for r in c.execute("SELECT id FROM people WHERE kingdom_id=? AND age>=15",(k,))]
        for _ in range(130):
            if len(adults)<2: break
            a,b=random.sample(adults,2)
            c.execute("INSERT OR IGNORE INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?)",(a,b,"amistad",random.randint(30,80)))


def seed_politics(c):
    if c.execute("SELECT COUNT(*) FROM parties").fetchone()[0]: return
    party_defs={1:[("Tradición Real","tradicionalista"),("Reformistas de la Corona","reformista"),("Liga Mercantil","mercantil")],2:[("Orden del Reino","tradicionalista"),("Consejo de Renovación","reformista"),("Alianza de Comerciantes","mercantil")]}
    for k,defs in party_defs.items():
        nobles=[r["id"] for r in c.execute("SELECT id FROM people WHERE kingdom_id=? AND status='noble' AND alive=1",(k,))]
        random.shuffle(nobles)
        for name,ideology in defs:
            c.execute("INSERT INTO parties(kingdom_id,name,ideology,influence,support) VALUES(?,?,?,?,?)",(k,name,ideology,random.randint(20,45),random.randint(15,40)))
            party_id=c.execute("SELECT last_insert_rowid()").fetchone()[0]
            for nid in nobles[:random.randint(4,9)]:
                c.execute("INSERT OR IGNORE INTO party_members(party_id,person_id,role,loyalty) VALUES(?,?,?,?)",(party_id,nid,"miembro",random.randint(45,90)))
            nobles=nobles[6:] if len(nobles)>6 else []
    if c.execute("SELECT COUNT(*) FROM offices").fetchone()[0]==0:
        for k in (1,2):
            nobles=[r["id"] for r in c.execute("SELECT id FROM people WHERE kingdom_id=? AND status='noble' AND alive=1 ORDER BY RANDOM()",(k,))]
            for (title,power),nid in zip([("Consejero Real",40),("Maestre de Finanzas",35),("Maestre de Leyes",30),("Comandante de la Guardia",35)],nobles):
                c.execute("INSERT INTO offices(kingdom_id,title,person_id,power) VALUES(?,?,?,?)",(k,title,nid,power))


GOOD_BASE={"trigo":10,"madera":14,"pescado":12,"hierro":22,"piedra":8,"sal":16,"metal":32,"comercio":18,"servicios":15}

def ensure_economy(c):
    # Seed market ledgers without resetting an existing world.
    if c.execute("SELECT COUNT(*) FROM markets").fetchone()[0]==0:
        for city in c.execute("SELECT id FROM cities ORDER BY id").fetchall():
            cid=city[0]
            goods=["trigo","madera","pescado","hierro","piedra","sal"]
            for g in goods:
                stock=random.randint(90,260); demand=random.randint(80,240); base=GOOD_BASE[g]
                price=max(1,round(base*(1+demand/max(stock,1)*0.45)))
                c.execute("INSERT OR IGNORE INTO markets(city_id,good,stock,demand,base_price,price,last_change) VALUES(?,?,?,?,?,?,?)",(cid,g,stock,demand,base,price,0))
    if c.execute("SELECT COUNT(*) FROM businesses").fetchone()[0]==0:
        for city in c.execute("SELECT id,kingdom_id,name FROM cities").fetchall():
            cid,kid,name=city
            owners=c.execute("SELECT id FROM people WHERE alive=1 AND kingdom_id=? AND age>=18 ORDER BY RANDOM() LIMIT 6",(kid,)).fetchall()
            for i,o in enumerate(owners[:4]):
                typ=random.choice(["panadería","taller","tienda","granja","carpintería","pesquería"])
                c.execute("INSERT INTO businesses(city_id,owner_id,name,business_type,capital,workers,stock,revenue,expenses,active) VALUES(?,?,?,?,?,?,?,?,?,1)",(cid,o[0],f"{typ.title()} de {name} {i+1}",typ,random.randint(300,1800),random.randint(1,6),random.randint(20,100),0,0))

def economy_daily_tick(c,wd):
    # Production, consumption and prices are local to each city.
    for m in c.execute("SELECT * FROM markets").fetchall():
        stock=m["stock"]; demand=m["demand"]
        delta_stock=0; delta_demand=0
        if m["good"]=="trigo": delta_stock=random.randint(2,9)
        elif m["good"]=="madera": delta_stock=random.randint(1,5)
        elif m["good"]=="pescado": delta_stock=random.randint(1,6)
        elif m["good"] in ("hierro","piedra","sal"): delta_stock=random.randint(0,3)
        # population creates continuous demand; local shocks create variation.
        pop=c.execute("SELECT COUNT(*) FROM people WHERE alive=1 AND city_id=?",(m["city_id"],)).fetchone()[0]
        delta_demand=max(1,round(pop/180))+random.choice([-1,0,0,1,2])
        stock=max(0,stock+delta_stock-delta_demand)
        demand=max(20,demand+delta_demand+random.choice([-3,-1,0,1,2]))
        scarcity=demand/max(stock,1)
        price=max(1,round(m["base_price"]*(0.55+min(3.5,scarcity)*0.45)))
        c.execute("UPDATE markets SET stock=?,demand=?,price=?,last_change=? WHERE id=?",(stock,demand,price,price-m["price"],m["id"]))
    # Businesses earn from local trade and pay workers/expenses.
    for b in c.execute("SELECT * FROM businesses WHERE active=1").fetchall():
        good={"panadería":"trigo","taller":"hierro","tienda":"sal","granja":"trigo","carpintería":"madera","pesquería":"pescado"}.get(b["business_type"],"trigo")
        m=c.execute("SELECT * FROM markets WHERE city_id=? AND good=?",(b["city_id"],good)).fetchone()
        if not m: continue
        output=max(1,b["workers"]//2+random.randint(0,2)); sales=min(output+random.randint(0,4),m["stock"])
        revenue=sales*m["price"]; expenses=max(1,b["workers"]*random.randint(2,5)+random.randint(1,8)); capital=max(0,b["capital"]+revenue-expenses)
        c.execute("UPDATE businesses SET capital=?,stock=max(0,stock+?-?),revenue=?,expenses=? WHERE id=?",(capital,output,sales,revenue,expenses,b["id"]))
        if capital<0: c.execute("UPDATE businesses SET active=0 WHERE id=?",(b["id"],))
    # Wages and household purchasing power.
    if wd%7==0:
        rows=c.execute("SELECT id,monthly_income,monthly_expense,wealth FROM people WHERE alive=1 AND age>=15").fetchall()
        for p in rows:
            wage=max(0,round(p["monthly_income"]/4)); cost=max(0,round(p["monthly_expense"]/4))
            c.execute("UPDATE people SET wealth=max(0,wealth+?) WHERE id=?",(wage-cost,p["id"]))
    # Occasional intercity shipment based on price differences.
    if wd%3==0:
        cities=[r[0] for r in c.execute("SELECT id FROM cities").fetchall()]
        if len(cities)>=2:
            origin,dest=random.sample(cities,2); good=random.choice(list(GOOD_BASE))
            a=c.execute("SELECT * FROM markets WHERE city_id=? AND good=?",(origin,good)).fetchone(); b=c.execute("SELECT * FROM markets WHERE city_id=? AND good=?",(dest,good)).fetchone()
            route=c.execute("SELECT * FROM routes WHERE (from_city_id=? AND to_city_id=?) OR (from_city_id=? AND to_city_id=?) ORDER BY safety DESC LIMIT 1",(origin,dest,dest,origin)).fetchone()
            if a and b and route and b["price"]>a["price"]*1.18 and a["stock"]>30:
                qty=min(20+random.randint(0,30),a["stock"],route["capacity"]//10); cost=qty*a["price"]
                owner=c.execute("SELECT id FROM people WHERE alive=1 AND kingdom_id=(SELECT kingdom_id FROM cities WHERE id=?) AND job='mercader' ORDER BY RANDOM() LIMIT 1",(origin,)).fetchone()
                if qty>0 and owner:
                    c.execute("UPDATE markets SET stock=stock-? WHERE id=?",(qty,a["id"]))
                    days=max(1,round(route["distance"]/70*(100-route["condition"]+40)/100))
                    c.execute("INSERT INTO shipments(route_id,good,quantity,origin_city,destination_city,status,days_left,price_paid,owner_id,created_day) VALUES(?,?,?,?,?,?,?,?,?,?)",(route["id"],good,qty,origin,dest,"en tránsito",days,cost,owner[0],wd))
                    if random.random()<.25: add_event(c,wd,"Una caravana parte hacia otro mercado",f"Una carga de {good} salió de una ciudad con destino a un mercado donde el precio era más alto.",2,cause="diferencia local de precios",location=f"ruta {origin}→{dest}")
    # Advance existing shipments.
    for sh in c.execute("SELECT * FROM shipments WHERE status='en tránsito'").fetchall():
        left=sh["days_left"]-1
        if left>0:
            c.execute("UPDATE shipments SET days_left=? WHERE id=?",(int(left),int(sh["id"])))
        else:
            c.execute("UPDATE markets SET stock=stock+? WHERE city_id=? AND good=?",(sh["quantity"],sh["destination_city"],sh["good"]))
            c.execute("UPDATE shipments SET status='entregado',days_left=0 WHERE id=?",(int(sh["id"]),))
            if random.random()<.35:
                city=c.execute("SELECT name FROM cities WHERE id=?",(sh["destination_city"],)).fetchone()[0]
                add_event(c,wd,"Llega una carga al mercado",f"Una carga de {sh['quantity']} unidades de {sh['good']} llegó a {city} después de viajar por tierra o agua.",2,cause="comercio interurbano",location=city)
    # Rare price shock events driven by real scarcity.
    if wd%5==0:
        m=c.execute("SELECT m.*,c.name city FROM markets m JOIN cities c ON c.id=m.city_id WHERE m.demand>m.stock*2.4 ORDER BY (m.demand-max(m.stock,1)) DESC LIMIT 1").fetchone()
        if m and random.random()<.65:
            add_event(c,wd,"Escasez en un mercado",f"La oferta de {m['good']} en {m['city']} quedó por debajo de la demanda y su precio subió a {m['price']} monedas.",3,cause="oferta insuficiente frente a la demanda",location=m['city'])

def world_day(w): return (w["year"]-247)*365+w["day"]


def create_daily_chronicle(c, wd, before, births, deaths):
    """Build a long daily chronicle strictly from the state and events produced by this simulation tick."""
    w=c.execute("SELECT * FROM world WHERE id=1").fetchone()
    pop=c.execute("SELECT COUNT(*) FROM people WHERE alive=1").fetchone()[0]
    adults=c.execute("SELECT COUNT(*) FROM people WHERE alive=1 AND age>=15").fetchone()[0]
    markets=c.execute("SELECT COUNT(*) FROM markets").fetchone()[0]
    shipments=c.execute("SELECT COUNT(*) FROM shipments WHERE status='en tránsito'").fetchone()[0]
    businesses=c.execute("SELECT COUNT(*) FROM businesses WHERE active=1").fetchone()[0]
    conflicts=c.execute("SELECT COUNT(*) FROM conflicts WHERE status='activo'").fetchone()[0]
    avg_price=round(c.execute("SELECT COALESCE(AVG(price),0) FROM markets").fetchone()[0])
    avg_wealth=round(c.execute("SELECT COALESCE(AVG(wealth),0) FROM people WHERE alive=1").fetchone()[0])
    actions=c.execute("SELECT last_action,COUNT(*) n FROM people WHERE alive=1 AND last_action_day=? GROUP BY last_action ORDER BY n DESC",(wd,)).fetchall()
    action_text=', '.join(f"{r['n']} {r['last_action']}" for r in actions[:5]) or 'rutinas cotidianas sin cambios destacados'
    recent=c.execute("SELECT * FROM events WHERE world_day=? ORDER BY importance DESC,id ASC LIMIT 12",(wd,)).fetchall()
    # Pick factual market pressure from current state.
    tight=c.execute("SELECT m.good,c.name,m.stock,m.demand,m.price FROM markets m JOIN cities c ON c.id=m.city_id WHERE m.demand>m.stock*1.7 ORDER BY (m.demand-max(m.stock,1)) DESC LIMIT 3").fetchall()
    kingdom_rows=c.execute("SELECT id,name,gold,stability FROM kingdoms ORDER BY id").fetchall()
    city_rows=c.execute("SELECT name,wealth,security,population_target FROM cities ORDER BY wealth DESC LIMIT 6").fetchall()
    route_rows=c.execute("SELECT a.name af,b.name bt,r.safety,r.condition FROM routes r JOIN cities a ON a.id=r.from_city_id JOIN cities b ON b.id=r.to_city_id ORDER BY r.safety ASC LIMIT 2").fetchall()
    paragraphs=[]
    paragraphs.append(f"El día {wd} transcurrió con {pop:,} habitantes vivos, de los cuales {adults:,} son mayores de 14 años. La vida cotidiana continuó alrededor del trabajo, el descanso, la alimentación, las relaciones y la búsqueda de ingresos. Entre las acciones registradas hoy destacan {action_text}.")
    if births or deaths:
        btxt = ', '.join(x[0] if isinstance(x, tuple) else str(x) for x in births[:6]) if births else 'ningún nacimiento registrado'
        dtxt = ', '.join(x['name'] for x in deaths[:6]) if deaths else 'ninguna muerte registrada'
        paragraphs.append(f"La demografía también cambió. Nacieron {len(births)} personas ({btxt}) y murieron {len(deaths)}. Las muertes registradas corresponden a {dtxt}. Cada nacimiento y cada muerte modifica familias, relaciones, herencias, trabajo y las decisiones futuras de quienes quedan vinculados.")
    else:
        paragraphs.append("No se registraron nacimientos ni muertes durante esta jornada. La estructura demográfica permaneció estable por ahora, aunque las familias y relaciones continuaron evolucionando en segundo plano.")
    if tight:
        items='; '.join(f"{r['good']} en {r['name']} (stock {r['stock']}, demanda {r['demand']}, precio {r['price']})" for r in tight)
        paragraphs.append(f"En la economía, los mercados operaron con {markets} plazas activas y {businesses} negocios activos. El precio medio registrado fue de {avg_price} monedas y la riqueza media individual fue de {avg_wealth}. Se observó presión de demanda en {items}. Esto no significa automáticamente una crisis: los comerciantes y hogares reaccionan de forma distinta según sus reservas y necesidades.")
    else:
        paragraphs.append(f"La actividad económica se mantuvo sin una escasez marcada en los mercados observados. Funcionaron {markets} mercados y {businesses} negocios activos; había {shipments} cargamentos en tránsito. El precio medio fue de {avg_price} monedas y la riqueza media individual, {avg_wealth} monedas.")
    if route_rows:
        routes='; '.join(f"{r['af']}–{r['bt']} (seguridad {r['safety']}%, condición {r['condition']}%)" for r in route_rows)
        paragraphs.append(f"El movimiento siguió dependiendo de las rutas físicas. Las conexiones con menor seguridad registradas hoy fueron {routes}. Había {shipments} envíos en tránsito, por lo que parte de la actividad comercial de este día todavía tendrá consecuencias en jornadas posteriores.")
    paragraphs.append(f"En política y seguridad, el mundo conserva {conflicts} conflictos activos. La estabilidad de los reinos y las relaciones entre sus grupos continúan cambiando según decisiones, recursos, información y acontecimientos anteriores; ningún acontecimiento aislado determina por sí solo el rumbo futuro.")
    if recent:
        detail=[]
        for e in recent[:8]:
            loc=f" en {e['location']}" if e['location'] else ''
            cause=f" La causa registrada fue {e['cause']}." if e['cause'] else ''
            detail.append(f"{e['title']}{loc}: {e['description']}{cause}")
        paragraphs.append("Entre los acontecimientos concretos del día se registraron: " + " ".join(detail))
    else:
        paragraphs.append("No hubo acontecimientos de alta importancia registrados en la crónica durante esta jornada. Eso no significa que el mundo estuviera inmóvil: las rutinas, decisiones pequeñas, movimientos y cambios internos continuaron y pueden adquirir importancia más adelante.")
    narrative='\n\n'.join(paragraphs)
    # Divine view exposes the full simulation-side state, not a fabricated prediction.
    hidden=[]
    unknown_knowledge=c.execute("SELECT COUNT(*) FROM knowledge WHERE certainty<50").fetchone()[0]
    hidden.append(f"La simulación registra {unknown_knowledge} piezas de información con certeza inferior al 50%, por lo que no todos los habitantes comparten una visión fiable de los hechos.")
    hidden.append(f"Estado interno al cierre: población {pop}, conflictos activos {conflicts}, envíos en tránsito {shipments}, precio medio {avg_price}.")
    if recent:
        hidden.append("El observador puede inspeccionar cada acontecimiento y sus actores desde las capas de Historia y Personas.")
    divine=' '.join(hidden)
    c.execute("INSERT OR REPLACE INTO daily_chronicles(world_day,title,narrative,divine_summary,created_at) VALUES(?,?,?,?,?)",(wd,f"Crónica del día {wd}",narrative,divine,time.time()))


def add_event(c,wd,title,desc,importance,cause="",location="",actors=""):
    c.execute("INSERT INTO events(world_day,title,description,importance,cause,location,actors) VALUES(?,?,?,?,?,?,?)",(wd,title,desc,importance,cause,location,actors))


def choose_action(p, context):
    # Lightweight utility model: no omniscience, only current needs + traits + situation.
    hunger=p["hunger"]; energy=p["energy"]; social=p["social"]; wealth=p["wealth"]; health=p["health"]
    options=[]
    if hunger>72: options.append(("comió",55+hunger))
    if energy<25: options.append(("descansó",65+(30-energy)))
    if social<25: options.append(("visitó a alguien cercano",45+(30-social)))
    if wealth<15 and p["age"]>=15: options.append(("buscó una oportunidad de ingreso",55+(20-wealth)))
    if context.get("market_tight") and p["job"] in ("mercader","panadero","artesano"): options.append(("revisó el mercado",65))
    if p["trait"] in ("ambicioso","calculador") and p["age"]>=18: options.append(("trabajó en su objetivo personal",48))
    if p["trait"] in ("sociable","generoso") and social<65: options.append(("conversó con un conocido",42))
    if not options: options=[("trabajó" if p["age"]>=15 else "estudió",50)]
    # Add a little uncertainty: people do not always pick the mathematically optimal choice.
    options.sort(key=lambda x:x[1]+random.randint(-15,15),reverse=True)
    return options[0][0]


def apply_action(c,p,action,wd):
    pid=p["id"]
    hunger=p["hunger"]; energy=p["energy"]; social=p["social"]; wealth=p["wealth"]
    income=max(0,p["monthly_income"])
    if action=="comió": hunger=max(0,hunger-45); wealth=max(0,wealth-random.randint(1,4)); energy=max(0,energy-3)
    elif action=="descansó": energy=min(100,energy+38); hunger=min(100,hunger+5)
    elif action=="visitó a alguien cercano": social=min(100,social+30); energy=max(0,energy-6)
    elif action=="buscó una oportunidad de ingreso": wealth+=random.randint(2,10); energy=max(0,energy-10)
    elif action=="revisó el mercado": social=max(0,social-2); energy=max(0,energy-4)
    elif action=="trabajó en su objetivo personal": wealth+=random.randint(1,6); energy=max(0,energy-9)
    elif action=="conversó con un conocido": social=min(100,social+18); energy=max(0,energy-3)
    elif action=="trabajó": wealth+=random.randint(1,5); energy=max(0,energy-14); hunger=min(100,hunger+8)
    elif action=="estudió": energy=max(0,energy-8); hunger=min(100,hunger+5)
    c.execute("UPDATE people SET hunger=?,energy=?,social=?,wealth=?,last_action=?,last_action_day=? WHERE id=?",(hunger,energy,social,wealth,action,wd,pid))


def relationship_tick(c,wd):
    rows=c.execute("SELECT * FROM relationships").fetchall()
    for r in rows:
        if r["a_id"]==r["b_id"]: continue
        drift=random.choice([-2,-1,0,0,1,1,2])
        c.execute("UPDATE relationships SET strength=? WHERE id=?",(max(0,min(100,r["strength"]+drift)),r["id"]))
    # Rare new friendship among socially active adults.
    if random.random()<0.22:
        row=c.execute("SELECT id,kingdom_id FROM people WHERE alive=1 AND age>=15 ORDER BY RANDOM() LIMIT 1").fetchone()
        if row:
            other=c.execute("SELECT id FROM people WHERE alive=1 AND kingdom_id=? AND age>=15 AND id!=? ORDER BY RANDOM() LIMIT 1",(row["kingdom_id"],row["id"])).fetchone()
            if other:
                c.execute("INSERT OR IGNORE INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?)",(row["id"],other["id"],"amistad",random.randint(25,55)))


def needs_and_daily_economy(c,wd):
    rows=c.execute("SELECT * FROM people WHERE alive=1").fetchall()
    context={"market_tight": random.random()<.12}
    for p in rows:
        # Natural daily drift.
        hunger=min(100,p["hunger"]+random.randint(3,8)); energy=max(0,p["energy"]-random.randint(3,10)); social=max(0,p["social"]-random.randint(0,3))
        if p["age"]<15: energy=min(100,energy+2)
        if hunger>85: health=max(0,p["health"]-random.randint(0,2)); morale=max(0,p["morale"]-1)
        else: health=min(100,p["health"]+random.choice([0,0,1]))
        action=choose_action(p,context)
        apply_action(c,p,action,wd)
        # monthly-like household accounting every 30 world days.
        if wd%30==0 and p["age"]>=15:
            delta=p["monthly_income"]-p["monthly_expense"]+random.randint(-4,5)
            c.execute("UPDATE people SET wealth=max(0,wealth+?),morale=max(0,min(100,morale+?)) WHERE id=?",(delta,1 if delta>=0 else -2,p["id"]))
        c.execute("UPDATE people SET hunger=?,energy=?,social=?,health=?,morale=? WHERE id=?",(hunger,energy,social,health,p["morale"],p["id"]))
        # Memory records meaningful personal experiences, not every trivial action.
        if action in ("buscó una oportunidad de ingreso","trabajó en su objetivo personal") and random.random()<.04:
            mem=(p["memory"] or "")
            text=f"Día {wd}: {action}."
            mem=(mem+" | "+text).strip(" |")[-900:]
            c.execute("UPDATE people SET memory=? WHERE id=?",(mem,p["id"]))


def death_tick(c,wd):
    deaths=[]
    rows=c.execute("SELECT * FROM people WHERE alive=1").fetchall()
    for p in rows:
        chance=.00002 if p["age"]<50 else (.00018 if p["age"]<65 else (.001 if p["age"]<75 else .004))
        if p["health"]<30: chance*=5
        if p["hunger"]>90: chance*=2
        if random.random()<chance:
            c.execute("UPDATE people SET alive=0 WHERE id=?",(p["id"],)); deaths.append(p)
            if p["partner_id"]:
                c.execute("UPDATE people SET partner_id=NULL WHERE id=?",(p["partner_id"],))
            if p["age"]>=60:
                add_event(c,wd,"Una muerte cambia una familia",f"{p['name']}, de {p['age']} años, murió en {kingdom_name(c,p['kingdom_id'])}. La pérdida afecta a las personas que dependían de él o ella.",3,cause="edad y salud",location=kingdom_name(c,p['kingdom_id']),actors=p['name'])
    return deaths


def birth_tick(c,wd):
    births=[]
    for k in (1,2):
        couples=c.execute("""SELECT m.id mother,f.id father FROM people m JOIN people f ON f.id=m.partner_id
        WHERE m.alive=1 AND f.alive=1 AND m.kingdom_id=? AND m.sex='F' AND m.age BETWEEN 18 AND 40 AND f.age BETWEEN 18 AND 50""",(k,)).fetchall()
        for couple in couples:
            if random.random()<0.0009:
                sex=random.choice(["M","F"]); name=f"{random.choice(MALE if sex=='M' else FEMALE)} {random.choice(SURNAMES)}"
                c.execute("""INSERT INTO people(name,sex,age,kingdom_id,job,wealth,status,alive,education,reputation,goal,fear,belief,mother_id,father_id,partner_id,hunger,energy,social,security,health,morale,trait,secondary_trait,monthly_income,monthly_expense,home_quality,routine,memory,last_action,last_action_day,birth_day)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(name,sex,0,k,"niño",random.randint(1,8),"común",1,0,20,"fundar una familia","enfermedad","familia",couple["mother"],couple["father"],None,20,95,65,65,95,85,random.choice(TRAITS),random.choice(TRAITS),0,3,50,"familia","", "nació",wd,wd))
                child=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                for a,b,kind in [(couple["mother"],child,"madre"),(couple["father"],child,"padre"),(child,couple["mother"],"hijo"),(child,couple["father"],"hijo")]:
                    c.execute("INSERT OR IGNORE INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?)",(a,b,kind,90))
                births.append((name,k,couple["mother"],couple["father"]))
                add_event(c,wd,"Nace un nuevo habitante",f"{name} nació en {kingdom_name(c,k)}. Sus padres deberán reorganizar su vida alrededor de la nueva familia.",3,cause="familia y circunstancias demográficas",location=kingdom_name(c,k),actors=name)
    return births


def kingdom_name(c,k):
    r=c.execute("SELECT name FROM kingdoms WHERE id=?",(k,)).fetchone(); return r[0] if r else "el reino"


def political_tick(c,wd):
    for party in c.execute("SELECT * FROM parties").fetchall():
        change=random.randint(-2,3)
        if party["ideology"]=="mercantil" and random.random()<.35: change+=1
        if party["ideology"]=="reformista" and random.random()<.20: change+=1
        c.execute("UPDATE parties SET support=?,influence=? WHERE id=?",(max(0,min(100,party["support"]+change)),max(5,min(100,party["influence"]+random.randint(-2,2))),party["id"]))
    for m in c.execute("SELECT * FROM party_members").fetchall():
        loyalty=max(10,min(100,m["loyalty"]+random.randint(-2,2))); c.execute("UPDATE party_members SET loyalty=? WHERE id=?",(loyalty,m["id"]))
        if loyalty<25 and random.random()<.05:
            c.execute("DELETE FROM party_members WHERE id=?",(m["id"],))
            add_event(c,wd,"Un noble cambia de bando","Un miembro de la nobleza abandonó una facción política y comenzó a buscar nuevos aliados.",3,cause="pérdida de confianza política")
    if random.random()<.10:
        p=c.execute("SELECT p.*,k.name kingdom FROM parties p JOIN kingdoms k ON k.id=p.kingdom_id ORDER BY RANDOM() LIMIT 1").fetchone()
        if p:
            titles=["Debate entre nobles","Disputa por impuestos","Coalición en formación","Presión de una facción","Negociación del consejo"]
            add_event(c,wd,random.choice(titles),f"En {p['kingdom']}, la facción {p['name']} ganó protagonismo. Sus miembros buscan apoyo, pero otros nobles no comparten necesariamente sus intereses.",random.randint(2,4),cause="cambio de apoyo e influencia",location=p["kingdom"],actors=p["name"])


def social_events(c,wd):
    # Events are generated from state; narration describes observed facts.
    if random.random()<.07:
        r=c.execute("SELECT * FROM people WHERE alive=1 AND age>=18 ORDER BY RANDOM() LIMIT 1").fetchone()
        if r:
            kind=random.choice(["mercado","familia","trabajo","rumor","viaje"])
            if kind=="mercado":
                add_event(c,wd,"Movimiento en el mercado",f"En {kingdom_name(c,r['kingdom_id'])}, {r['name']} pasó parte del día buscando mejores precios y oportunidades de intercambio.",2,cause="necesidad económica",location=kingdom_name(c,r['kingdom_id']),actors=r['name'])
            elif kind=="familia":
                add_event(c,wd,"Una familia toma una decisión",f"{r['name']} dedicó tiempo a resolver un asunto familiar. La decisión modificó ligeramente sus planes para los próximos días.",2,cause="relaciones y necesidades familiares",location=kingdom_name(c,r['kingdom_id']),actors=r['name'])
            elif kind=="trabajo":
                add_event(c,wd,"Un día de trabajo difícil",f"{r['name']} tuvo que reorganizar su jornada laboral. El cambio redujo su tiempo libre y afectó su cansancio.",1,cause="rutina y circunstancias laborales",location=kingdom_name(c,r['kingdom_id']),actors=r['name'])
            elif kind=="rumor":
                # Seed a rumor into two people, with limited certainty.
                a=r; b=c.execute("SELECT * FROM people WHERE alive=1 AND kingdom_id=? AND id!=? ORDER BY RANDOM() LIMIT 1",(r["kingdom_id"],r["id"])).fetchone()
                if b:
                    content=f"Se dice que {a['name']} está buscando una nueva oportunidad económica."
                    c.execute("INSERT INTO knowledge(person_id,subject,content,certainty,source) VALUES(?,?,?,?,?)",(b["id"],"rumor",content,random.randint(25,65),a["name"]))
                    add_event(c,wd,"Circula un rumor",f"Un rumor sobre {a['name']} comenzó a circular, aunque su veracidad todavía no está clara.",2,cause="transmisión social de información",location=kingdom_name(c,r['kingdom_id']),actors=a['name'])
            else:
                add_event(c,wd,"Viajeros en los caminos",f"Personas que se desplazan entre comunidades llevaron conversaciones y noticias de un lugar a otro.",2,cause="movimiento de población",location=kingdom_name(c,r['kingdom_id']))


def divine_log(c, wd, action, target_type, target_id, parameters, description, consequence=""):
    c.execute("INSERT INTO divine_interventions(world_day,action,target_type,target_id,parameters,description,consequence,created_at) VALUES(?,?,?,?,?,?,?,?)",
              (wd,action,target_type,target_id,json.dumps(parameters,ensure_ascii=False),description,consequence,time.time()))

def execute_divine(c, wd, action, target_type, target_id, params, description=""):
    # God has no simulation-side permission checks. The simulation only resolves consequences.
    consequence=""
    if action=="kill_person":
        person=c.execute("SELECT * FROM people WHERE id=?",(target_id,)).fetchone()
        if not person: raise HTTPException(404,"Persona no encontrada")
        if person["alive"]:
            c.execute("UPDATE people SET alive=0,health=0 WHERE id=?",(target_id,))
            # Property/business inheritance is intentionally left to normal social/economic systems.
            add_event(c,wd,"Una muerte inesperada",f"{person['name']} murió de forma repentina. La causa no pudo explicarse de inmediato.",4,cause="acontecimiento inexplicable",location=kingdom_name(c,person["kingdom_id"]),actors=person["name"])
            consequence="La muerte afecta a su familia, relaciones, trabajo, propiedades y otros sistemas en los siguientes ciclos."
    elif action=="save_person":
        person=c.execute("SELECT * FROM people WHERE id=?",(target_id,)).fetchone()
        if not person: raise HTTPException(404,"Persona no encontrada")
        c.execute("UPDATE people SET alive=1,health=max(50,health),morale=max(50,morale) WHERE id=?",(target_id,))
        consequence="La supervivencia mantiene abiertas todas las futuras ramas causales de esta persona."
        add_event(c,wd,"Una vida se prolonga",f"{person['name']} sobrevivió a un desenlace que parecía inevitable.",4,cause="acontecimiento inexplicable",location=kingdom_name(c,person["kingdom_id"]),actors=person["name"])
    elif action=="grant_wealth":
        amount=int(params.get("amount",10000)); kind=target_type
        if kind=="kingdom": c.execute("UPDATE kingdoms SET gold=gold+? WHERE id=?",(amount,target_id)); name=c.execute("SELECT name FROM kingdoms WHERE id=?",(target_id,)).fetchone()[0]
        elif kind=="person": c.execute("UPDATE people SET wealth=wealth+? WHERE id=?",(amount,target_id)); name=c.execute("SELECT name FROM people WHERE id=?",(target_id,)).fetchone()[0]
        else: raise HTTPException(400,"Objetivo de riqueza inválido")
        consequence=f"Se añadieron {amount} monedas a {name}; los mercados y decisiones futuras pueden reaccionar a la nueva riqueza."
        add_event(c,wd,"Una riqueza de origen desconocido",f"Una cantidad extraordinaria de riqueza apareció en manos de {name}.",4,cause="origen desconocido",location=name)
    elif action=="create_letter":
        recipient=c.execute("SELECT * FROM people WHERE id=? AND alive=1",(target_id,)).fetchone()
        if not recipient: raise HTTPException(404,"Destinatario no encontrado o fallecido")
        deliver_day=int(params.get("delivery_day",wd)); sender=params.get("sender","Un remitente desconocido"); content=params.get("content","")
        status="entregada" if deliver_day<=wd else "programada"
        c.execute("INSERT INTO letters(world_day,sender,recipient_id,content,delivered,divine_origin,delivery_day,status) VALUES(?,?,?,?,?,?,?,?)",(wd,sender,target_id,content,1 if status=="entregada" else 0,1,deliver_day,status))
        consequence="La carta entra en el sistema de información; el destinatario decide qué creer y qué hacer con ella."
        if status=="entregada": c.execute("INSERT INTO knowledge(person_id,subject,content,certainty,source) VALUES(?,?,?,?,?)",(target_id,"carta",content,random.randint(60,95),sender))
        else: c.execute("UPDATE letters SET status='programada' WHERE recipient_id=? AND delivery_day=?",(target_id,deliver_day))
        add_event(c,wd,"Una carta cambia de manos",f"Una carta fue preparada para {recipient['name']}.",3,cause="intervención desconocida",location=kingdom_name(c,recipient["kingdom_id"]),actors=recipient["name"])
    elif action=="create_conflict":
        kingdom_id=int(params.get("kingdom_id",1)); title=params.get("title","Conflicto inesperado"); cause=params.get("cause","causa desconocida"); intensity=max(1,min(100,int(params.get("intensity",35)))); location=params.get("location",kingdom_name(c,kingdom_id)); parties=params.get("parties","personas desconocidas")
        c.execute("INSERT INTO conflicts(world_day,kingdom_id,type,title,status,intensity,location,parties,cause,description) VALUES(?,?,?,?,?,?,?,?,?,?)",(wd,kingdom_id,params.get("type","social"),title,"activo",intensity,location,parties,cause,params.get("description","")))
        consequence="El conflicto queda sometido a las decisiones autónomas de las personas y organizaciones implicadas."
        add_event(c,wd,"Surge un conflicto",title,4,cause=cause,location=location,actors=parties)
    elif action=="reveal_knowledge":
        recipient=c.execute("SELECT * FROM people WHERE id=? AND alive=1",(target_id,)).fetchone()
        if not recipient: raise HTTPException(404,"Persona no encontrada")
        subject=params.get("subject","información"); content=params.get("content",""); certainty=max(0,min(100,int(params.get("certainty",100))))
        c.execute("INSERT INTO knowledge(person_id,subject,content,certainty,source) VALUES(?,?,?,?,?)",(target_id,subject,content,certainty,"origen desconocido"))
        consequence="El conocimiento fue entregado al NPC, pero su interpretación y uso siguen siendo autónomos."
    elif action=="erase_knowledge":
        subject=params.get("subject",""); c.execute("DELETE FROM knowledge WHERE person_id=? AND subject=?",(target_id,subject)); consequence="La información indicada fue retirada de la memoria informacional de ese NPC."
    elif action=="change_relationship":
        a=int(params.get("a_id",target_id)); b=int(params.get("b_id",0)); kind=params.get("kind","amistad"); strength=max(0,min(100,int(params.get("strength",80))))
        if not c.execute("SELECT id FROM people WHERE id=?",(a,)).fetchone() or not c.execute("SELECT id FROM people WHERE id=?",(b,)).fetchone(): raise HTTPException(404,"Persona no encontrada")
        c.execute("INSERT INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?) ON CONFLICT(a_id,b_id,kind) DO UPDATE SET strength=excluded.strength",(a,b,kind,strength))
        consequence="La relación queda modificada; futuras experiencias pueden hacerla evolucionar."
    elif action=="create_resource":
        region=int(params.get("region_id",target_id)); rtype=params.get("resource_type","oro"); qty=max(1,int(params.get("quantity",1000))); quality=max(1,min(100,int(params.get("quality",100))))
        c.execute("INSERT INTO resources(region_id,resource_type,quantity,quality,extraction) VALUES(?,?,?,?,?)",(region,rtype,qty,quality,max(1,min(100,int(params.get("extraction",100))))))
        consequence="El recurso entra en la economía física y puede afectar producción, comercio, precios y política."
    elif action=="weather":
        region=int(params.get("region_id",target_id)); start=wd; duration=max(1,int(params.get("duration",3))); weather=params.get("weather","tormenta"); intensity=max(1,min(100,int(params.get("intensity",50))))
        c.execute("INSERT INTO divine_weather(start_day,end_day,region_id,weather,intensity,description,active) VALUES(?,?,?,?,?,?,1)",(start,wd+duration-1,region,weather,intensity,params.get("description","Fenómeno meteorológico extraordinario")))
        consequence="El clima se convierte en una condición del mundo durante el período indicado y puede afectar agricultura, rutas, seguridad y guerra."
        add_event(c,wd,"Fenómeno meteorológico",f"Un episodio de {weather} afecta a la región.",4,cause="fenómeno natural inexplicable",location=str(region))
    else:
        raise HTTPException(400,"Intervención divina desconocida")
    divine_log(c,wd,action,target_type,target_id,params,description,consequence)
    return consequence

def process_divine_schedules(c,wd):
    rows=c.execute("SELECT * FROM divine_schedules WHERE active=1 AND execute_day<=? ORDER BY execute_day,id",(wd,)).fetchall()
    for r in rows:
        try:
            execute_divine(c,wd,r["action"],r["target_type"],r["target_id"],json.loads(r["parameters"] or "{}"),r["description"] or "")
            c.execute("UPDATE divine_schedules SET active=0 WHERE id=?",(r["id"],))
        except Exception as e:
            c.execute("UPDATE divine_schedules SET active=0 WHERE id=?",(r["id"],))
            add_event(c,wd,"Intervención divina no ejecutada",f"Una intervención programada no pudo resolverse: {e}",2,cause="error de objetivo",location="mundo")
    # Deliver scheduled divine letters through the information network.
    letters=c.execute("SELECT * FROM letters WHERE delivered=0 AND delivery_day<=? AND status='programada'",(wd,)).fetchall()
    for l in letters:
        recipient=c.execute("SELECT * FROM people WHERE id=? AND alive=1",(l["recipient_id"],)).fetchone()
        if recipient:
            c.execute("INSERT INTO knowledge(person_id,subject,content,certainty,source) VALUES(?,?,?,?,?)",(recipient["id"],"carta",l["content"],random.randint(55,95),l["sender"]))
            c.execute("UPDATE letters SET delivered=1,status='entregada' WHERE id=?",(l["id"],))
            add_event(c,wd,"Una carta llega a su destinatario",f"Una carta de {l['sender']} llegó a {recipient['name']}.",3,cause="correo y transmisión de información",location=kingdom_name(c,recipient["kingdom_id"]),actors=recipient["name"])
    c.execute("UPDATE divine_weather SET active=0 WHERE end_day<?",(wd,))

def _tick_unlocked(days=1):
    c=db()
    for _ in range(days):
        w=c.execute("SELECT * FROM world WHERE id=1").fetchone()
        wd=world_day(w)+1; day=w["day"]+1; year=w["year"]
        if day>365:
            day=1; year+=1
            c.execute("UPDATE people SET age=age+1 WHERE alive=1")
            add_event(c,wd,"Comienza un nuevo año",f"El año {year} comienza en Aurelia y Valdoria. Las personas continúan sus vidas mientras cambian lentamente las relaciones, fortunas y objetivos.",4,cause="paso del tiempo",location="Aurelia y Valdoria")
        before={
            "population": c.execute("SELECT COUNT(*) FROM people WHERE alive=1").fetchone()[0],
            "conflicts": c.execute("SELECT COUNT(*) FROM conflicts WHERE status='activo'").fetchone()[0],
            "shipments": c.execute("SELECT COUNT(*) FROM shipments WHERE status='en tránsito'").fetchone()[0]
        }
        process_divine_schedules(c,wd)
        needs_and_daily_economy(c,wd)
        economy_daily_tick(c,wd)
        relationship_tick(c,wd)
        births=birth_tick(c,wd)
        deaths=death_tick(c,wd)
        if wd%7==0: political_tick(c,wd)
        social_events(c,wd)
        c.execute("UPDATE world SET year=?,day=?,last_real=? WHERE id=1",(year,day,time.time()))
        create_daily_chronicle(c,wd,before,births,deaths)
    c.commit(); c.close()


def tick(days=1):
    with SIM_LOCK: _tick_unlocked(max(1,int(days)))


def _catch_up_unlocked():
    c=db(); w=c.execute("SELECT * FROM world WHERE id=1").fetchone(); c.close()
    missed=min(int(max(0,time.time()-w["last_real"])/86400*3),90)
    if missed and not w["paused"]: _tick_unlocked(missed)


def catch_up():
    with SIM_LOCK:
        _catch_up_unlocked()


async def background_loop():
    while True:
        try:
            c=db(); w=c.execute("SELECT * FROM world WHERE id=1").fetchone(); c.close()
            if not w["paused"]: tick(max(1,w["speed"]))
        except Exception:
            pass
        await asyncio.sleep(3600)


@app.on_event("startup")
async def startup():
    init(); catch_up(); asyncio.create_task(background_loop())

@app.get("/")
def home(): return FileResponse(os.path.join(BASE,"index.html"))

@app.get("/api/world")
def get_world():
    catch_up(); c=db()
    w=dict(c.execute("SELECT * FROM world WHERE id=1").fetchone())
    ks=[dict(x) for x in c.execute("SELECT * FROM kingdoms ORDER BY id")]
    pop=c.execute("SELECT COUNT(*) FROM people WHERE alive=1").fetchone()[0]
    nobles=c.execute("SELECT COUNT(*) FROM people WHERE alive=1 AND status='noble'").fetchone()[0]
    families=c.execute("SELECT COUNT(*) FROM people WHERE alive=1 AND partner_id IS NOT NULL").fetchone()[0]//2
    avg_health=round(c.execute("SELECT COALESCE(AVG(health),0) FROM people WHERE alive=1").fetchone()[0])
    avg_wealth=round(c.execute("SELECT COALESCE(AVG(wealth),0) FROM people WHERE alive=1").fetchone()[0])
    events=[dict(x) for x in c.execute("SELECT * FROM events ORDER BY id DESC LIMIT 15")]
    chronicles=[dict(x) for x in c.execute("SELECT * FROM daily_chronicles ORDER BY world_day DESC LIMIT 10")]
    parties=[dict(x) for x in c.execute("SELECT p.*,k.name AS kingdom FROM parties p JOIN kingdoms k ON k.id=p.kingdom_id ORDER BY k.id,p.influence DESC")]
    offices=[dict(x) for x in c.execute("SELECT o.*,p.name AS person_name,k.name AS kingdom FROM offices o JOIN people p ON p.id=o.person_id JOIN kingdoms k ON k.id=o.kingdom_id ORDER BY k.id,o.power DESC")]
    ppl=[dict(x) for x in c.execute("SELECT id,name,age,job,wealth,status,kingdom_id,goal,reputation,hunger,energy,social,health,morale,trait,secondary_trait,last_action,mother_id,father_id,partner_id FROM people WHERE alive=1 ORDER BY RANDOM() LIMIT 16")]
    economy={"markets":c.execute("SELECT COUNT(*) FROM markets").fetchone()[0],"businesses":c.execute("SELECT COUNT(*) FROM businesses WHERE active=1").fetchone()[0],"shipments":c.execute("SELECT COUNT(*) FROM shipments WHERE status='en tránsito'").fetchone()[0],"avg_price":round(c.execute("SELECT COALESCE(AVG(price),0) FROM markets").fetchone()[0])}
    c.close()
    return {"world":w,"population":pop,"nobles":nobles,"families":families,"avg_health":avg_health,"avg_wealth":avg_wealth,"kingdoms":ks,"parties":parties,"offices":offices,"events":events,"chronicles":chronicles,"people":ppl,"economy":economy}


@app.get("/api/people/{person_id}")
def get_person(person_id:int):
    catch_up(); c=db(); p=c.execute("SELECT * FROM people WHERE id=?",(person_id,)).fetchone()
    if not p: c.close(); raise HTTPException(404,"Habitante no encontrado")
    rel=[dict(x) for x in c.execute("SELECT r.*,p.name AS other_name,p.age AS other_age,p.alive AS other_alive FROM relationships r JOIN people p ON p.id=r.b_id WHERE r.a_id=? ORDER BY r.strength DESC LIMIT 30",(person_id,))]
    know=[dict(x) for x in c.execute("SELECT * FROM knowledge WHERE person_id=? ORDER BY id DESC LIMIT 20",(person_id,))]
    hist=[dict(x) for x in c.execute("SELECT * FROM events WHERE actors LIKE ? ORDER BY id DESC LIMIT 15",('%'+p["name"]+'%',))]
    c.close(); return {"person":dict(p),"relationships":rel,"knowledge":know,"history":hist}


class Advance(BaseModel): days:int=1
class Speed(BaseModel): speed:int
class Pause(BaseModel): paused:bool

@app.post("/api/advance")
def advance(a:Advance): tick(max(1,min(a.days,3650))); return get_world()
@app.post("/api/speed")
def speed(s:Speed):
    c=db(); c.execute("UPDATE world SET speed=? WHERE id=1",(max(1,min(s.speed,100)),)); c.commit(); c.close(); return get_world()
@app.post("/api/pause")
def pause(p:Pause):
    c=db(); c.execute("UPDATE world SET paused=? WHERE id=1",(1 if p.paused else 0,)); c.commit(); c.close(); return get_world()

@app.get("/api/layers")
def get_layers():
    catch_up(); c=db()
    regions=[dict(x) for x in c.execute("SELECT r.*,k.name kingdom FROM regions r JOIN kingdoms k ON k.id=r.kingdom_id ORDER BY r.id")]
    cities=[dict(x) for x in c.execute("SELECT c.*,r.name region,k.name kingdom FROM cities c JOIN regions r ON r.id=c.region_id JOIN kingdoms k ON k.id=c.kingdom_id ORDER BY c.id")]; districts=[dict(x) for x in c.execute("SELECT d.*,c.name city FROM districts d JOIN cities c ON c.id=d.city_id ORDER BY d.city_id,d.id")]
    properties=[dict(x) for x in c.execute("SELECT p.*,c.name city,d.name district,COALESCE(pe.name,'Sin propietario') owner FROM properties p JOIN cities c ON c.id=p.city_id JOIN districts d ON d.id=p.district_id LEFT JOIN people pe ON pe.id=p.owner_id ORDER BY p.value DESC LIMIT 80")]; resources=[dict(x) for x in c.execute("SELECT r.*,g.name region FROM resources r JOIN regions g ON g.id=r.region_id ORDER BY g.id")]; routes=[dict(x) for x in c.execute("SELECT r.*,a.name from_city,b.name to_city FROM routes r JOIN cities a ON a.id=r.from_city_id JOIN cities b ON b.id=r.to_city_id ORDER BY r.id")]; conflicts=[dict(x) for x in c.execute("SELECT * FROM conflicts ORDER BY id DESC LIMIT 30")]; markets=[dict(x) for x in c.execute("SELECT m.*,c.name city FROM markets m JOIN cities c ON c.id=m.city_id ORDER BY c.id,m.good")]; businesses=[dict(x) for x in c.execute("SELECT b.*,c.name city,COALESCE(p.name,'Sin dueño') owner FROM businesses b JOIN cities c ON c.id=b.city_id LEFT JOIN people p ON p.id=b.owner_id ORDER BY b.capital DESC LIMIT 80")]; shipments=[dict(x) for x in c.execute("SELECT s.*,a.name origin_name,b.name destination_name FROM shipments s JOIN cities a ON a.id=s.origin_city JOIN cities b ON b.id=s.destination_city ORDER BY s.id DESC LIMIT 40")]
    c.close(); return {"regions":regions,"cities":cities,"districts":districts,"properties":properties,"resources":resources,"routes":routes,"conflicts":conflicts,"markets":markets,"businesses":businesses,"shipments":shipments}

@app.get("/api/cities/{city_id}")
def get_city(city_id:int):
    catch_up(); c=db(); city=c.execute("SELECT c.*,r.name region,k.name kingdom FROM cities c JOIN regions r ON r.id=c.region_id JOIN kingdoms k ON k.id=c.kingdom_id WHERE c.id=?",(city_id,)).fetchone()
    if not city: c.close(); raise HTTPException(404,"Ciudad no encontrada")
    districts=[dict(x) for x in c.execute("SELECT * FROM districts WHERE city_id=? ORDER BY id",(city_id,))]; props=[dict(x) for x in c.execute("SELECT p.*,COALESCE(pe.name,'Sin propietario') owner FROM properties p LEFT JOIN people pe ON pe.id=p.owner_id WHERE p.city_id=? ORDER BY p.value DESC",(city_id,))]; people=[dict(x) for x in c.execute("SELECT id,name,age,job,wealth,status,trait FROM people WHERE alive=1 AND city_id=? ORDER BY RANDOM() LIMIT 30",(city_id,))]; c.close(); return {"city":dict(city),"districts":districts,"properties":props,"people":people}

class DivineAction(BaseModel):
    action:str
    target_type:str="world"
    target_id:int=0
    parameters:dict={}
    description:str=""

class DivineSchedule(BaseModel):
    execute_in_days:int=1
    action:str
    target_type:str="world"
    target_id:int=0
    parameters:dict={}
    description:str=""

@app.get("/api/divine")
def divine_dashboard():
    catch_up(); c=db(); w=c.execute("SELECT * FROM world WHERE id=1").fetchone(); wd=world_day(w)
    interventions=[dict(x) for x in c.execute("SELECT * FROM divine_interventions ORDER BY id DESC LIMIT 50")]
    schedules=[dict(x) for x in c.execute("SELECT * FROM divine_schedules WHERE active=1 ORDER BY execute_day,id LIMIT 50")]
    letters=[dict(x) for x in c.execute("SELECT l.*,p.name recipient_name FROM letters l JOIN people p ON p.id=l.recipient_id ORDER BY l.id DESC LIMIT 50")]
    weather=[dict(x) for x in c.execute("SELECT * FROM divine_weather WHERE active=1 ORDER BY end_day")]
    c.close(); return {"world_day":wd,"interventions":interventions,"schedules":schedules,"letters":letters,"weather":weather}

@app.post("/api/divine/intervene")
def divine_intervene(a:DivineAction):
    # Manual divine actions must share the same process lock as the autonomous
    # simulation. Otherwise a background tick can hold a SQLite write transaction
    # while this request tries to write, producing "database is locked".
    with SIM_LOCK:
        _catch_up_unlocked()
        c=db(); w=c.execute("SELECT * FROM world WHERE id=1").fetchone(); wd=world_day(w)
        try:
            consequence=execute_divine(c,wd,a.action,a.target_type,a.target_id,a.parameters,a.description)
            c.commit()
            return {"ok":True,"consequence":consequence,"world_day":wd}
        finally:
            c.close()

@app.post("/api/divine/schedule")
def divine_schedule(a:DivineSchedule):
    with SIM_LOCK:
        _catch_up_unlocked()
        c=db(); w=c.execute("SELECT * FROM world WHERE id=1").fetchone(); wd=world_day(w); execute_day=wd+max(1,min(int(a.execute_in_days),365000))
        try:
            c.execute("INSERT INTO divine_schedules(execute_day,action,target_type,target_id,parameters,description,active) VALUES(?,?,?,?,?,?,1)",(execute_day,a.action,a.target_type,a.target_id,json.dumps(a.parameters,ensure_ascii=False),a.description))
            divine_log(c,wd,"schedule:"+a.action,a.target_type,a.target_id,a.parameters,f"Intervención programada para el día {execute_day}.","La intervención aún no ha ocurrido.")
            c.commit()
            return {"ok":True,"execute_day":execute_day}
        finally:
            c.close()

@app.delete("/api/divine/schedule/{schedule_id}")
def cancel_divine_schedule(schedule_id:int):
    c=db(); c.execute("UPDATE divine_schedules SET active=0 WHERE id=?",(schedule_id,)); c.commit(); c.close(); return {"ok":True}

@app.post("/api/divine/wealth/{kingdom_id}")
def divine_wealth(kingdom_id:int):
    c=db(); c.execute("UPDATE kingdoms SET gold=gold+10000 WHERE id=?",(kingdom_id,)); w=c.execute("SELECT year,day FROM world WHERE id=1").fetchone(); add_event(c,world_day(w),"Intervención divina","Una riqueza inesperada apareció en las arcas del reino. Nadie conoce su origen.",4,cause="causa desconocida",location=kingdom_name(c,kingdom_id)); c.commit(); c.close(); return get_world()
