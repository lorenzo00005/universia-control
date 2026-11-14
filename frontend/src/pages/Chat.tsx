import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useRealtime } from "../hooks/useRealtime";
import type { Conversation, Message, Stage, User, WaNumber } from "../types";
import { contactName, formatTime } from "../util";

function Ticks({ ack }: { ack: number }) {
  if (ack < 1) return <span className="ticks">…</span>;
  return <span className={ack >= 3 ? "ticks read" : "ticks"}>{ack >= 2 ? "✓✓" : "✓"}</span>;
}

export default function Chat({ user, initialConversationId }: { user: User; initialConversationId: number | null }) {
  const [numbers, setNumbers] = useState<WaNumber[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [numberFilter, setNumberFilter] = useState<number | "">("");
  const [onlyMine, setOnlyMine] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(initialConversationId);
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const selectedRef = useRef(selectedId);
  selectedRef.current = selectedId;
  const filterRef = useRef(numberFilter);
  filterRef.current = numberFilter;

  useEffect(() => {
    api.numbers().then(setNumbers).catch(() => undefined);
    api.stages().then(setStages).catch(() => undefined);
    api.users().then(setUsers).catch(() => undefined);
  }, []);

  const loadConversations = useCallback(() => {
    api
      .conversations({ number_id: numberFilter === "" ? undefined : numberFilter, assigned_to: onlyMine ? user.id : undefined })
      .then(setConversations)
      .catch((e) => setError(e.message));
  }, [numberFilter, onlyMine, user.id]);

  useEffect(loadConversations, [loadConversations]);

  useEffect(() => {
    if (selectedId === null) {
      setMessages([]);
      return;
    }
    api.messages(selectedId).then(setMessages).catch((e) => setError(e.message));
    api.markRead(selectedId).catch(() => undefined);
    setConversations((prev) => prev.map((c) => (c.id === selectedId ? { ...c, unread_count: 0 } : c)));
  }, [selectedId]);

  useEffect(() => {
    // Bloque sin return: scrollIntoView puede devolver una Promise y React la tomaría como función de limpieza.
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useRealtime((event) => {
    if (event.type === "message") {
      const conv = event.conversation;
      const filter = filterRef.current;
      if (filter === "" || conv.number_id === filter) {
        const isOpen = selectedRef.current === conv.id;
        const updated = isOpen ? { ...conv, unread_count: 0 } : conv;
        setConversations((prev) => [updated, ...prev.filter((c) => c.id !== conv.id)]);
      }
      if (selectedRef.current === conv.id) {
        setMessages((prev) => (prev.some((m) => m.id === event.message.id) ? prev : [...prev, event.message]));
        if (event.message.direction === "in") api.markRead(conv.id).catch(() => undefined);
      }
    } else if (event.type === "conversation") {
      setConversations((prev) => prev.map((c) => (c.id === event.conversation.id ? event.conversation : c)));
    } else if (event.type === "session") {
      setNumbers((prev) => prev.map((n) => (n.id === event.number_id ? { ...n, status: event.status } : n)));
    } else if (event.type === "ack") {
      setMessages((prev) => prev.map((m) => (m.id === event.message_id ? { ...m, ack: event.ack } : m)));
    }
  });

  const selected = conversations.find((c) => c.id === selectedId) ?? null;
  const numberOf = (c: Conversation) => numbers.find((n) => n.id === c.number_id);
  const selectedNumber = selected ? numberOf(selected) : undefined;

  const send = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected || !text.trim()) return;
    setSending(true);
    setError("");
    try {
      const message = await api.sendMessage(selected.id, text.trim());
      setMessages((prev) => (prev.some((m) => m.id === message.id) ? prev : [...prev, message]));
      setText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo enviar");
    } finally {
      setSending(false);
    }
  };

  const [saleValue, setSaleValue] = useState("");
  const [saleNote, setSaleNote] = useState("");

  const markSale = () => {
    if (!selected) return;
    const value = saleValue.trim() === "" ? null : Number(saleValue.replace(",", "."));
    if (value !== null && (Number.isNaN(value) || value < 0)) {
      setError("El monto no es válido");
      return;
    }
    api
      .markSale(selected.id, value)
      .then((c) => {
        setConversations((prev) => prev.map((x) => (x.id === c.id ? c : x)));
        setSaleValue("");
        setSaleNote("Venta registrada y enviada a Meta.");
      })
      .catch((err) => setError(err.message));
  };

  const change = (changes: Parameters<typeof api.updateConversation>[1]) => {
    if (!selected) return;
    api
      .updateConversation(selected.id, changes)
      .then((c) => setConversations((prev) => prev.map((x) => (x.id === c.id ? c : x))))
      .catch((err) => setError(err.message));
  };

  return (
    <div className="chat">
      <aside className="list">
        <div className="filters">
          <select value={numberFilter} onChange={(e) => setNumberFilter(e.target.value === "" ? "" : Number(e.target.value))}>
            <option value="">Todos los números</option>
            {numbers.filter((n) => n.status !== "DELETED").map((n) => (
              <option key={n.id} value={n.id}>{n.label}</option>
            ))}
          </select>
          <label className="check">
            <input type="checkbox" checked={onlyMine} onChange={(e) => setOnlyMine(e.target.checked)} /> Solo mías
          </label>
        </div>
        <div className="items">
          {conversations.length === 0 && <p className="muted pad">Sin conversaciones todavía.</p>}
          {conversations.map((c) => (
            <button key={c.id} className={c.id === selectedId ? "item active" : "item"} onClick={() => setSelectedId(c.id)}>
              <div className="row">
                <strong>{contactName(c.contact)}</strong>
                <span className="muted small">{formatTime(c.last_message_at)}</span>
              </div>
              <div className="row">
                <span className="preview">{c.last_message_preview}</span>
                {c.unread_count > 0 && <span className="badge">{c.unread_count}</span>}
              </div>
              <span className="tag">{numberOf(c)?.label ?? "—"}</span>
            </button>
          ))}
        </div>
      </aside>

      <section className="thread">
        {!selected ? (
          <div className="center muted">Elegí una conversación</div>
        ) : (
          <>
            <div className="thread-head">
              <strong>{contactName(selected.contact)}</strong>
              <span className="muted small">{selected.contact.phone ? `+${selected.contact.phone}` : selected.contact.chat_id} · vía {selectedNumber?.label}</span>
            </div>
            <div className="messages">
              {messages.map((m) => (
                <div key={m.id} className={m.direction === "out" ? "bubble out" : "bubble in"}>
                  {m.body || (m.has_media ? "[archivo adjunto]" : "")}
                  <span className="meta">
                    {formatTime(m.created_at)} {m.direction === "out" && <Ticks ack={m.ack} />}
                  </span>
                </div>
              ))}
              <div ref={bottom} />
            </div>
            {error && <div className="error pad">{error}</div>}
            {selectedNumber && selectedNumber.status !== "WORKING" && (
              <div className="warn pad">Este número no está conectado ({selectedNumber.status}). No se puede responder hasta reconectarlo en “Números”.</div>
            )}
            <form className="composer" onSubmit={send}>
              <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Escribí un mensaje…" disabled={sending} />
              <button className="primary" disabled={sending || !text.trim()}>Enviar</button>
            </form>
          </>
        )}
      </section>

      <aside className="details">
        {selected && (
          <>
            <h3>Cliente</h3>
            <p>{contactName(selected.contact)}</p>
            <label>Etapa</label>
            <select value={selected.stage_id ?? ""} onChange={(e) => change({ stage_id: e.target.value === "" ? null : Number(e.target.value) })}>
              <option value="">Sin etapa</option>
              {stages.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <label>Asignado a</label>
            <select value={selected.assigned_to ?? ""} onChange={(e) => change({ assigned_to: e.target.value === "" ? null : Number(e.target.value) })}>
              <option value="">Sin asignar</option>
              {users.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
            {selected.campaign && (
              <>
                <label>Campaña</label>
                <p className="small">{selected.campaign}</p>
              </>
            )}
            <label>Venta</label>
            <input
              type="text"
              inputMode="decimal"
              placeholder="Monto (opcional)"
              value={saleValue}
              onChange={(e) => { setSaleValue(e.target.value); setSaleNote(""); }}
            />
            <button onClick={markSale}>Marcar como venta</button>
            {saleNote && <p className="muted small">{saleNote}</p>}
            <label>Estado</label>
            <button className="ghost" onClick={() => change({ status: selected.status === "open" ? "closed" : "open" })}>
              {selected.status === "open" ? "Cerrar conversación" : "Reabrir conversación"}
            </button>
          </>
        )}
      </aside>
    </div>
  );
}
