import sqlite3
import logging
import os
import uuid
import collections
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Header, Query
from pydantic import BaseModel, Field

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ORDENES] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# --- Config ---
DB_PATH         = os.getenv("ORDENES_DB_PATH",    "./data/ordenes.db")
CATALOGO_URL    = os.getenv("CATALOGO_URL",        "http://servicio-catalogo:8001")
INVENTARIO_URL  = os.getenv("INVENTARIO_URL",      "http://servicio-inventario:8002")
SERVICE_TIMEOUT = int(os.getenv("SERVICE_TIMEOUT", "5"))

app = FastAPI(title="Servicio Ordenes")

# --- Cola de notificaciones (simula Message Broker) ---
cola_eventos: collections.deque = collections.deque(maxlen=1000)

def publicar_evento(tipo: str, datos: dict):
    evento = {
        "id":         "evt-" + str(uuid.uuid4())[:8],
        "tipo":       tipo,
        "datos":      datos,
        "timestamp":  datetime.utcnow().isoformat(),
        "procesado":  False,
    }
    cola_eventos.append(evento)
    logger.info("Evento publicado: %s [%s]", tipo, evento["id"])

# --- Pydantic Models ---
class ItemOrden(BaseModel):
    videojuego_id: str
    sede: str
    cantidad: int = Field(..., gt=0)

class OrdenCreate(BaseModel):
    cliente_nombre: str
    cliente_email: str
    items: list[ItemOrden] = Field(..., min_length=1)
    metodo_pago: str = "tarjeta"

