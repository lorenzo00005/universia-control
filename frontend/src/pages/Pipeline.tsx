import { useEffect, useState } from "react";
import { api } from "../api";
import { useRealtime } from "../hooks/useRealtime";
import type { Conversation, Stage, WaNumber } from "../types";
import { contactName } from "../util";

export default function Pipeline({ onOpenChat }: { onOpenChat: (conversationId: number) => void }) {
  const [stages, setStages] = useState<Stage[]>([]);
  const [numbers, setNumbers] = useState<WaNumber[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [dragging, setDragging] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.stages().then(setStages).catch((e) => setError(e.message));
    api.numbers().then(setNumbers).catch(() => undefined);
    api.conversations({ limit: 200 }).then(setConversations).catch((e) => setError(e.message));
  }, []);

  useRealtime((event) => {
    if (event.type === "message" || event.type === "conversation") {
      const conv = event.conversation;
      setConversations((prev) => (prev.some((c) => c.id === conv.id) ? prev.map((c) => (c.id === conv.id ? conv : c)) : [conv, ...prev]));
    }
  });

  const move = async (conversationId: number, stageId: number | null) => {
    const previous = conversations;
    setConversations((prev) => prev.map((c) => (c.id === conversationId ? { ...c, stage_id: stageId } : c)));
    try {
      await api.updateConversation(conversationId, { stage_id: stageId });
    } catch (err) {
      setConversations(previous);
      setError(err instanceof Error ? err.message : "No se pudo mover");
    }
  };

  const columns: { id: number | null; name: string; tone: string }[] = [
    ...stages.map((s) => ({ id: s.id as number | null, name: s.name, tone: s.is_won ? "won" : s.is_lost ? "lost" : "" })),
    ...(conversations.some((c) => c.stage_id === null) ? [{ id: null, name: "Sin etapa", tone: "" }] : []),
  ];

  return (
    <div className="page wide">
      <h2>Pipeline de ventas</h2>
      {error && <div className="error">{error}</div>}
      <div className="kanban">
        {columns.map((col) => {
          const items = conversations.filter((c) => c.stage_id === col.id);
          return (
            <div
              key={col.id ?? "none"}
              className={`column ${col.tone}`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => dragging !== null && move(dragging, col.id)}
            >
              <div className="column-head">
                <strong>{col.name}</strong>
                <span className="badge muted-badge">{items.length}</span>
              </div>
              {items.map((c) => (
                <div key={c.id} className="kcard" draggable onDragStart={() => setDragging(c.id)} onDragEnd={() => setDragging(null)} onClick={() => onOpenChat(c.id)}>
                  <strong>{contactName(c.contact)}</strong>
                  <span className="preview">{c.last_message_preview}</span>
                  <span className="tag">{numbers.find((n) => n.id === c.number_id)?.label ?? "—"}</span>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
