# Almacen de Videojuegos - Arquitectura de Microservicios

## Fase 2: Implementacion MVP en Docker

| Campo       | Detalle                                        |
|-------------|------------------------------------------------|
| Proyecto    | Almacen de Videojuegos Fisico y Virtual        |
| Universidad | UNAB - Programa de Ingenieria de Software      |
| Autor       | Miguel Angel Solano Diaz                       |
| Stack       | Python 3.12 + FastAPI + SQLite                 |

---

## Arquitectura

```
                        ┌─────────────────────────────────────────────────┐
                        │              red-frontend (Docker)               │
                        │                                                   │
  Cliente               │  ┌─────────────────────────────────────────────┐ │
  (cURL / Postman)  ───►│  │           API Gateway  :8000                │ │
                        │  │   proxy · health aggregator · auth check     │ │
                        │  └───────────────────┬─────────────────────────┘ │
                        └──────────────────────┼──────────────────────────┘
                                               │
                        ┌──────────────────────┼──────────────────────────┐
                        │   red-backend (Docker)│                          │
                        │        ┌─────────────┼──────────────┐           │
                        │        ▼             ▼              ▼           │
                        │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
                        │  │ Catalogo │  │Inventario│  │    Ordenes   │  │
                        │  │  :8001   │  │  :8002   │  │    :8003     │  │
                        │  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
                        │       │              │               │           │
                        │  [catalogo.db]  [inventario.db]     │           │
                        │  (volumen)      (volumen)           │           │
                        │                              ┌──────┘           │
                        │                              │ Chained Pattern  │
                        │                    consulta  ▼                  │
                        │                    Catalogo + Inventario        │
                        │                    [ordenes.db] (volumen)       │
                        │                    [cola de eventos async]      │
                        └─────────────────────────────────────────────────┘
```

> **Ordenes** implementa el patron **Chained Microservice**: al crear una orden,
> primero valida el videojuego en Catalogo y luego verifica/reserva stock en
> Inventario antes de confirmar. Los eventos de pago/compensacion se procesan
> con una cola async en memoria que simula un Message Broker.

---

## Patrones Arquitectonicos Implementados (5)

| # | Patron | Donde se aplica |
|---|--------|-----------------|
| 1 | **API Gateway** | `api-gateway/` — punto de entrada unico, reverse proxy y health aggregator de todos los servicios |
| 2 | **Aggregator / Chained Microservice** | `servicio-ordenes/` — consulta Catalogo y luego Inventario en cadena antes de confirmar una orden |
| 3 | **Asynchronous Messaging** | `servicio-ordenes/` — cola de eventos en memoria que simula un Message Broker (RabbitMQ / Kafka) |
| 4 | **Database per Service** | Cada servicio tiene su propio `*.db` SQLite montado en un volumen Docker independiente |
| 5 | **Health Check** | Endpoint `/health` en cada servicio; el Gateway los agrega en un unico `/health` global |

---

## Requisitos Previos

- **Docker Engine** 20.10 o superior
- **Docker Compose** v2 o superior (`docker compose` sin guion)

Verificar instalacion:

```bash
docker --version
docker compose version
```

---

## Inicio Rapido

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd almacen-videojuegos-microservicios

# 2. Copiar variables de entorno
cp .env.example .env

# 3. Construir imagenes y levantar todos los servicios
docker compose up --build

# 4. Verificar que los 4 contenedores esten corriendo
docker ps
```

La API Gateway queda disponible en `http://localhost:8000`.

---

## Servicios y Puertos

| Servicio           | Puerto | Descripcion                                      |
|--------------------|--------|--------------------------------------------------|
| **API Gateway**    | `8000` | Punto de entrada unico para todos los clientes   |
| **Catalogo**       | `8001` | CRUD de videojuegos (titulo, plataforma, precio) |
| **Inventario**     | `8002` | Stock por tienda y disponibilidad                |
| **Ordenes**        | `8003` | Creacion, pago, saga de compensacion y eventos   |

---

## Pruebas con cURL

### Flujo Feliz

**0. Health check global (todos los servicios)**
```bash
curl http://localhost:8000/health
```

