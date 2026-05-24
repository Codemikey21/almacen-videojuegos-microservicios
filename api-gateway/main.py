import logging
import os

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [GATEWAY] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# --- Config ---
GATEWAY_PORT    = int(os.getenv("GATEWAY_PORT",    "8080"))
SERVICE_TIMEOUT = int(os.getenv("SERVICE_TIMEOUT", "5"))
CATALOGO_URL    = os.getenv("CATALOGO_URL",   "http://servicio-catalogo:8001")
INVENTARIO_URL  = os.getenv("INVENTARIO_URL", "http://servicio-inventario:8002")
ORDENES_URL     = os.getenv("ORDENES_URL",    "http://servicio-ordenes:8003")

SERVICES = {
    "catalogo":   CATALOGO_URL,
    "inventario": INVENTARIO_URL,
    "ordenes":    ORDENES_URL,
}

app = FastAPI(title="API Gateway - Almacen de Videojuegos")

# --- Health check agregado ---
@app.get("/health")
async def health():
    resultados = {}
    todos_ok = True

    async with httpx.AsyncClient(timeout=SERVICE_TIMEOUT) as client:
        for nombre, url in SERVICES.items():
            try:
                resp = await client.get(f"{url}/health")
                if resp.status_code == 200:
                    resultados[nombre] = {"status": "ok", "detalle": resp.json()}
                else:
                    resultados[nombre] = {"status": "error", "codigo": resp.status_code}
                    todos_ok = False
            except httpx.TimeoutException:
                resultados[nombre] = {"status": "timeout"}
                todos_ok = False
            except httpx.ConnectError:
                resultados[nombre] = {"status": "no disponible"}
                todos_ok = False

    return {
        "gateway":       "ok",
        "estado_global": "saludable" if todos_ok else "degradado",
        "servicios":     resultados,
    }

# --- Proxy helper ---
async def proxy_request(service_name: str, path: str, request: Request) -> JSONResponse:
    base_url = SERVICES[service_name]
    url = f"{base_url}{path}"

    headers = {}
    if "content-type" in request.headers:
        headers["content-type"] = request.headers["content-type"]
    if "x-auth-token" in request.headers:
        headers["x-auth-token"] = request.headers["x-auth-token"]

    params = dict(request.query_params)
    body   = await request.body()

    logger.info("Proxy %s %s -> %s", request.method, request.url.path, url)

    try:
        async with httpx.AsyncClient(timeout=SERVICE_TIMEOUT) as client:
            resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=params,
                content=body,
            )
        return JSONResponse(status_code=resp.status_code, content=resp.json())
    except httpx.TimeoutException:
        logger.error("Timeout al contactar servicio %s: %s", service_name, url)
        raise HTTPException(
            status_code=504,
            detail=f"El servicio {service_name} no respondio en {SERVICE_TIMEOUT} segundos"
        )
    except httpx.ConnectError:
        logger.error("Conexion rechazada por servicio %s: %s", service_name, url)
        raise HTTPException(
            status_code=503,
            detail=f"El servicio {service_name} no esta disponible"
        )

# --- Rutas proxy: Catalogo ---
@app.api_route("/api/videojuegos", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_catalogo_root(request: Request):
    return await proxy_request("catalogo", "/api/videojuegos", request)

@app.api_route("/api/videojuegos/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_catalogo(path: str, request: Request):
    return await proxy_request("catalogo", f"/api/videojuegos/{path}", request)

# --- Rutas proxy: Inventario ---
@app.api_route("/api/inventario", methods=["GET", "POST", "PUT"])
async def proxy_inventario_root(request: Request):
    return await proxy_request("inventario", "/api/inventario", request)

@app.api_route("/api/inventario/{path:path}", methods=["GET", "POST", "PUT"])
async def proxy_inventario(path: str, request: Request):
    return await proxy_request("inventario", f"/api/inventario/{path}", request)

# --- Rutas proxy: Ordenes ---
@app.api_route("/api/ordenes", methods=["GET", "POST"])
async def proxy_ordenes_root(request: Request):
    return await proxy_request("ordenes", "/api/ordenes", request)

@app.api_route("/api/ordenes/{path:path}", methods=["GET", "POST"])
async def proxy_ordenes(path: str, request: Request):
    return await proxy_request("ordenes", f"/api/ordenes/{path}", request)

# --- Rutas proxy: Eventos ---
@app.api_route("/api/eventos", methods=["GET"])
async def proxy_eventos(request: Request):
    return await proxy_request("ordenes", "/api/eventos", request)

# --- Info ---
@app.get("/")
def info():
    return {
        "plataforma":  "Almacen de Videojuegos - Microservicios",
        "version":     "1.0.0",
        "gateway":     f"Puerto {GATEWAY_PORT}",
        "servicios": {
            "catalogo":   CATALOGO_URL,
            "inventario": INVENTARIO_URL,
            "ordenes":    ORDENES_URL,
        },
        "endpoints_disponibles": [
            "GET  /health                            - Estado de todos los servicios",
            "GET  /api/videojuegos                   - Listar videojuegos",
            "GET  /api/videojuegos/{id}              - Consultar videojuego",
            "POST /api/videojuegos                   - Crear videojuego",
            "PUT  /api/videojuegos/{id}              - Actualizar videojuego",
            "DELETE /api/videojuegos/{id}            - Eliminar videojuego",
            "GET  /api/inventario                    - Listar inventario",
            "GET  /api/inventario/disponibilidad/{id}- Verificar disponibilidad",
            "POST /api/inventario                    - Crear stock",
            "PUT  /api/inventario/{id}/{sede}        - Actualizar stock",
            "POST /api/inventario/reservar           - Reservar stock",
            "POST /api/inventario/liberar/{id}       - Liberar reserva",
            "GET  /api/ordenes                       - Listar ordenes",
            "POST /api/ordenes                       - Crear orden (requiere auth)",
            "GET  /api/ordenes/{id}                  - Consultar orden",
            "POST /api/ordenes/pagar                 - Simular pago",
            "GET  /api/eventos                       - Ver cola de eventos",
        ],
        "autenticacion": "Endpoints de ordenes requieren header: X-Auth-Token: Bearer token-simulado-2026",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=GATEWAY_PORT, reload=True)
