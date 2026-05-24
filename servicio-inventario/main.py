import sqlite3
import logging
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [INVENTARIO] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# --- Config ---
DB_PATH = os.getenv("INVENTARIO_DB_PATH", "./data/inventario.db")

app = FastAPI(title="Servicio Inventario")

# --- Pydantic Models ---
class StockCreate(BaseModel):
    videojuego_id: str
    sede: str
    cantidad: int
    canal: str

class StockResponse(BaseModel):
    id: str
    videojuego_id: str
    sede: str
    cantidad: int
    canal: str
    ultima_actualizacion: str

class StockUpdate(BaseModel):
    cantidad: int = Field(..., ge=0)

class ReservaRequest(BaseModel):
    videojuego_id: str
    sede: str
    cantidad: int = Field(..., gt=0)

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
    ("inv-001", "vj-001", "tienda-principal", 15,  "fisico"),
    ("inv-002", "vj-001", "almacen-virtual",  100, "virtual"),
    ("inv-003", "vj-002", "tienda-principal", 8,   "fisico"),
    ("inv-004", "vj-002", "almacen-virtual",  50,  "virtual"),
    ("inv-005", "vj-003", "almacen-virtual",  999, "virtual"),
    ("inv-006", "vj-004", "tienda-principal", 20,  "fisico"),
    ("inv-007", "vj-004", "almacen-virtual",  75,  "virtual"),
    ("inv-008", "vj-005", "almacen-virtual",  200, "virtual"),
    ("inv-009", "vj-006", "tienda-principal", 30,  "fisico"),
    ("inv-010", "vj-007", "almacen-virtual",  999, "virtual"),
    ("inv-011", "vj-008", "tienda-principal", 5,   "fisico"),
]

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventario (
                id TEXT PRIMARY KEY,
                videojuego_id TEXT NOT NULL,
                sede TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                canal TEXT NOT NULL,
                ultima_actualizacion TEXT NOT NULL,
                UNIQUE (videojuego_id, sede)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reservas (
                id TEXT PRIMARY KEY,
                videojuego_id TEXT NOT NULL,
                sede TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                estado TEXT NOT NULL,
                fecha_reserva TEXT NOT NULL,
                fecha_expiracion TEXT NOT NULL
            )
        """)
        row = conn.execute("SELECT COUNT(*) FROM inventario").fetchone()
        if row[0] == 0:
            ahora = datetime.utcnow().isoformat()
            conn.executemany(
                "INSERT INTO inventario VALUES (?, ?, ?, ?, ?, ?)",
                [(*item, ahora) for item in SEED_DATA]
            )
            logger.info("Datos semilla insertados: %d registros de inventario", len(SEED_DATA))

@app.on_event("startup")
def startup():
    logger.info("Iniciando Servicio Inventario en puerto 8002")
    init_db()
    logger.info("Base de datos lista: %s", DB_PATH)

# --- Endpoints ---
@app.get("/health")
def health():
    try:
        with get_db() as conn:
            stock_count = conn.execute("SELECT COUNT(*) FROM inventario").fetchone()[0]
            reservas_count = conn.execute("SELECT COUNT(*) FROM reservas").fetchone()[0]
        return {
            "status": "ok",
            "servicio": "inventario",
            "puerto": 8002,
            "registros_inventario": stock_count,
            "reservas_activas": reservas_count,
        }
    except Exception as e:
        logger.error("Health check fallido: %s", e)
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

@app.get("/api/inventario")
def listar_inventario(
    videojuego_id: Optional[str] = Query(None),
    sede: Optional[str] = Query(None),
    canal: Optional[str] = Query(None),
):
    query = "SELECT * FROM inventario WHERE 1=1"
    params = []
    if videojuego_id:
        query += " AND videojuego_id = ?"
        params.append(videojuego_id)
    if sede:
        query += " AND sede = ?"
        params.append(sede)
    if canal:
        query += " AND canal = ?"
        params.append(canal)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    logger.info("Consulta inventario: %d resultados", len(rows))
    return [dict(r) for r in rows]

@app.get("/api/inventario/disponibilidad/{videojuego_id}")
def verificar_disponibilidad(
    videojuego_id: str,
    sede: Optional[str] = Query(None),
):
    query = "SELECT * FROM inventario WHERE videojuego_id = ?"
    params = [videojuego_id]
    if sede:
        query += " AND sede = ?"
        params.append(sede)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="Videojuego no encontrado en inventario")

    detalle = [dict(r) for r in rows]
    stock_total = sum(r["cantidad"] for r in detalle)

    return {
        "videojuego_id": videojuego_id,
        "stock_total": stock_total,
        "disponible": stock_total > 0,
        "detalle": detalle,
    }

@app.post("/api/inventario", status_code=201)
def crear_stock(data: StockCreate):
    nuevo_id = "inv-" + str(uuid.uuid4())[:8]
    ahora = datetime.utcnow().isoformat()
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO inventario VALUES (?, ?, ?, ?, ?, ?)",
                (nuevo_id, data.videojuego_id, data.sede, data.cantidad, data.canal, ahora)
            )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe stock para videojuego_id={data.videojuego_id} en sede={data.sede}"
        )
    logger.info("Stock creado: %s para %s en %s", nuevo_id, data.videojuego_id, data.sede)
    return {"id": nuevo_id, "videojuego_id": data.videojuego_id, "sede": data.sede, "cantidad": data.cantidad}

@app.put("/api/inventario/{videojuego_id}/{sede}")
def actualizar_stock(videojuego_id: str, sede: str, data: StockUpdate):
    ahora = datetime.utcnow().isoformat()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM inventario WHERE videojuego_id = ? AND sede = ?",
            (videojuego_id, sede)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Registro de inventario no encontrado")
        conn.execute(
            "UPDATE inventario SET cantidad = ?, ultima_actualizacion = ? WHERE videojuego_id = ? AND sede = ?",
            (data.cantidad, ahora, videojuego_id, sede)
        )
        updated = conn.execute(
            "SELECT * FROM inventario WHERE videojuego_id = ? AND sede = ?",
            (videojuego_id, sede)
        ).fetchone()
    logger.info("Stock actualizado: %s en %s -> cantidad=%d", videojuego_id, sede, data.cantidad)
    return dict(updated)

@app.post("/api/inventario/reservar", status_code=201)
def reservar_stock(data: ReservaRequest):
    ahora = datetime.utcnow()
    expiracion = (ahora + timedelta(minutes=15)).isoformat()
    ahora_iso = ahora.isoformat()
    reserva_id = "res-" + str(uuid.uuid4())[:8]

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM inventario WHERE videojuego_id = ? AND sede = ?",
            (data.videojuego_id, data.sede)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Registro de inventario no encontrado")

        stock_actual = row["cantidad"]
        if stock_actual < data.cantidad:
            raise HTTPException(
                status_code=409,
                detail=f"Stock insuficiente. Disponible: {stock_actual}, solicitado: {data.cantidad}"
            )

        conn.execute(
            "UPDATE inventario SET cantidad = ?, ultima_actualizacion = ? WHERE videojuego_id = ? AND sede = ?",
            (stock_actual - data.cantidad, ahora_iso, data.videojuego_id, data.sede)
        )
        conn.execute(
            "INSERT INTO reservas VALUES (?, ?, ?, ?, ?, ?, ?)",
            (reserva_id, data.videojuego_id, data.sede, data.cantidad, "activa", ahora_iso, expiracion)
        )

    logger.info(
        "Reserva creada: %s para %s en %s, cantidad=%d",
        reserva_id, data.videojuego_id, data.sede, data.cantidad
    )
    return {
        "reserva_id": reserva_id,
        "videojuego_id": data.videojuego_id,
        "sede": data.sede,
        "cantidad": data.cantidad,
        "estado": "activa",
        "fecha_reserva": ahora_iso,
        "fecha_expiracion": expiracion,
    }

@app.post("/api/inventario/liberar/{reserva_id}")
def liberar_reserva(reserva_id: str):
    ahora = datetime.utcnow().isoformat()

    with get_db() as conn:
        reserva = conn.execute(
            "SELECT * FROM reservas WHERE id = ?", (reserva_id,)
        ).fetchone()
        if not reserva:
            raise HTTPException(status_code=404, detail="Reserva no encontrada")
        if reserva["estado"] != "activa":
            raise HTTPException(
                status_code=409,
                detail=f"La reserva no esta activa. Estado actual: {reserva['estado']}"
            )

        conn.execute(
            "UPDATE reservas SET estado = ? WHERE id = ?",
            ("liberada", reserva_id)
        )
        conn.execute(
            """UPDATE inventario SET cantidad = cantidad + ?, ultima_actualizacion = ?
               WHERE videojuego_id = ? AND sede = ?""",
            (reserva["cantidad"], ahora, reserva["videojuego_id"], reserva["sede"])
        )

    logger.info(
        "Reserva liberada (compensacion Saga): %s, devuelto stock=%d a %s/%s",
        reserva_id, reserva["cantidad"], reserva["videojuego_id"], reserva["sede"]
    )
    return {
        "reserva_id": reserva_id,
        "estado": "liberada",
        "cantidad_devuelta": reserva["cantidad"],
        "videojuego_id": reserva["videojuego_id"],
        "sede": reserva["sede"],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
