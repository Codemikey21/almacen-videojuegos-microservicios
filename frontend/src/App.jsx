import { useState, useEffect, useCallback } from "react";

const API = "";

const TABS = [
  { id: "catalogo", label: "CATALOGO", icon: "\u{1F3AE}" },
  { id: "inventario", label: "INVENTARIO", icon: "\u{1F4E6}" },
  { id: "orden", label: "NUEVA ORDEN", icon: "\u{1F6D2}" },
  { id: "eventos", label: "EVENTOS", icon: "\u{26A1}" },
  { id: "monkey", label: "CHAOS MONKEY", icon: "\u{1F480}" },
];

const PLAT_COLORS = {
  "Nintendo Switch": { bg: "#e60012", text: "#fff" },
  PS5: { bg: "#003087", text: "#fff" },
  "Xbox Series X": { bg: "#107c10", text: "#fff" },
  PC: { bg: "#444", text: "#ccc" },
};

function StatusDot({ ok }) {
  return (
    <span
      style={{
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: ok ? "#00e676" : "#ff1744",
        display: "inline-block",
        boxShadow: ok ? "0 0 6px #00e676" : "0 0 6px #ff1744",
      }}
    />
  );
}

function ServiceCard({ name, port, status }) {
  const ok = status === "saludable" || status === "ok";
  return (
    <div
      style={{
        background: "#111118",
        border: `1px solid ${ok ? "#1a1a2e" : "#ff1744"}`,
        padding: "16px 20px",
        flex: 1,
        minWidth: 140,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 8,
        }}
      >
        <StatusDot ok={ok} />
        <span
          style={{
            fontSize: 11,
            letterSpacing: 2,
            color: "#666",
            textTransform: "uppercase",
          }}
        >
          {name}
        </span>
      </div>
      <div
        style={{
          fontFamily: "'Bebas Neue', sans-serif",
          fontSize: 26,
          color: ok ? "#e8c840" : "#ff1744",
        }}
      >
        :{port}
      </div>
    </div>
  );
}

function PlatBadge({ plat }) {
  const c = PLAT_COLORS[plat] || { bg: "#333", text: "#aaa" };
  const short =
    plat === "Nintendo Switch"
      ? "SWITCH"
      : plat === "Xbox Series X"
        ? "XBOX"
        : plat;
  return (
    <span
      style={{
        background: c.bg,
        color: c.text,
        padding: "2px 10px",
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: 1,
        textTransform: "uppercase",
      }}
    >
      {short}
    </span>
  );
}

