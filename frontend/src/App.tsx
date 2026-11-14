import { useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";
import Chat from "./pages/Chat";
import Login from "./pages/Login";
import Numbers from "./pages/Numbers";
import Pipeline from "./pages/Pipeline";
import Waha from "./pages/Waha";
import { Icon, OrbitMark } from "./components";
import type { User } from "./types";

type Tab = "chat" | "pipeline" | "numbers" | "waha";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(Boolean(getToken()));
  const [tab, setTab] = useState<Tab>("chat");
  const [openConversation, setOpenConversation] = useState<number | null>(null);

  useEffect(() => {
    if (!getToken()) return;
    api.me().then(setUser).catch(() => setToken(null)).finally(() => setChecking(false));
  }, []);

  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener("rcm-logout", onLogout);
    return () => window.removeEventListener("rcm-logout", onLogout);
  }, []);

  if (checking) return <div className="center muted">Cargando…</div>;
  if (!user) return <Login onLogin={setUser} />;

  const goToChat = (conversationId: number) => {
    setOpenConversation(conversationId);
    setTab("chat");
  };

  const labels: Record<Tab, string> = { chat: "Chat", pipeline: "Pipeline", numbers: "Números", waha: "WAHA" };

  return (
    <div className="app">
      <nav className="rail" aria-label="Secciones">
        <span className="brand" title="Universia Control">
          <OrbitMark size={30} />
        </span>
        {(["chat", "pipeline", "numbers", "waha"] as Tab[]).map((t) => (
          <button key={t} className={tab === t ? "rail-tab active" : "rail-tab"} onClick={() => setTab(t)} aria-current={tab === t ? "page" : undefined}>
            <Icon name={t} />
            <span>{labels[t]}</span>
          </button>
        ))}
        <span className="spacer" />
        <span className="who" title={user.email}>{user.name}</span>
        <button
          className="rail-tab"
          onClick={() => {
            setToken(null);
            setUser(null);
          }}
        >
          <Icon name="logout" />
          <span>Salir</span>
        </button>
      </nav>
      <main>
        {tab === "chat" && <Chat user={user} initialConversationId={openConversation} />}
        {tab === "pipeline" && <Pipeline onOpenChat={goToChat} />}
        {tab === "numbers" && <Numbers user={user} />}
        {tab === "waha" && <Waha />}
      </main>
    </div>
  );
}
