from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3, random, os, time, asyncio, threading

SIM_LOCK = threading.Lock()

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "world.db")
app = FastAPI(title="Reino Vivo v0.6")

MALE = ["Aren","Bran","Corvin","Edric","Garen","Hugo","Ivar","Jon","Kael","Lucan","Marek","Nolan","Oren","Perrin","Ronan","Tomas"]
FEMALE = ["Aelia","Brina","Celia","Fiona","Gwen","Isla","Lena","Mara","Neria","Olia","Rhea","Selene","Talia","Una","Vera","Yara"]
JOBS = ["agricultor","artesano","mercader","pescador","minero","soldado","guardia","constructor","curandero","escriba","panadero","carpintero","tejedor","cocinero","marinero"]
GOALS = ["familia","riqueza","prestigio","proteger su hogar","aprender","viajar","tener hijos"]
FEARS = ["pobreza","guerra","enfermedad","perder un familiar","deudas","soledad"]
BELIEFS = ["tradición","honor","familia","fortuna","naturaleza","leyes"]

def db():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    return c

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
    CREATE TABLE IF NOT EXISTS relationships(
        id INTEGER PRIMARY KEY AUTOINCREMENT, a_id INTEGER, b_id INTEGER, kind TEXT, strength INTEGER,
        UNIQUE(a_id,b_id,kind)
    );
    CREATE TABLE IF NOT EXISTS knowledge(
        id INTEGER PRIMARY KEY AUTOINCREMENT, person_id INTEGER, subject TEXT, content TEXT,
        certainty INTEGER, source TEXT
    );
    CREATE TABLE IF NOT EXISTS parties(
        id INTEGER PRIMARY KEY AUTOINCREMENT, kingdom_id INTEGER, name TEXT, ideology TEXT, influence INTEGER, support INTEGER
    );
    CREATE TABLE IF NOT EXISTS party_members(
        id INTEGER PRIMARY KEY AUTOINCREMENT, party_id INTEGER, person_id INTEGER, role TEXT, loyalty INTEGER, UNIQUE(party_id,person_id)
    );
    CREATE TABLE IF NOT EXISTS offices(
        id INTEGER PRIMARY KEY AUTOINCREMENT, kingdom_id INTEGER, title TEXT, person_id INTEGER, power INTEGER
    );
    CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, world_day INTEGER, title TEXT, description TEXT, importance INTEGER
    );
    """)
    if c.execute("SELECT COUNT(*) FROM world").fetchone()[0] == 0:
        c.execute("INSERT INTO world VALUES(1,247,1,1,0,?)", (time.time(),))
        c.execute("INSERT INTO kingdoms VALUES(1,'Aurelia','Elira I','Reina',100000,82)")
        c.execute("INSERT INTO kingdoms VALUES(2,'Valdoria','Darian II','Rey',100000,78)")
        random.seed(247)
        pid = 1
        for k in (1, 2):
            for i in range(1000):
                sex = "M" if i < 500 else "F"
                names = MALE if sex == "M" else FEMALE
                age = random.randint(1, 75)
                job = random.choice(JOBS) if age >= 15 else "estudiante"
                wealth = random.randint(10, 500) if age >= 15 else random.randint(1, 30)
                status = "noble" if i < 20 else ("real" if i < 25 else "común")
                c.execute("""INSERT INTO people
                (id,name,sex,age,kingdom_id,job,wealth,status,alive,education,reputation,goal,fear,belief,mother_id,father_id,partner_id)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (pid,f"{random.choice(names)} {pid}",sex,age,k,job,wealth,status,1,
                 random.randint(0,100),random.randint(0,100),random.choice(GOALS),
                 random.choice(FEARS),random.choice(BELIEFS),None,None,None))
                pid += 1

        # Initial family links: adults of opposite sex in small households.
        for k in (1, 2):
            males = [r["id"] for r in c.execute("SELECT id FROM people WHERE kingdom_id=? AND sex='M' AND age BETWEEN 20 AND 55", (k,)).fetchall()]
            females = [r["id"] for r in c.execute("SELECT id FROM people WHERE kingdom_id=? AND sex='F' AND age BETWEEN 20 AND 50", (k,)).fetchall()]
            random.shuffle(males); random.shuffle(females)
            for a,b in zip(males[:140], females[:140]):
                if random.random() < 0.55:
                    c.execute("UPDATE people SET partner_id=? WHERE id=?", (b,a))
                    c.execute("UPDATE people SET partner_id=? WHERE id=?", (a,b))
                    c.execute("INSERT OR IGNORE INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?)", (a,b,"pareja",random.randint(45,90)))
                    c.execute("INSERT OR IGNORE INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?)", (b,a,"pareja",random.randint(45,90)))

        # Seed individual knowledge: not everyone knows everything.
        for r in c.execute("SELECT id,name,kingdom_id FROM people WHERE alive=1 ORDER BY id LIMIT 120").fetchall():
            c.execute("INSERT INTO knowledge(person_id,subject,content,certainty,source) VALUES(?,?,?,?,?)",
                      (r["id"],"mundo","Vive en " + ("Aurelia" if r["kingdom_id"]==1 else "Valdoria"),100,"experiencia"))
        # Initial political parties and noble offices. Parties are autonomous factions, not fixed good/bad labels.
        party_defs = {
            1: [("Tradición Real","tradicionalista"),("Reformistas de la Corona","reformista"),("Liga Mercantil","mercantil")],
            2: [("Orden del Reino","tradicionalista"),("Consejo de Renovación","reformista"),("Alianza de Comerciantes","mercantil")]
        }
        for k, defs in party_defs.items():
            nobles=[r["id"] for r in c.execute("SELECT id FROM people WHERE kingdom_id=? AND status='noble' AND alive=1",(k,)).fetchall()]
            random.shuffle(nobles)
            for name, ideology in defs:
                c.execute("INSERT INTO parties(kingdom_id,name,ideology,influence,support) VALUES(?,?,?,?,?)",(k,name,ideology,random.randint(20,45),random.randint(15,40)))
                party_id=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                take=random.randint(4,9)
                for nid in nobles[:take]:
                    c.execute("INSERT OR IGNORE INTO party_members(party_id,person_id,role,loyalty) VALUES(?,?,?,?)",(party_id,nid,"miembro",random.randint(45,90)))
                nobles=nobles[take:] if len(nobles)>take else nobles
        for k in (1,2):
            nobles=[r["id"] for r in c.execute("SELECT id FROM people WHERE kingdom_id=? AND status='noble' AND alive=1 ORDER BY RANDOM()",(k,)).fetchall()]
            titles=[("Consejero Real",40),("Maestre de Finanzas",35),("Maestre de Leyes",30),("Comandante de la Guardia",35)]
            for (title,power),nid in zip(titles,nobles):
                c.execute("INSERT INTO offices(kingdom_id,title,person_id,power) VALUES(?,?,?,?)",(k,title,nid,power))
        c.execute("INSERT INTO events(world_day,title,description,importance) VALUES(1,?,?,?)",
                  ("Nacimiento del Reino Vivo","Dos reinos comienzan una nueva era con 2.000 habitantes. Algunas familias ya tienen vínculos entre sí y los nobles empiezan a organizarse en facciones políticas.",5))
    c.commit(); c.close()