class SimularPagoRequest(BaseModel):
    orden_id: str
    exito: bool = True

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

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ordenes (
                id TEXT PRIMARY KEY,
                cliente_nombre TEXT NOT NULL,
                cliente_email TEXT NOT NULL,
                estado TEXT NOT NULL DEFAULT 'pendiente',
                total REAL NOT NULL,
                metodo_pago TEXT NOT NULL,
                fecha_creacion TEXT NOT NULL,
                reserva_ids TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orden_items (
                id TEXT PRIMARY KEY,
                orden_id TEXT NOT NULL,
                videojuego_id TEXT NOT NULL,
                titulo TEXT NOT NULL,
                sede TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                precio_unitario REAL NOT NULL,
                subtotal REAL NOT NULL
            )
        """)

@app.on_event("startup")
def startup():
    logger.info("Iniciando Servicio Ordenes en puerto 8003")
    init_db()
    logger.info("Base de datos lista: %s", DB_PATH)

# --- HTTP Helpers ---
async def consultar_catalogo(videojuego_id: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=SERVICE_TIMEOUT) as client:
            resp = await client.get(f"{CATALOGO_URL}/api/videojuegos/{videojuego_id}")
            resp.raise_for_status()
            return resp.json()
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.error("Error al conectar con catalogo: %s", e)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("Error HTTP catalogo %s: %s", videojuego_id, e)
        return None

async def consultar_disponibilidad(videojuego_id: str, sede: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=SERVICE_TIMEOUT) as client:
            resp = await client.get(
                f"{INVENTARIO_URL}/api/inventario/disponibilidad/{videojuego_id}",
                params={"sede": sede}
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.error("Error al conectar con inventario (disponibilidad): %s", e)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("Error HTTP inventario disponibilidad %s: %s", videojuego_id, e)
        return None

async def reservar_stock(videojuego_id: str, sede: str, cantidad: int) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=SERVICE_TIMEOUT) as client:
            resp = await client.post(
                f"{INVENTARIO_URL}/api/inventario/reservar",
                json={"videojuego_id": videojuego_id, "sede": sede, "cantidad": cantidad}
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.error("Error al conectar con inventario (reservar): %s", e)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("Error HTTP inventario reservar %s: %s", videojuego_id, e)
        return None

async def liberar_stock(reserva_id: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=SERVICE_TIMEOUT) as client:
            resp = await client.post(f"{INVENTARIO_URL}/api/inventario/liberar/{reserva_id}")
            resp.raise_for_status()
            return resp.json()
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.error("Error al conectar con inventario (liberar): %s", e)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("Error HTTP inventario liberar %s: %s", reserva_id, e)
        return None

# --- Helpers internos ---
def _obtener_orden_con_items(conn, orden_id: str) -> Optional[dict]:
    orden = conn.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
    if not orden:
        return None
    items = conn.execute("SELECT * FROM orden_items WHERE orden_id = ?", (orden_id,)).fetchall()
    resultado = dict(orden)
    resultado["items"] = [dict(i) for i in items]
    return resultado

async def _liberar_reservas(reserva_ids: list[str]):
    for rid in reserva_ids:
        await liberar_stock(rid)
        logger.info("Saga compensacion: reserva liberada %s", rid)

# --- Endpoints ---
@app.get("/health")
def health():
    try:
        with get_db() as conn:
            ordenes_count = conn.execute("SELECT COUNT(*) FROM ordenes").fetchone()[0]
        return {
            "status": "ok",
            "servicio": "ordenes",
            "puerto": 8003,
            "total_ordenes": ordenes_count,
            "eventos_en_cola": len(cola_eventos),
        }
    except Exception as e:
        logger.error("Health check fallido: %s", e)
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

@app.post("/api/ordenes", status_code=201)
async def crear_orden(
    data: OrdenCreate,
    x_auth_token: Optional[str] = Header(None),
):
    # Autenticacion simulada
    if x_auth_token != "Bearer token-simulado-2026":
        raise HTTPException(status_code=401, detail="Token de autenticacion invalido o ausente")

    orden_id    = "ord-" + str(uuid.uuid4())[:8]
    ahora       = datetime.utcnow().isoformat()
    reserva_ids = []
    items_detalle = []
    total = 0.0
    servicio_caido = False

    for item in data.items:
        # 1. Consultar catalogo para obtener precio y titulo
        vj = await consultar_catalogo(item.videojuego_id)
        if vj is None:
            servicio_caido = True
            logger.error("Servicio catalogo no disponible o videojuego %s no encontrado", item.videojuego_id)
            break

        # 2. Consultar disponibilidad
        disponibilidad = await consultar_disponibilidad(item.videojuego_id, item.sede)
        if disponibilidad is None:
            servicio_caido = True
            logger.error("Servicio inventario no disponible para %s", item.videojuego_id)
            break

        stock_total = disponibilidad.get("stock_total", 0)
        if stock_total < item.cantidad:
            # Stock insuficiente: compensacion Saga
            await _liberar_reservas(reserva_ids)
            raise HTTPException(
                status_code=409,
                detail=f"Stock insuficiente para {item.videojuego_id} en {item.sede}. "
                       f"Disponible: {stock_total}, solicitado: {item.cantidad}"
            )

        # 3. Reservar stock
        reserva = await reservar_stock(item.videojuego_id, item.sede, item.cantidad)
        if reserva is None:
            servicio_caido = True
            logger.error("No se pudo reservar stock para %s", item.videojuego_id)
            break

        reserva_ids.append(reserva["reserva_id"])
        precio = float(vj["precio"])
        subtotal = precio * item.cantidad
        total += subtotal
        items_detalle.append({
            "id":              "oit-" + str(uuid.uuid4())[:8],
            "orden_id":        orden_id,
            "videojuego_id":   item.videojuego_id,
            "titulo":          vj["titulo"],
            "sede":            item.sede,
            "cantidad":        item.cantidad,
            "precio_unitario": precio,
            "subtotal":        subtotal,
        })

    if servicio_caido:
        await _liberar_reservas(reserva_ids)
        raise HTTPException(
            status_code=503,
            detail="Uno o mas servicios no estan disponibles. Orden cancelada, reservas liberadas."
        )

    # Persistir orden e items
    with get_db() as conn:
        conn.execute(
            "INSERT INTO ordenes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (orden_id, data.cliente_nombre, data.cliente_email, "pendiente",
             round(total, 2), data.metodo_pago, ahora, ",".join(reserva_ids))
        )
        conn.executemany(
            "INSERT INTO orden_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(i["id"], i["orden_id"], i["videojuego_id"], i["titulo"],
              i["sede"], i["cantidad"], i["precio_unitario"], i["subtotal"])
             for i in items_detalle]
        )

    publicar_evento("OrderCreated", {
        "orden_id":       orden_id,
        "cliente":        data.cliente_nombre,
        "total":          round(total, 2),
        "items":          len(items_detalle),
        "reservas":       reserva_ids,
    })

    logger.info("Orden creada: %s para %s, total=%.2f", orden_id, data.cliente_nombre, total)
    return {
        "orden_id":      orden_id,
        "estado":        "pendiente",
        "cliente_nombre": data.cliente_nombre,
        "cliente_email": data.cliente_email,
        "total":         round(total, 2),
        "metodo_pago":   data.metodo_pago,
        "fecha_creacion": ahora,
        "reserva_ids":   reserva_ids,
        "items":         items_detalle,
    }

@app.post("/api/ordenes/pagar")
async def simular_pago(data: SimularPagoRequest):
    with get_db() as conn:
        orden = conn.execute("SELECT * FROM ordenes WHERE id = ?", (data.orden_id,)).fetchone()
        if not orden:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        if orden["estado"] not in ("pendiente",):
            raise HTTPException(
                status_code=409,
                detail=f"La orden no esta en estado pendiente. Estado actual: {orden['estado']}"
            )

        reserva_ids = [r for r in orden["reserva_ids"].split(",") if r]

        if data.exito:
            nuevo_estado = "confirmada"
            conn.execute(
                "UPDATE ordenes SET estado = ? WHERE id = ?",
                (nuevo_estado, data.orden_id)
            )
            publicar_evento("PaymentCompleted", {
                "orden_id": data.orden_id,
                "total":    orden["total"],
                "metodo":   orden["metodo_pago"],
            })
            publicar_evento("NotificacionEnviada", {
                "orden_id": data.orden_id,
                "cliente":  orden["cliente_email"],
                "asunto":   "Pago confirmado - Orden " + data.orden_id,
            })
            logger.info("Pago exitoso para orden %s", data.orden_id)
        else:
            nuevo_estado = "cancelada"
            conn.execute(
                "UPDATE ordenes SET estado = ? WHERE id = ?",
                (nuevo_estado, data.orden_id)
            )
            # Compensacion Saga: liberar todas las reservas
            await _liberar_reservas(reserva_ids)
            publicar_evento("PaymentFailed", {
                "orden_id":  data.orden_id,
                "reservas_liberadas": reserva_ids,
            })
            publicar_evento("NotificacionEnviada", {
                "orden_id": data.orden_id,
                "cliente":  orden["cliente_email"],
                "asunto":   "Pago fallido - Orden " + data.orden_id,
            })
            logger.info("Pago fallido para orden %s, reservas liberadas: %s", data.orden_id, reserva_ids)

    return {
        "orden_id": data.orden_id,
        "estado":   nuevo_estado,
        "exito":    data.exito,
        "mensaje":  "Pago procesado correctamente" if data.exito else "Pago fallido, reservas liberadas",
    }

@app.get("/api/ordenes")
def listar_ordenes(estado: Optional[str] = Query(None)):
    query = "SELECT * FROM ordenes WHERE 1=1"
    params = []
    if estado:
        query += " AND estado = ?"
        params.append(estado)

    with get_db() as conn:
        ordenes = conn.execute(query, params).fetchall()
        resultado = []
        for o in ordenes:
            items = conn.execute(
                "SELECT * FROM orden_items WHERE orden_id = ?", (o["id"],)
            ).fetchall()
            entrada = dict(o)
            entrada["items"] = [dict(i) for i in items]
            resultado.append(entrada)

    logger.info("Consulta de ordenes: %d resultados", len(resultado))
    return resultado

@app.get("/api/ordenes/{orden_id}")
def obtener_orden(orden_id: str):
    with get_db() as conn:
        orden = _obtener_orden_con_items(conn, orden_id)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return orden

@app.get("/api/eventos")
def listar_eventos(tipo: Optional[str] = Query(None)):
    eventos = list(cola_eventos)
    if tipo:
        eventos = [e for e in eventos if e["tipo"] == tipo]
    return {
        "total":   len(eventos),
        "eventos": eventos,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
