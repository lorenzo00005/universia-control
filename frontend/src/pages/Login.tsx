import { FormEvent, useState } from "react";
import { api, setToken } from "../api";
import { OrbitMark } from "../components";
import type { User } from "../types";

export default function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setToken(await api.login(email, password));
      onLogin(await api.me());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      <section className="login-art" aria-hidden="true">
        <div className="orbits">
          <i /><i /><i />
          <b style={{ ["--hue" as string]: 262 }} />
          <b style={{ ["--hue" as string]: 330 }} />
          <b style={{ ["--hue" as string]: 190 }} />
          <b style={{ ["--hue" as string]: 40 }} />
        </div>
        <p>Cada número en su órbita.<br />Todas las conversaciones, en un solo lugar.</p>
      </section>
      <section className="login-form-wrap">
        <form className="login" onSubmit={submit}>
          <span className="login-mark"><OrbitMark size={36} /></span>
          <h1>Universia Control</h1>
          <p className="muted">Entrá para atender los chats de todos tus números.</p>
          <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus autoComplete="username" /></label>
          <label>Contraseña<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" /></label>
          {error && <div className="error" role="alert">{error}</div>}
          <button className="primary" disabled={busy}>{busy ? "Entrando…" : "Entrar"}</button>
        </form>
      </section>
    </div>
  );
}
