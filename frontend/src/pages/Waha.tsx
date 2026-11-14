import { useEffect, useState } from "react";
import { api } from "../api";

/** Dashboard de WAHA dentro del panel: las sesiones y el CRM se manejan desde el mismo lugar. */
export default function Waha() {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.systemInfo().then((info) => setUrl(info.waha_dashboard_url)).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="page"><p className="error">{error}</p></div>;
  if (!url) return <div className="center muted">Cargando…</div>;

  return (
    <div className="waha-page">
      <div className="waha-bar">
        <strong>Panel de WAHA</strong>
        <span className="muted">Sesiones, QR, API y logs. Ingresá con el usuario y la clave del dashboard de tu .env.</span>
        <a className="btn-link" href={url} target="_blank" rel="noreferrer">Abrir en otra pestaña</a>
      </div>
      <iframe className="waha-frame" title="Panel de WAHA" src={url} />
    </div>
  );
}