def world_day(w):
    return (w["year"] - 247) * 365 + w["day"]

def add_event(c, wd, title, desc, importance):
    c.execute("INSERT INTO events(world_day,title,description,importance) VALUES(?,?,?,?)",
              (wd,title,desc,importance))

def political_tick(c, wd):
    # Parties gain/lose support from autonomous social and economic conditions.
    for party in c.execute("SELECT * FROM parties").fetchall():
        change=random.randint(-2,3)
        if party["ideology"]=="mercantil" and random.random()<0.35: change+=1
        if party["ideology"]=="reformista" and random.random()<0.20: change+=1
        support=max(0,min(100,party["support"]+change))
        influence=max(5,min(100,party["influence"]+random.randint(-2,2)))
        c.execute("UPDATE parties SET support=?,influence=? WHERE id=?",(support,influence,party["id"]))
    if random.random()<0.12:
        p=c.execute("SELECT p.*,k.name kingdom FROM parties p JOIN kingdoms k ON k.id=p.kingdom_id ORDER BY RANDOM() LIMIT 1").fetchone()
        if p:
            titles=["Debate entre nobles","Disputa por impuestos","Coalición en formación","Presión de una facción","Negociación del consejo"]
            desc=f"En {p['kingdom']}, la facción {p['name']} ganó protagonismo. Sus miembros negocian, discrepan y buscan apoyo entre otros nobles."
            add_event(c,wd,random.choice(titles),desc,random.randint(2,4))
    # Noble loyalty drifts; a very low loyalty can move a noble to another faction.
    for m in c.execute("SELECT * FROM party_members").fetchall():
        loyalty=max(10,min(100,m["loyalty"]+random.randint(-3,3)))
        c.execute("UPDATE party_members SET loyalty=? WHERE id=?",(loyalty,m["id"]))
        if loyalty<25 and random.random()<0.08:
            c.execute("DELETE FROM party_members WHERE id=?",(m["id"],))
            add_event(c,wd,"Un noble cambia de bando","Un miembro de la nobleza abandonó una facción política y comenzó a buscar nuevos aliados.",3)

