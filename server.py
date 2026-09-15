from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3, random, os
from datetime import datetime

BASE=os.path.dirname(os.path.abspath(__file__))
DB=os.path.join(BASE,"world.db")
app=FastAPI(title="Reino Vivo v0.2")

def db():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c

def init():
    c=db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS world(
      id INTEGER PRIMARY KEY CHECK(id=1),
      year INTEGER NOT NULL,
      day INTEGER NOT NULL,
      paused INTEGER NOT NULL DEFAULT 0,
      speed INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS kingdoms(
      id INTEGER PRIMARY KEY,
      name TEXT, ruler TEXT, ruler_title TEXT, population INTEGER,
      gold REAL, stability REAL
    );
    CREATE TABLE IF NOT EXISTS cities(
      id INTEGER PRIMARY KEY, kingdom_id INTEGER, name TEXT, population INTEGER
    );
    CREATE TABLE IF NOT EXISTS people(
      id INTEGER PRIMARY KEY, kingdom_id INTEGER, name TEXT, sex TEXT,
      age INTEGER, job TEXT, wealth REAL, status TEXT, alive INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY AUTOINCREMENT, world_day INTEGER,
      title TEXT, description TEXT, importance INTEGER
    );
    """)
    if c.execute("SELECT COUNT(*) FROM world").fetchone()[0]==0:
        c.execute("INSERT INTO world VALUES(1,247,1,0,1)")
        kingdoms=[
            (1,"Aurelia","Elira I","Reina",1000,100000,82),
            (2,"Valdoria","Darian II","Rey",1000,100000,79)
        ]
        c.executemany("INSERT INTO kingdoms VALUES(?,?,?,?,?,?,?)",kingdoms)
        cities=[(1,1,"Puerto Alba",360),(2,1,"Río Claro",330),(3,1,"Bosque Alto",310),
                (4,2,"Corona",380),(5,2,"Monteluz",320),(6,2,"Bahía Gris",300)]
        c.executemany("INSERT INTO cities VALUES(?,?,?,?)",cities)
        male_jobs=["Agricultor","Herrero","Soldado","Mercader","Carpintero","Pescador"]
        female_jobs=["Agricultora","Tejedora","Comerciante","Curandera","Panadera","Escriba"]
        names_m=["Aldric","Bran","Cedric","Dorian","Edric","Gareth","Hugo","Ivar","Jon","Lucan","Marek","Oren"]
        names_f=["Aelia","Brina","Celia","Dara","Elin","Fara","Lyra","Mira","Nadia","Rhea","Sera","Talia"]
        rows=[]
        pid=1
        for k in (1,2):
            for i in range(500):
                age=random.choices(range(1,81),weights=[1 if a<15 else 2 if a<60 else 1 for a in range(1,81)])[0]
                rows.append((pid,k,random.choice(names_m)+f" {pid}", "M",age,random.choice(male_jobs),round(random.uniform(10,2500),2),"Común"))
                pid+=1
            for i in range(500):
                age=random.choices(range(1,81),weights=[1 if a<15 else 2 if a<60 else 1 for a in range(1,81)])[0]
                rows.append((pid,k,random.choice(names_f)+f" {pid}", "F",age,random.choice(female_jobs),round(random.uniform(10,2500),2),"Común"))
                pid+=1
        c.executemany("INSERT INTO people(id,kingdom_id,name,sex,age,job,wealth,status) VALUES(?,?,?,?,?,?,?,?)",rows)
        c.execute("INSERT INTO events(world_day,title,description,importance) VALUES(1,'El mundo despierta','Los dos reinos continúan su historia en el año 247.',3)")
    c.commit(); c.close()

def tick(days=1):
    c=db()
    w=c.execute("SELECT * FROM world WHERE id=1").fetchone()
    if w["paused"]:
        c.close(); return
    for _ in range(days):
        d=w["day"]+1; y=w["year"]
        if d>365: d=1; y+=1
        c.execute("UPDATE people SET age=age+1 WHERE alive=1 AND (age*365 + ?) % 365 = 0",(d,))
        # lightweight emergent events
        if random.random()<0.22:
            k=random.choice(c.execute("SELECT * FROM kingdoms").fetchall())
            templates=[
                ("Mercado en movimiento",f"Los precios en {k['name']} cambiaron por variaciones en la oferta y la demanda."),
                ("Rumores en la corte",f"Circulan rumores entre nobles de {k['name']}. Su veracidad aún no está confirmada."),
                ("Problemas de cosecha",f"Algunas comunidades de {k['name']} reportan una cosecha menor a la esperada."),
                ("Viajeros",f"Mercaderes y viajeros llegaron a distintas ciudades de {k['name']}.")
            ]
            t=random.choice(templates)
            c.execute("INSERT INTO events(world_day,title,description,importance) VALUES(?,?,?,?)",(d,t[0],t[1],random.randint(1,3)))
        c.execute("UPDATE world SET day=?, year=? WHERE id=1",(d,y))
        w=c.execute("SELECT * FROM world WHERE id=1").fetchone()
    c.commit(); c.close()

class Advance(BaseModel):
    days:int=1

class Speed(BaseModel):
    speed:int

class Pause(BaseModel):
    paused:bool

@app.get("/")
def home(): return FileResponse(os.path.join(BASE,"web","index.html"))

@app.get("/api/world")
def world():
    c=db()
    w=dict(c.execute("SELECT * FROM world WHERE id=1").fetchone())
    ks=[dict(x) for x in c.execute("SELECT * FROM kingdoms").fetchall()]
    ev=[dict(x) for x in c.execute("SELECT * FROM events ORDER BY id DESC LIMIT 20").fetchall()]
    people=c.execute("SELECT COUNT(*) FROM people WHERE alive=1").fetchone()[0]
    c.close()
    return {"world":w,"kingdoms":ks,"population":people,"events":ev}

@app.post("/api/advance")
def advance(a:Advance):
    tick(max(1,min(a.days,3650)))
    return world()

@app.post("/api/speed")
def speed(s:Speed):
    c=db(); c.execute("UPDATE world SET speed=? WHERE id=1",(max(1,min(s.speed,100)),)); c.commit(); c.close()
    return world()

@app.post("/api/pause")
def pause(p:Pause):
    c=db(); c.execute("UPDATE world SET paused=? WHERE id=1",(1 if p.paused else 0,)); c.commit(); c.close()
    return world()

@app.post("/api/divine/wealth/{kingdom_id}")
def divine_wealth(kingdom_id:int):
    c=db(); c.execute("UPDATE kingdoms SET gold=gold+10000 WHERE id=?",(kingdom_id,))
    c.execute("INSERT INTO events(world_day,title,description,importance) SELECT day,'Intervención del Creador','Una cantidad extraordinaria de riqueza apareció en las arcas del reino.',4 FROM world WHERE id=1")
    c.commit(); c.close(); return world()

init()