**1. Listar todos los videojuegos**
```bash
curl http://localhost:8000/api/videojuegos
```

**2. Obtener un videojuego por ID**
```bash
curl http://localhost:8000/api/videojuegos/vj-001
```

**3. Filtrar por plataforma**
```bash
curl "http://localhost:8000/api/videojuegos?plataforma=PS5"
```

**4. Agregar un nuevo videojuego**
```bash
curl -X POST http://localhost:8000/api/videojuegos \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Super Smash Bros Ultimate",
    "plataforma": "Nintendo Switch",
    "genero": "Pelea",
    "precio": 59.99
  }'
```

**5. Consultar inventario completo**
```bash
curl http://localhost:8000/api/inventario
```

**6. Verificar disponibilidad de un videojuego**
```bash
curl http://localhost:8000/api/inventario/disponibilidad/vj-001
```

**7. Crear una orden**
```bash
curl -X POST http://localhost:8000/api/ordenes \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: Bearer token-simulado-2026" \
  -d '{
    "cliente_nombre": "Miguel Solano",
    "cliente_email": "miguel@email.com",
    "items": [
      {"videojuego_id": "vj-001", "tienda_id": "tienda-principal", "cantidad": 2},
      {"videojuego_id": "vj-002", "tienda_id": "tienda-principal", "cantidad": 1}
    ],
    "metodo_pago": "tarjeta"
  }'
```

**8. Procesar pago de una orden**
```bash
curl -X POST http://localhost:8000/api/ordenes/pagar \
  -H "Content-Type: application/json" \
  -d '{
    "orden_id": "ord-XXXXXXXX",
    "exito": true
  }'
```

**9. Ver cola de eventos**
```bash
curl http://localhost:8000/api/eventos
```

**10. Listar todas las ordenes**
```bash
curl http://localhost:8000/api/ordenes
```

---

### Pago Fallido (Saga de Compensacion)

Demuestra que el stock reservado se libera automaticamente cuando el pago falla:

```bash
# Paso 1: Crear la orden (el stock queda RESERVADO)
curl -X POST http://localhost:8000/api/ordenes \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: Bearer token-simulado-2026" \
  -d '{
    "cliente_nombre": "Miguel Solano",
    "cliente_email": "miguel@email.com",
    "items": [{"videojuego_id": "vj-001", "tienda_id": "tienda-principal", "cantidad": 1}],
    "metodo_pago": "tarjeta"
  }'

# Paso 2: Verificar que el stock fue reservado
curl http://localhost:8000/api/inventario/disponibilidad/vj-001

# Paso 3: Simular pago fallido (exito: false)
curl -X POST http://localhost:8000/api/ordenes/pagar \
  -H "Content-Type: application/json" \
  -d '{"orden_id": "ord-XXXXXXXX", "exito": false}'

# Paso 4: Verificar que el stock fue LIBERADO (saga de compensacion ejecutada)
curl http://localhost:8000/api/inventario/disponibilidad/vj-001

# Paso 5: Confirmar el evento de compensacion en la cola
curl http://localhost:8000/api/eventos
```

---

### Autenticacion Fallida

El endpoint de ordenes requiere el header `X-Auth-Token`. Sin el, retorna `401 Unauthorized`:

```bash
# Sin header de autenticacion -> 401
curl -X POST http://localhost:8000/api/ordenes \
  -H "Content-Type: application/json" \
  -d '{"cliente_nombre": "Test", "cliente_email": "test@email.com", "items": [], "metodo_pago": "tarjeta"}'
```

---

## Test del Mono

Verifica la resiliencia del sistema ante caidas de servicios individuales.

### Escenario 1: Caida del Servicio Inventario

```bash
# 1. Verificar que todo esta saludable
curl http://localhost:8000/health

# 2. Derribar el servicio de inventario
docker stop servicio-inventario

# 3. El Gateway detecta la caida (inventario marcado como "no_disponible")
curl http://localhost:8000/health

# 4. Intentar crear una orden -> responde 503 de forma graceful (no crash)
curl -X POST http://localhost:8000/api/ordenes \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: Bearer token-simulado-2026" \
  -d '{"cliente_nombre": "Test", "cliente_email": "test@email.com", "items": [{"videojuego_id": "vj-001", "tienda_id": "tienda-principal", "cantidad": 1}], "metodo_pago": "tarjeta"}'

# 5. Catalogo sigue funcionando de forma INDEPENDIENTE
curl http://localhost:8000/api/videojuegos

# 6. Recuperar el servicio
docker start servicio-inventario

# 7. Verificar recuperacion automatica
curl http://localhost:8000/health
```

