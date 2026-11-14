import { useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";
import Chat from "./pages/Chat";
import Login from "./pages/Login";
import Numbers from "./pages/Numbers";
import Pipeline from "./pages/Pipeline";
import type { User } from "./types";

type Tab = "chat" | "pipeline" | "numbers";

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

  return (
    <div className="app">
      <header className="topbar">
        <strong className="brand">Universia Control</strong>
        <nav>
          {(["chat", "pipeline", "numbers"] as Tab[]).map((t) => (
            <button key={t} className={tab === t ? "tab active" : "tab"} onClick={() => setTab(t)}>
              {{ chat: "Chat", pipeline: "Pipeline", numbers: "Números" }[t]}
            </button>
          ))}
        </nav>
        <span className="spacer" />
        <span className="muted">{user.name}</span>
        <button
          className="ghost"
          onClick={() => {
            setToken(null);
            setUser(null);
          }}
        >
          Salir
        </button>
      </header>
      <main>
        {tab === "chat" && <Chat user={user} initialConversationId={openConversation} />}
        {tab === "pipeline" && <Pipeline onOpenChat={goToChat} />}
        {tab === "numbers" && <Numbers user={user} />}
      </main>
    </div>
  );
}
