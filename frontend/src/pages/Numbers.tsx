import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useRealtime } from "../hooks/useRealtime";
import type { User, WaNumber } from "../types";
import { STATUS_LABEL } from "../util";

function QrModal({ number, onClose }: { number: WaNumber; onClose: () => void }) {
  const [src, setSrc] = useState<string | null>(null);
  const [message, setMessage] = useState("Esperando el código QR…");

  useEffect(() => {
    let alive = true;
    let current: string | null = null;
    const refresh = async () => {
      try {
        const url = await api.qr(number.id);
        if (!alive) return URL.revokeObjectURL(url);
        if (current) URL.revokeObjectURL(current);
        current = url;
        setSrc(url);
      } catch (e) {
        if (alive) {
          setSrc(null);
          setMessage(e instanceof Error ? e.message : "Sin QR disponible");
        }
      }
    };
    refresh();
    const timer = window.setInterval(refresh, 8000);
    return () => {
      alive = false;
      window.clearInterval(timer);
      if (current) URL.revokeObjectURL(current);
    };
  }, [number.id]);

  useEffect(() => {
    if (number.status === "WORKING") onClose();
  }, [number.status, onClose]);

  return (
    <div className="modal-back" onClick={onClose}>
      <div className="card modal" onClick={(e) => e.stopPropagation()}>
        <h3>Vincular “{number.label}”</h3>
        {src ? <img src={src} alt="QR de WhatsApp" className="qr" /> : <p className="muted">{message}</p>}
        <p className="muted small">WhatsApp → Dispositivos vinculados → Vincular un dispositivo. El código se renueva solo.</p>
        <button className="ghost" onClick={onClose}>Cerrar</button>
      </div>
    </div>
  );
}

export default function Numbers({ user }: { user: User }) {
  const [numbers, setNumbers] = useState<WaNumber[]>([]);
  const [sessionName, setSessionName] = useState("");
  const [label, setLabel] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [qrFor, setQrFor] = useState<number | null>(null);
  const isAdmin = user.role === "admin";

  const load = useCallback(() => {
    api.numbers().then(setNumbers).catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    load();
    // Importa en silencio las sesiones que ya existan en WAHA (ej. creadas desde su dashboard)
    if (isAdmin) api.syncNumbers().then(setNumbers).catch(() => undefined);
  }, [load, isAdmin]);

  useRealtime((event) => {
    if (event.type === "session") {
      setNumbers((prev) => prev.map((n) => (n.id === event.number_id ? { ...n, status: event.status } : n)));
    }
  });

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const number = await api.createNumber(sessionName.trim(), label.trim());
      setNumbers((prev) => [...prev, number]);
      setSessionName("");
      setLabel("");
      setQrFor(number.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear la instancia");
    } finally {
      setBusy(false);
    }
  };

  const act = async (fn: () => Promise<unknown>) => {
    setError("");
    try {
      await fn();
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    }
  };

  const visible = numbers.filter((n) => n.status !== "DELETED");
  const qrNumber = visible.find((n) => n.id === qrFor);

  return (
    <div className="page">
      <h2>Números de WhatsApp</h2>
      {isAdmin && (
        <form className="card inline" onSubmit={create}>
          <input
            placeholder="Nombre de sesión (ej: ventas1)"
            value={sessionName}
            onChange={(e) => setSessionName(e.target.value.toLowerCase())}
            pattern="[a-z0-9_\-]{2,40}"
            title="2 a 40 caracteres: minúsculas, números, guion o guion bajo"
            required
          />
          <input placeholder="Etiqueta (ej: Ventas 1)" value={label} onChange={(e) => setLabel(e.target.value)} required />
          <button className="primary" disabled={busy}>{busy ? "Creando…" : "Crear instancia"}</button>
        </form>
      )}
      {error && <div className="error">{error}</div>}
      {isAdmin && (
        <button className="ghost" onClick={() => act(async () => setNumbers(await api.syncNumbers()))}>
          Importar sesiones de WAHA
        </button>
      )}

      <div className="grid">
        {visible.length === 0 && <p className="muted">Todavía no hay números. Creá la primera instancia y escaneá el QR.</p>}
        {visible.map((n) => (
          <div key={n.id} className="card number">
            <div className="row">
              <strong>{n.label}</strong>
              <span className={`status s-${n.status}`}>{STATUS_LABEL[n.status] ?? n.status}</span>
            </div>
            <span className="muted small">{n.session_name}{n.phone ? ` · +${n.phone}` : ""}</span>
            <div className="actions">
              {n.status !== "WORKING" && <button className="primary" onClick={() => setQrFor(n.id)}>Ver QR</button>}
              <button className="ghost" onClick={() => act(() => api.numberStatus(n.id))}>Actualizar estado</button>
              <button className="ghost" onClick={() => act(() => api.restartNumber(n.id))}>Reiniciar</button>
              {isAdmin && (
                <button className="danger" onClick={() => confirm(`¿Eliminar "${n.label}"?`) && act(() => api.deleteNumber(n.id))}>
                  Eliminar
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      {qrNumber && <QrModal number={qrNumber} onClose={() => setQrFor(null)} />}
    </div>
  );
}