def _tick_unlocked(days=1):
    c = db()
    for _ in range(days):
        w = c.execute("SELECT * FROM world WHERE id=1").fetchone()
        wd = world_day(w) + 1
        day, year = w["day"] + 1, w["year"]
        if day > 365:
            day, year = 1, year + 1
            c.execute("UPDATE people SET age=age+1 WHERE alive=1")

        people = c.execute("SELECT id,age,wealth,job,kingdom_id FROM people WHERE alive=1").fetchall()
        for p in people:
            wealth = max(0, p["wealth"] + random.randint(-3,5))
            if p["job"] == "agricultor" and random.random() < .08:
                wealth += random.randint(5,25)
            if p["job"] == "mercader" and random.random() < .08:
                wealth += random.randint(5,30)
            c.execute("UPDATE people SET wealth=? WHERE id=?", (wealth,p["id"]))
            age = p["age"]
            chance = .00015 if age < 50 else (.0015 if age < 70 else .008)
            if random.random() < chance:
                c.execute("UPDATE people SET alive=0 WHERE id=?", (p["id"],))
                if p["age"] >= 60:
                    add_event(c,wd,"Una muerte en la comunidad",
                              "Una persona de edad avanzada ha muerto; sus relaciones y bienes quedan en manos de su entorno.",2)

        # Small autonomous family formation.
        for k in (1,2):
            candidates = c.execute("""SELECT id FROM people
                WHERE alive=1 AND kingdom_id=? AND partner_id IS NULL AND age BETWEEN 20 AND 38""",(k,)).fetchall()
            ids = [x["id"] for x in candidates]
            random.shuffle(ids)
            if len(ids) >= 2 and random.random() < .10:
                a,b = ids[0], ids[1]
                sa,sb = c.execute("SELECT sex FROM people WHERE id=?", (a,)).fetchone()[0], c.execute("SELECT sex FROM people WHERE id=?", (b,)).fetchone()[0]
                if sa != sb:
                    c.execute("UPDATE people SET partner_id=? WHERE id=?", (b,a))
                    c.execute("UPDATE people SET partner_id=? WHERE id=?", (a,b))
                    c.execute("INSERT OR IGNORE INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?)",(a,b,"pareja",50))
                    c.execute("INSERT OR IGNORE INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?)",(b,a,"pareja",50))

        # Births only from existing couples; child stores real parents.
        for k in (1,2):
            couples = c.execute("""SELECT p.id AS mother, p.partner_id AS father
                FROM people p JOIN people f ON f.id=p.partner_id
                WHERE p.alive=1 AND f.alive=1 AND p.kingdom_id=? AND p.sex='F'
                AND p.age BETWEEN 18 AND 40 AND f.age BETWEEN 18 AND 50""",(k,)).fetchall()
            if couples and random.random() < min(.35, len(couples)/500):
                couple = random.choice(couples)
                sex = random.choice(["M","F"])
                names = MALE if sex=="M" else FEMALE
                name = f"{random.choice(names)} {int(time.time()*1000000)%1000000}"
                c.execute("""INSERT INTO people
                (name,sex,age,kingdom_id,job,wealth,status,alive,education,reputation,goal,fear,belief,mother_id,father_id,partner_id)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name,sex,0,k,"niño",random.randint(1,10),"común",1,0,20,"familia","enfermedad","familia",
                 couple["mother"],couple["father"],None))
                child = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                c.execute("INSERT INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?)",(couple["mother"],child,"madre",90))
                c.execute("INSERT INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?)",(couple["father"],child,"padre",90))
                c.execute("INSERT INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?)",(child,couple["mother"],"hijo",90))
                c.execute("INSERT INTO relationships(a_id,b_id,kind,strength) VALUES(?,?,?,?)",(child,couple["father"],"hijo",90))
                add_event(c,wd,"Nace un nuevo habitante",
                          "Una familia recibe a un nuevo hijo. El nacimiento cambia la vida y las obligaciones de quienes lo rodean.",2)

        if random.random() < .18:
            choices = [
                ("Mercado en movimiento","Los precios y fortunas de algunos comerciantes cambiaron."),
                ("Rumores entre familias","Circulan versiones distintas sobre un conflicto menor."),
                ("Cosecha desigual","Algunas comunidades tuvieron una temporada mejor que otras."),
                ("Viajeros en los caminos","Mercaderes y viajeros llevan noticias entre los reinos.")
            ]
            t,d = random.choice(choices)
            add_event(c,wd,t,d,random.randint(1,3))

        c.execute("UPDATE world SET year=?,day=?,last_real=? WHERE id=1",(year,day,time.time()))
    c.commit(); c.close()

def tick(days=1):
    with SIM_LOCK:
        _tick_unlocked(max(1, int(days)))

def catch_up():
    with SIM_LOCK:
        c = db()
        w = c.execute("SELECT * FROM world WHERE id=1").fetchone()
        c.close()
        missed = min(int(max(0,time.time()-w["last_real"])/86400*3),90)
        if missed and not w["paused"]:
            _tick_unlocked(missed)

async def background_loop():
    while True:
        try:
            c=db(); w=c.execute("SELECT * FROM world WHERE id=1").fetchone(); c.close()
            if not w["paused"]:
                tick(max(1,w["speed"]))
        except Exception:
            pass
        await asyncio.sleep(3600)

@app.on_event("startup")
async def startup():
    init()
    catch_up()
    asyncio.create_task(background_loop())

@app.get("/")
def home():
    return FileResponse(os.path.join(BASE,"index.html"))

@app.get("/api/world")
def get_world():
    catch_up()
    c=db()
    w=dict(c.execute("SELECT * FROM world WHERE id=1").fetchone())
    ks=[dict(x) for x in c.execute("SELECT * FROM kingdoms ORDER BY id")]
    pop=c.execute("SELECT COUNT(*) FROM people WHERE alive=1").fetchone()[0]
    nobles=c.execute("SELECT COUNT(*) FROM people WHERE alive=1 AND status='noble'").fetchone()[0]
    families=c.execute("SELECT COUNT(*) FROM people WHERE alive=1 AND partner_id IS NOT NULL").fetchone()[0]//2
    ev=[dict(x) for x in c.execute("SELECT * FROM events ORDER BY id DESC LIMIT 12")]
    parties=[dict(x) for x in c.execute("SELECT p.*,k.name AS kingdom FROM parties p JOIN kingdoms k ON k.id=p.kingdom_id ORDER BY k.id,p.influence DESC")]
    offices=[dict(x) for x in c.execute("SELECT o.*,p.name AS person_name,k.name AS kingdom FROM offices o JOIN people p ON p.id=o.person_id JOIN kingdoms k ON k.id=o.kingdom_id ORDER BY k.id,o.power DESC")]
    ppl=[dict(x) for x in c.execute("""SELECT id,name,age,job,wealth,status,kingdom_id,goal,reputation,
        mother_id,father_id,partner_id FROM people WHERE alive=1 ORDER BY RANDOM() LIMIT 12""")]
    c.close()
    return {"world":w,"population":pop,"nobles":nobles,"families":families,"kingdoms":ks,"parties":parties,"offices":offices,"events":ev,"people":ppl}

class Advance(BaseModel):
    days:int=1
class Speed(BaseModel):
    speed:int
class Pause(BaseModel):
    paused:bool

@app.post("/api/advance")
def advance(a:Advance):
    tick(max(1,min(a.days,3650)))
    return get_world()

@app.post("/api/speed")
def speed(s:Speed):
    c=db(); c.execute("UPDATE world SET speed=? WHERE id=1",(max(1,min(s.speed,100)),)); c.commit(); c.close()
    return get_world()

@app.post("/api/pause")
def pause(p:Pause):
    c=db(); c.execute("UPDATE world SET paused=? WHERE id=1",(1 if p.paused else 0,)); c.commit(); c.close()
    return get_world()

@app.post("/api/divine/wealth/{kingdom_id}")
def divine_wealth(kingdom_id:int):
    c=db()
    c.execute("UPDATE kingdoms SET gold=gold+10000 WHERE id=?",(kingdom_id,))
    w=c.execute("SELECT year,day FROM world WHERE id=1").fetchone()
    add_event(c,world_day(w),"Intervención divina","Una riqueza inesperada apareció en las arcas del reino.",4)
    c.commit(); c.close()
    return get_world()
