import sqlite3
import logging
import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CATALOGO] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# --- Config ---
DB_PATH = os.getenv("CATALOGO_DB_PATH", "./data/catalogo.db")

app = FastAPI(title="Servicio Catalogo")

# --- Pydantic Models ---
class VideojuegoCreate(BaseModel):
    titulo: str
    plataforma: str
    genero: str
    precio: float
    clasificacion: str
    formato: str

class VideojuegoUpdate(BaseModel):
    titulo: Optional[str] = None
    plataforma: Optional[str] = None
    genero: Optional[str] = None
    precio: Optional[float] = None
    clasificacion: Optional[str] = None
    formato: Optional[str] = None

# --- Database ---
@contextmanager
def get_db():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

SEED_DATA = [
    ("vj-001", "The Legend of Zelda: Tears of the Kingdom", "Nintendo Switch", "Aventura", 59.99, "E10+", "fisico"),
    ("vj-002", "God of War: Ragnarok", "PS5", "Accion", 69.99, "M", "fisico"),
    ("vj-003", "Halo Infinite", "Xbox Series X", "Shooter", 59.99, "T", "digital"),
    ("vj-004", "Mario Kart 8 Deluxe", "Nintendo Switch", "Carreras", 49.99, "E", "fisico"),
    ("vj-005", "Elden Ring", "PS5", "RPG", 59.99, "M", "digital"),
    ("vj-006", "FIFA 25", "PS5", "Deportes", 69.99, "E", "fisico"),
    ("vj-007", "Minecraft", "PC", "Sandbox", 29.99, "E10+", "digital"),
    ("vj-008", "Red Dead Redemption 2", "Xbox Series X", "Aventura", 39.99, "M", "fisico"),
]

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS videojuegos (
                id TEXT PRIMARY KEY,
                titulo TEXT NOT NULL,
                plataforma TEXT NOT NULL,
                genero TEXT NOT NULL,
                precio REAL NOT NULL,
                clasificacion TEXT NOT NULL,
                formato TEXT NOT NULL,
                fecha_registro TEXT NOT NULL
            )
        """)
        row = conn.execute("SELECT COUNT(*) FROM videojuegos").fetchone()
        if row[0] == 0:
            fecha = datetime.utcnow().isoformat()
            conn.executemany(
                "INSERT INTO videojuegos VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [(*item, fecha) for item in SEED_DATA]
            )
            logger.info("Datos semilla insertados: %d videojuegos", len(SEED_DATA))

@app.on_event("startup")
def startup():
    logger.info("Iniciando Servicio Catalogo en puerto 8001")
    init_db()
    logger.info("Base de datos lista: %s", DB_PATH)

# --- Endpoints ---
@app.get("/health")
def health():
    try:
        with get_db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM videojuegos").fetchone()[0]
        return {"status": "ok", "servicio": "catalogo", "puerto": 8001, "videojuegos": count}
    except Exception as e:
        logger.error("Health check fallido: %s", e)
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

@app.get("/api/videojuegos")
def listar_videojuegos(
    plataforma: Optional[str] = Query(None),
    genero: Optional[str] = Query(None),
    formato: Optional[str] = Query(None),
):
    query = "SELECT * FROM videojuegos WHERE 1=1"
    params = []
    if plataforma:
        query += " AND plataforma = ?"
        params.append(plataforma)
    if genero:
        query += " AND genero = ?"
        params.append(genero)
    if formato:
        query += " AND formato = ?"
        params.append(formato)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    logger.info("Consulta de videojuegos: %d resultados", len(rows))
    return [dict(r) for r in rows]

@app.get("/api/videojuegos/{videojuego_id}")
def obtener_videojuego(videojuego_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM videojuegos WHERE id = ?", (videojuego_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Videojuego no encontrado")
    return dict(row)

@app.post("/api/videojuegos", status_code=201)
def crear_videojuego(data: VideojuegoCreate):
    nuevo_id = "vj-" + str(uuid.uuid4())[:8]
    fecha = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO videojuegos VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (nuevo_id, data.titulo, data.plataforma, data.genero,
             data.precio, data.clasificacion, data.formato, fecha)
        )
    logger.info("Videojuego creado: %s - %s", nuevo_id, data.titulo)
    return {"id": nuevo_id, "titulo": data.titulo, "fecha_registro": fecha}

@app.put("/api/videojuegos/{videojuego_id}")
def actualizar_videojuego(videojuego_id: str, data: VideojuegoUpdate):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM videojuegos WHERE id = ?", (videojuego_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Videojuego no encontrado")
        actual = dict(row)
        campos = {k: v for k, v in data.model_dump().items() if v is not None}
        if not campos:
            return actual
        sets = ", ".join(f"{k} = ?" for k in campos)
        valores = list(campos.values()) + [videojuego_id]
        conn.execute(f"UPDATE videojuegos SET {sets} WHERE id = ?", valores)
        updated = conn.execute("SELECT * FROM videojuegos WHERE id = ?", (videojuego_id,)).fetchone()
    logger.info("Videojuego actualizado: %s", videojuego_id)
    return dict(updated)

@app.delete("/api/videojuegos/{videojuego_id}")
def eliminar_videojuego(videojuego_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM videojuegos WHERE id = ?", (videojuego_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Videojuego no encontrado")
        conn.execute("DELETE FROM videojuegos WHERE id = ?", (videojuego_id,))
    logger.info("Videojuego eliminado: %s", videojuego_id)
    return {"mensaje": "Videojuego eliminado", "id": videojuego_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