### Escenario 2: Caida del Servicio Catalogo

```bash
# 1. Verificar estado inicial
curl http://localhost:8000/health

# 2. Derribar el servicio de catalogo
docker stop servicio-catalogo

# 3. Gateway detecta la caida (catalogo marcado como "no_disponible")
curl http://localhost:8000/health

# 4. Intentar listar videojuegos -> 503 graceful
curl http://localhost:8000/api/videojuegos

# 5. Inventario sigue funcionando de forma INDEPENDIENTE
curl http://localhost:8000/api/inventario

# 6. Recuperar y verificar
docker start servicio-catalogo
curl http://localhost:8000/health
```

---

## Detener la Solucion

```bash
# Detener y eliminar contenedores (conserva volumenes y datos)
docker compose down

# Detener, eliminar contenedores Y borrar volumenes (datos perdidos)
docker compose down -v
```

---

## Estructura del Repositorio

```
almacen-videojuegos-microservicios/
├── docker-compose.yml          # Orquestacion de los 4 servicios
├── .env.example                # Variables de entorno de referencia
├── README.md                   # Este archivo
├── docs/                       # Documentacion adicional
├── api-gateway/
│   ├── Dockerfile              # Imagen del gateway
│   ├── main.py                 # Proxy, health aggregator, auth check
│   └── requirements.txt
├── servicio-catalogo/
│   ├── Dockerfile
│   ├── main.py                 # CRUD de videojuegos + SQLite
│   └── requirements.txt
├── servicio-inventario/
│   ├── Dockerfile
│   ├── main.py                 # Stock por tienda + SQLite
│   └── requirements.txt
└── servicio-ordenes/
    ├── Dockerfile
    ├── main.py                 # Chained pattern + Saga + cola async + SQLite
    └── requirements.txt
```

---

## Respuestas de Defensa (Sustentacion)

### Por que son microservicios y no modulos de un monolito?

Cada servicio tiene su **propio proceso** (contenedor Docker independiente), su **propia base de datos** (volumen aislado), su **propio Dockerfile** y su **propio ciclo de despliegue**. Se pueden escalar, actualizar y fallar de forma completamente independiente. Si `servicio-catalogo` cae, `servicio-inventario` y `servicio-ordenes` continuan operando. En un monolito, un fallo en un modulo derriba toda la aplicacion.

---

### Como evita la solucion el acoplamiento fuerte?

- **Comunicacion exclusivamente por HTTP/REST**: ningun servicio importa codigo de otro ni accede directamente a su base de datos.
- **Contratos bien definidos**: cada servicio expone una API documentada; los demas consumen esa API, no los internos.
- **Timeouts y fallbacks**: si un servicio dependiente no responde dentro del timeout configurado, el servicio solicitante retorna un error controlado (`503`) en lugar de bloquearse indefinidamente.
- **Redes Docker segmentadas**: `red-frontend` solo expone el Gateway al exterior; los servicios internos viven en `red-backend` sin acceso publico directo.

---

### Que cambiarias para produccion?

| Componente actual | Reemplazo productivo | Motivo |
|-------------------|----------------------|--------|
| SQLite | PostgreSQL / MongoDB | Concurrencia, replicacion y backups gestionados |
| Cola en memoria | RabbitMQ / Apache Kafka | Durabilidad de mensajes, escalado horizontal |
| Token simulado | JWT real con Auth0 / Keycloak | Seguridad, expiracion, roles y scopes |
| Docker Compose | Kubernetes (EKS / GKE) | Auto-scaling, rolling deploys, self-healing |
| Reintentos manuales | Circuit Breaker con `tenacity` | Proteccion ante cascadas de fallos |
| Logs en consola | Prometheus + Grafana + ELK Stack | Observabilidad, alertas y trazabilidad distribuida |
