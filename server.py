from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3, random, os, time, asyncio, threading, math

SIM_LOCK = threading.Lock()
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "world.db")
app = FastAPI(title="Reino Vivo v0.7")

MALE = ["Aren","Bran","Corvin","Edric","Garen","Hugo","Ivar","Jon","Kael","Lucan","Marek","Nolan","Oren","Perrin","Ronan","Tomas","Dario","León","Mateo","Silas"]
FEMALE = ["Aelia","Brina","Celia","Fiona","Gwen","Isla","Lena","Mara","Neria","Olia","Rhea","Selene","Talia","Una","Vera","Yara","Elia","Nora","Livia","Mira"]
SURNAMES = ["Valen","Ríos","Montes","Alvar","Seren","Dorn","Vega","Luar","Cantos","Ravel","Neris","Ferrer","Solano","Mares","Tovar"]
JOBS = ["agricultor","artesano","mercader","pescador","minero","soldado","guardia","constructor","curandero","escriba","panadero","carpintero","tejedor","cocinero","marinero"]
GOALS = ["fundar una familia","acumular riqueza","ganar prestigio","proteger a su familia","aprender un oficio","viajar","tener hijos","conseguir una propiedad","mejorar su posición social"]
FEARS = ["pobreza","guerra","enfermedad","perder a un familiar","deudas","soledad","deshonra","perder su hogar"]
BELIEFS = ["tradición","honor","familia","fortuna","naturaleza","ley","comunidad"]
TRAITS = ["prudente","ambicioso","generoso","desconfiado","sociable","reservado","valiente","temeroso","honesto","calculador","religioso","curioso"]


def db():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
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
    c.commit(); c.close()


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


def world_day(w): return (w["year"]-247)*365+w["day"]


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


def _tick_unlocked(days=1):
    c=db()
    for _ in range(days):
        w=c.execute("SELECT * FROM world WHERE id=1").fetchone()
        wd=world_day(w)+1; day=w["day"]+1; year=w["year"]
        if day>365:
            day=1; year+=1
            c.execute("UPDATE people SET age=age+1 WHERE alive=1")
            add_event(c,wd,"Comienza un nuevo año",f"El año {year} comienza en Aurelia y Valdoria. Las personas continúan sus vidas mientras cambian lentamente las relaciones, fortunas y objetivos.",4,cause="paso del tiempo",location="Aurelia y Valdoria")
        needs_and_daily_economy(c,wd)
        relationship_tick(c,wd)
        birth_tick(c,wd)
        death_tick(c,wd)
        if wd%7==0: political_tick(c,wd)
        social_events(c,wd)
        c.execute("UPDATE world SET year=?,day=?,last_real=? WHERE id=1",(year,day,time.time()))
    c.commit(); c.close()


def tick(days=1):
    with SIM_LOCK: _tick_unlocked(max(1,int(days)))


def catch_up():
    with SIM_LOCK:
        c=db(); w=c.execute("SELECT * FROM world WHERE id=1").fetchone(); c.close()
        missed=min(int(max(0,time.time()-w["last_real"])/86400*3),90)
        if missed and not w["paused"]: _tick_unlocked(missed)


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
    parties=[dict(x) for x in c.execute("SELECT p.*,k.name AS kingdom FROM parties p JOIN kingdoms k ON k.id=p.kingdom_id ORDER BY k.id,p.influence DESC")]
    offices=[dict(x) for x in c.execute("SELECT o.*,p.name AS person_name,k.name AS kingdom FROM offices o JOIN people p ON p.id=o.person_id JOIN kingdoms k ON k.id=o.kingdom_id ORDER BY k.id,o.power DESC")]
    ppl=[dict(x) for x in c.execute("SELECT id,name,age,job,wealth,status,kingdom_id,goal,reputation,hunger,energy,social,health,morale,trait,secondary_trait,last_action,mother_id,father_id,partner_id FROM people WHERE alive=1 ORDER BY RANDOM() LIMIT 16")]
    c.close()
    return {"world":w,"population":pop,"nobles":nobles,"families":families,"avg_health":avg_health,"avg_wealth":avg_wealth,"kingdoms":ks,"parties":parties,"offices":offices,"events":events,"people":ppl}


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

@app.post("/api/divine/wealth/{kingdom_id}")
def divine_wealth(kingdom_id:int):
    c=db(); c.execute("UPDATE kingdoms SET gold=gold+10000 WHERE id=?",(kingdom_id,)); w=c.execute("SELECT year,day FROM world WHERE id=1").fetchone(); add_event(c,world_day(w),"Intervención divina","Una riqueza inesperada apareció en las arcas del reino. Nadie conoce su origen.",4,cause="causa desconocida",location=kingdom_name(c,kingdom_id)); c.commit(); c.close(); return get_world()