function CatalogoTab() {
  const [games, setGames] = useState([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/videojuegos`)
      .then((r) => r.json())
      .then(setGames)
      .catch(() => setGames([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter
    ? games.filter(
        (g) => g.plataforma.toLowerCase().includes(filter.toLowerCase()) ||
               g.genero.toLowerCase().includes(filter.toLowerCase()) ||
               g.titulo.toLowerCase().includes(filter.toLowerCase())
      )
    : games;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
        <h2 style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: 28, letterSpacing: 3, color: "#e8c840", margin: 0 }}>
          CATALOGO DE VIDEOJUEGOS
        </h2>
        <span style={{ fontSize: 13, color: "#555" }}>{games.length} titulos</span>
      </div>
      <input
        type="text"
        placeholder="Buscar por titulo, plataforma o genero..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        style={{
          width: "100%",
          padding: "10px 16px",
          background: "#0d0d14",
          border: "1px solid #1e1e2e",
          color: "#e0ddd4",
          fontSize: 14,
          marginBottom: 16,
          outline: "none",
          fontFamily: "'Rajdhani', sans-serif",
        }}
      />
      {loading ? (
        <div style={{ textAlign: "center", padding: 40, color: "#555" }}>Cargando...</div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #1e1e2e" }}>
                {["ID", "TITULO", "PLATAFORMA", "GENERO", "PRECIO", "FORMATO"].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: h === "PRECIO" ? "right" : "left",
                      padding: "10px 12px",
                      fontSize: 11,
                      letterSpacing: 2,
                      color: "#555",
                      fontWeight: 400,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((g) => (
                <tr
                  key={g.id}
                  style={{ borderBottom: "1px solid #111118", cursor: "pointer" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#111118")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <td style={{ padding: "10px 12px", color: "#444", fontSize: 11, fontFamily: "monospace" }}>{g.id}</td>
                  <td style={{ padding: "10px 12px", fontWeight: 600 }}>{g.titulo}</td>
                  <td style={{ padding: "10px 12px" }}><PlatBadge plat={g.plataforma} /></td>
                  <td style={{ padding: "10px 12px", color: "#777" }}>{g.genero}</td>
                  <td style={{ padding: "10px 12px", textAlign: "right", fontFamily: "'Bebas Neue', sans-serif", fontSize: 18, color: "#e8c840" }}>${g.precio}</td>
                  <td style={{ padding: "10px 12px" }}>
                    <span style={{ border: "1px solid #1e1e2e", padding: "2px 8px", fontSize: 11, color: "#666", letterSpacing: 1, textTransform: "uppercase" }}>
                      {g.formato}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function InventarioTab() {
  const [inv, setInv] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/inventario`)
      .then((r) => r.json())
      .then(setInv)
      .catch(() => setInv([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h2 style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: 28, letterSpacing: 3, color: "#e8c840", marginBottom: 20 }}>
        CONTROL DE INVENTARIO
      </h2>
      {loading ? (
        <div style={{ textAlign: "center", padding: 40, color: "#555" }}>Cargando...</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
          {inv.map((item) => (
            <div
              key={item.id}
              style={{
                background: "#111118",
                border: "1px solid #1e1e2e",
                padding: "16px 20px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: "#555", fontFamily: "monospace" }}>{item.videojuego_id}</span>
                <span
                  style={{
                    fontFamily: "'Bebas Neue', sans-serif",
                    fontSize: 28,
                    color: item.cantidad > 10 ? "#00e676" : item.cantidad > 0 ? "#e8c840" : "#ff1744",
                  }}
                >
                  {item.cantidad}
                </span>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <span style={{ fontSize: 11, padding: "2px 8px", background: "#1a1a2e", color: "#888", letterSpacing: 1, textTransform: "uppercase" }}>
                  {item.sede}
                </span>
                <span style={{ fontSize: 11, padding: "2px 8px", border: "1px solid #1e1e2e", color: "#666", letterSpacing: 1, textTransform: "uppercase" }}>
                  {item.canal}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function OrdenTab() {
  const [nombre, setNombre] = useState("Miguel Solano");
  const [email, setEmail] = useState("miguel@email.com");
  const [vjId, setVjId] = useState("vj-001");
  const [sede, setSede] = useState("tienda-principal");
  const [cantidad, setCantidad] = useState(1);
  const [metodo, setMetodo] = useState("tarjeta");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pagoResult, setPagoResult] = useState(null);

  const crearOrden = async () => {
    setLoading(true);
    setResult(null);
    setPagoResult(null);
    try {
      const res = await fetch(`${API}/api/ordenes`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Auth-Token": "Bearer token-simulado-2026" },
        body: JSON.stringify({
          cliente_nombre: nombre,
          cliente_email: email,
          items: [{ videojuego_id: vjId, sede, cantidad: parseInt(cantidad) }],
          metodo_pago: metodo,
        }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ error: "No se pudo conectar al servicio" });
    }
    setLoading(false);
  };

  const pagar = async (exito) => {
    if (!result?.orden_id) return;
    try {
      const res = await fetch(`${API}/api/ordenes/pagar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ orden_id: result.orden_id, exito }),
      });
      const data = await res.json();
      setPagoResult(data);
    } catch (e) {
      setPagoResult({ error: "Error al procesar pago" });
    }
  };

  const inputStyle = {
    padding: "10px 14px",
    background: "#0d0d14",
    border: "1px solid #1e1e2e",
    color: "#e0ddd4",
    fontSize: 14,
    fontFamily: "'Rajdhani', sans-serif",
    outline: "none",
    width: "100%",
  };

  return (
    <div>
      <h2 style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: 28, letterSpacing: 3, color: "#e8c840", marginBottom: 20 }}>
        CREAR NUEVA ORDEN
      </h2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        <div>
          <label style={{ fontSize: 11, color: "#555", letterSpacing: 2, display: "block", marginBottom: 4 }}>NOMBRE</label>
          <input value={nombre} onChange={(e) => setNombre(e.target.value)} style={inputStyle} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "#555", letterSpacing: 2, display: "block", marginBottom: 4 }}>EMAIL</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} style={inputStyle} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "#555", letterSpacing: 2, display: "block", marginBottom: 4 }}>VIDEOJUEGO ID</label>
          <input value={vjId} onChange={(e) => setVjId(e.target.value)} style={inputStyle} placeholder="vj-001" />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "#555", letterSpacing: 2, display: "block", marginBottom: 4 }}>SEDE</label>
          <select value={sede} onChange={(e) => setSede(e.target.value)} style={{ ...inputStyle, cursor: "pointer" }}>
            <option value="tienda-principal">Tienda Principal</option>
            <option value="almacen-virtual">Almacen Virtual</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: 11, color: "#555", letterSpacing: 2, display: "block", marginBottom: 4 }}>CANTIDAD</label>
          <input type="number" min={1} value={cantidad} onChange={(e) => setCantidad(e.target.value)} style={inputStyle} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "#555", letterSpacing: 2, display: "block", marginBottom: 4 }}>METODO DE PAGO</label>
          <select value={metodo} onChange={(e) => setMetodo(e.target.value)} style={{ ...inputStyle, cursor: "pointer" }}>
            <option value="tarjeta">Tarjeta</option>
            <option value="efectivo">Efectivo</option>
            <option value="PSE">PSE</option>
          </select>
        </div>
      </div>
      <button
        onClick={crearOrden}
        disabled={loading}
        style={{
          padding: "12px 32px",
          background: loading ? "#333" : "#e8c840",
          color: "#000",
          border: "none",
          fontFamily: "'Bebas Neue', sans-serif",
          fontSize: 18,
          letterSpacing: 3,
          cursor: loading ? "wait" : "pointer",
          width: "100%",
          marginBottom: 16,
        }}
      >
        {loading ? "PROCESANDO..." : "CREAR ORDEN"}
      </button>

      {result && (
        <div style={{ background: "#111118", border: "1px solid #1e1e2e", padding: 20, marginBottom: 12 }}>
          <div style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: 20, color: result.error ? "#ff1744" : "#e8c840", marginBottom: 8 }}>
            {result.error ? "ERROR" : `ORDEN: ${result.orden_id}`}
          </div>
          {result.error ? (
            <div style={{ color: "#ff1744", fontSize: 13 }}>{typeof result.error === "string" ? result.error : result.detail || JSON.stringify(result)}</div>
          ) : (
            <>
              <div style={{ fontSize: 13, color: "#888", marginBottom: 12 }}>
                Total: <span style={{ color: "#e8c840", fontFamily: "'Bebas Neue', sans-serif", fontSize: 22 }}>${result.total}</span>
                {" | "}Estado: <span style={{ color: "#00e676" }}>{result.estado}</span>
              </div>
              <div style={{ display: "flex", gap: 12 }}>
                <button
                  onClick={() => pagar(true)}
                  style={{ flex: 1, padding: "10px", background: "#00e676", color: "#000", border: "none", fontFamily: "'Bebas Neue', sans-serif", fontSize: 16, letterSpacing: 2, cursor: "pointer" }}
                >
                  PAGO EXITOSO
                </button>
                <button
                  onClick={() => pagar(false)}
                  style={{ flex: 1, padding: "10px", background: "#ff1744", color: "#fff", border: "none", fontFamily: "'Bebas Neue', sans-serif", fontSize: 16, letterSpacing: 2, cursor: "pointer" }}
                >
                  PAGO FALLIDO
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {pagoResult && (
        <div style={{ background: "#111118", border: `1px solid ${pagoResult.estado === "confirmada" ? "#00e676" : "#ff1744"}`, padding: 20 }}>
          <div style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: 18, color: pagoResult.estado === "confirmada" ? "#00e676" : "#ff1744", marginBottom: 8 }}>
            {pagoResult.estado === "confirmada" ? "PAGO CONFIRMADO" : "PAGO RECHAZADO — SAGA COMPENSACION"}
          </div>
          <div style={{ fontSize: 13, color: "#888" }}>{pagoResult.mensaje}</div>
          {pagoResult.reservas_liberadas && (
            <div style={{ fontSize: 12, color: "#ff1744", marginTop: 8 }}>
              Reservas liberadas: {pagoResult.reservas_liberadas.join(", ")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EventosTab() {
  const [eventos, setEventos] = useState([]);
  const [loading, setLoading] = useState(true);

  const cargar = useCallback(() => {
    setLoading(true);
    fetch(`${API}/api/eventos`)
      .then((r) => r.json())
      .then((d) => setEventos(d.eventos || []))
      .catch(() => setEventos([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  const tipoColor = {
    OrderCreated: "#e8c840",
    PaymentCompleted: "#00e676",
    PaymentFailed: "#ff1744",
    NotificacionEnviada: "#448aff",
  };

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
        <h2 style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: 28, letterSpacing: 3, color: "#e8c840", margin: 0 }}>
          COLA DE EVENTOS ASYNC
        </h2>
        <button
          onClick={cargar}
          style={{ padding: "6px 16px", background: "transparent", border: "1px solid #1e1e2e", color: "#888", fontSize: 12, cursor: "pointer", letterSpacing: 1 }}
        >
          REFRESH
        </button>
      </div>
      <div style={{ fontSize: 12, color: "#555", marginBottom: 16 }}>
        Patron: Asynchronous Messaging — Los eventos se publican en una cola en memoria simulando un Message Broker
      </div>
      {loading ? (
        <div style={{ textAlign: "center", padding: 40, color: "#555" }}>Cargando...</div>
      ) : eventos.length === 0 ? (
        <div style={{ textAlign: "center", padding: 40, color: "#555" }}>No hay eventos. Crea una orden para generar eventos.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {eventos.map((ev, i) => (
            <div key={ev.id || i} style={{ background: "#111118", border: "1px solid #1e1e2e", padding: "12px 16px", display: "flex", alignItems: "center", gap: 16 }}>
              <span style={{ fontSize: 11, color: "#444", fontFamily: "monospace", minWidth: 80 }}>{ev.id}</span>
              <span
                style={{
                  padding: "2px 10px",
                  background: (tipoColor[ev.tipo] || "#555") + "22",
                  color: tipoColor[ev.tipo] || "#555",
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: 1,
                  minWidth: 160,
                }}
              >
                {ev.tipo}
              </span>
              <span style={{ fontSize: 12, color: "#666", flex: 1 }}>
                {JSON.stringify(ev.datos).substring(0, 80)}...
              </span>
              <span style={{ fontSize: 11, color: "#333", fontFamily: "monospace" }}>
                {ev.timestamp?.substring(11, 19)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MonkeyTab() {
  const [health, setHealth] = useState(null);
  const [log, setLog] = useState([]);
  const [loading, setLoading] = useState(false);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API}/health`);
      const data = await res.json();
      setHealth(data);
      return data;
    } catch {
      setHealth({ estado_global: "error" });
      return null;
    }
  };

  useEffect(() => { checkHealth(); }, []);

  const addLog = (msg, type = "info") => {
    setLog((prev) => [...prev, { msg, type, time: new Date().toLocaleTimeString() }]);
  };

  const testOrden = async () => {
    setLoading(true);
    addLog("Intentando crear orden con inventario caido...", "warning");
    try {
      const res = await fetch(`${API}/api/ordenes`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Auth-Token": "Bearer token-simulado-2026" },
        body: JSON.stringify({
          cliente_nombre: "Chaos Monkey",
          cliente_email: "monkey@test.com",
          items: [{ videojuego_id: "vj-001", sede: "tienda-principal", cantidad: 1 }],
        }),
      });
      const data = await res.json();
      if (res.ok) {
        addLog(`Orden creada: ${data.orden_id}`, "success");
      } else {
        addLog(`Error controlado (${res.status}): ${data.detail || JSON.stringify(data)}`, "error");
      }
    } catch (e) {
      addLog("Servicio no disponible: " + e.message, "error");
    }
    setLoading(false);
  };

  const testCatalogo = async () => {
    addLog("Probando catalogo...", "info");
    try {
      const res = await fetch(`${API}/api/videojuegos`);
      const data = await res.json();
      addLog(`Catalogo respondio OK: ${data.length} juegos`, "success");
    } catch {
      addLog("Catalogo no disponible", "error");
    }
  };

  const runFullTest = async () => {
    setLog([]);
    addLog("=== INICIO TEST DEL MONO ===", "warning");

    addLog("1. Verificando health de todos los servicios...", "info");
    const h = await checkHealth();
    if (h) addLog(`Estado global: ${h.estado_global}`, h.estado_global === "saludable" ? "success" : "error");

    addLog("2. Probando crear orden...", "info");
    await testOrden();

    addLog("3. Probando catalogo independiente...", "info");
    await testCatalogo();

    addLog("4. Verificando health final...", "info");
    await checkHealth();

    addLog("=== FIN TEST DEL MONO ===", "warning");
  };

  const logColors = { info: "#448aff", success: "#00e676", error: "#ff1744", warning: "#e8c840" };

  return (
    <div>
      <h2 style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: 28, letterSpacing: 3, color: "#ff1744", marginBottom: 8 }}>
        CHAOS MONKEY — TEST DE RESILIENCIA
      </h2>
      <div style={{ fontSize: 12, color: "#555", marginBottom: 20 }}>
        Ejecuta docker stop servicio-inventario en tu terminal, luego presiona el boton para probar la resiliencia
      </div>

      {health && (
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          {["catalogo", "inventario", "ordenes"].map((s) => {
            const st = health[s] || health.servicios?.[s];
            const ok = st?.estado === "saludable" || st?.estado === "ok" || st?.status === "ok";
            return (
              <div key={s} style={{ flex: 1, background: "#111118", border: `1px solid ${ok ? "#1e1e2e" : "#ff1744"}`, padding: "12px 16px", textAlign: "center" }}>
                <StatusDot ok={ok} />
                <span style={{ marginLeft: 8, fontSize: 13, color: ok ? "#888" : "#ff1744", textTransform: "uppercase", letterSpacing: 1 }}>{s}</span>
              </div>
            );
          })}
        </div>
      )}

      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        <button
          onClick={runFullTest}
          style={{ flex: 1, padding: "12px", background: "#ff1744", color: "#fff", border: "none", fontFamily: "'Bebas Neue', sans-serif", fontSize: 16, letterSpacing: 3, cursor: "pointer" }}
        >
          EJECUTAR TEST COMPLETO
        </button>
        <button
          onClick={checkHealth}
          style={{ padding: "12px 24px", background: "transparent", border: "1px solid #1e1e2e", color: "#888", fontFamily: "'Bebas Neue', sans-serif", fontSize: 16, letterSpacing: 2, cursor: "pointer" }}
        >
          REFRESH HEALTH
        </button>
      </div>

      <div style={{ background: "#0a0a0f", border: "1px solid #1e1e2e", padding: 16, minHeight: 200, fontFamily: "monospace", fontSize: 12 }}>
        <div style={{ color: "#444", marginBottom: 8 }}>--- TERMINAL ---</div>
        {log.length === 0 ? (
          <div style={{ color: "#333" }}>Esperando comandos...</div>
        ) : (
          log.map((l, i) => (
            <div key={i} style={{ color: logColors[l.type], marginBottom: 4 }}>
              <span style={{ color: "#333" }}>[{l.time}]</span> {l.msg}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("catalogo");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const onlineCount = health
    ? ["catalogo", "inventario", "ordenes"].filter((s) => {
        const st = health[s] || health.servicios?.[s];
        return st?.estado === "saludable" || st?.estado === "ok" || st?.status === "ok";
      }).length + 1
    : 0;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0a0a0f",
        color: "#e0ddd4",
        fontFamily: "'Rajdhani', sans-serif",
      }}
    >
      <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet" />

      <header
        style={{
          background: "#000",
          borderBottom: "2px solid #e8c840",
          padding: "0 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: 60,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: 32, letterSpacing: 6, color: "#e8c840" }}>
            GAMEVAULT
          </div>
          <span style={{ fontSize: 11, color: "#444", letterSpacing: 2 }}>MICROSERVICES DASHBOARD</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <StatusDot ok={onlineCount === 4} />
          <span style={{ fontSize: 12, color: onlineCount === 4 ? "#00e676" : "#ff1744", letterSpacing: 1 }}>
            {onlineCount}/4 ONLINE
          </span>
        </div>
      </header>

      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #1a1a2e", background: "#0d0d14" }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: "12px 20px",
              background: "transparent",
              border: "none",
              borderBottom: tab === t.id ? "2px solid #e8c840" : "2px solid transparent",
              color: t.id === "monkey" ? (tab === t.id ? "#ff1744" : "#662222") : tab === t.id ? "#e8c840" : "#555",
              fontSize: 12,
              letterSpacing: 2,
              cursor: "pointer",
              fontFamily: "'Rajdhani', sans-serif",
              fontWeight: 700,
              transition: "color 0.2s",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #1a1a2e" }}>
        <ServiceCard name="Gateway" port="8080" status={health ? "saludable" : "error"} />
        <ServiceCard name="Catalogo" port="8001" status={health?.catalogo?.estado || health?.servicios?.catalogo?.estado || "error"} />
        <ServiceCard name="Inventario" port="8002" status={health?.inventario?.estado || health?.servicios?.inventario?.estado || "error"} />
        <ServiceCard name="Ordenes" port="8003" status={health?.ordenes?.estado || health?.servicios?.ordenes?.estado || "error"} />
      </div>

      <main style={{ padding: "24px 24px 40px" }}>
        {tab === "catalogo" && <CatalogoTab />}
        {tab === "inventario" && <InventarioTab />}
        {tab === "orden" && <OrdenTab />}
        {tab === "eventos" && <EventosTab />}
        {tab === "monkey" && <MonkeyTab />}
      </main>

      <footer
        style={{
          background: "#000",
          borderTop: "1px solid #1a1a2e",
          padding: "12px 24px",
          display: "flex",
          justifyContent: "space-between",
          fontSize: 11,
          color: "#333",
          letterSpacing: 1,
          textTransform: "uppercase",
        }}
      >
        <span>API Gateway: localhost:8080</span>
        <span>Timeout: 5s | Database per Service: SQLite</span>
        <span>UNAB 2026 — Miguel Angel Solano Diaz</span>
      </footer>
    </div>
  );
}
