import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Chat from "./pages/Chat";

const contact = { id: 1, chat_id: "111111111111111@lid", name: "Cliente", phone: null };
const conversation = {
  id: 1, number_id: 1, contact, stage_id: 1, assigned_to: null, status: "open", unread_count: 1,
  last_message_at: "2026-11-12T21:33:00Z", last_message_preview: "Hola",
  first_inbound_at: "2026-11-12T21:33:00Z", first_response_at: null,
};
const inMsg = { id: 1, conversation_id: 1, direction: "in", body: "Hola", has_media: false, ack: 0, sent_by: null, created_at: "2026-11-12T21:33:00Z" };
const outMsg = { id: 2, conversation_id: 1, direction: "out", body: "hola como estas", has_media: false, ack: 0, sent_by: 1, created_at: "2026-11-12T21:38:00Z" };

class FakeSocket {
  static last: FakeSocket;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  constructor() { FakeSocket.last = this; }
  close() {}
  emit(event: unknown) { this.onmessage?.({ data: JSON.stringify(event) }); }
}

const routes: Record<string, unknown> = {
  "GET /numbers": [{ id: 1, session_name: "sesion1", label: "sesion1", phone: "549", provider: "waha", status: "WORKING", status_changed_at: "2026-11-12T21:00:00Z" }],
  "GET /stages": [{ id: 1, name: "Nuevo", position: 0, is_won: false, is_lost: false }],
  "GET /users": [{ id: 1, email: "a@a", name: "Admin", role: "admin" }],
  "GET /conversations?": [conversation],
  "GET /conversations/1/messages": [inMsg],
  "POST /conversations/1/read": null,
  "POST /conversations/1/messages": outMsg,
};

beforeEach(() => {
  vi.stubGlobal("WebSocket", FakeSocket);
  // Chrome reciente devuelve una Promise desde scrollIntoView: el test lo imita
  Element.prototype.scrollIntoView = vi.fn(() => Promise.resolve()) as unknown as typeof Element.prototype.scrollIntoView;
  vi.stubGlobal("fetch", vi.fn(async (path: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${path}`;
    const hit = key in routes ? routes[key] : undefined;
    if (hit === undefined) return new Response(JSON.stringify({ detail: `sin mock: ${key}` }), { status: 404 });
    return hit === null ? new Response(null, { status: 204 }) : new Response(JSON.stringify(hit), { status: 200 });
  }));
});

describe("Chat", () => {
  it("sobrevive a enviar un mensaje y a los eventos en tiempo real posteriores", async () => {
    const errors: unknown[] = [];
    const onError = (e: ErrorEvent) => errors.push(e.error);
    window.addEventListener("error", onError);

    render(<Chat user={{ id: 1, email: "a@a", name: "Admin", role: "admin" }} initialConversationId={null} />);
    fireEvent.click(await screen.findByText("Cliente"));
    await screen.findByText("Hola", { selector: ".bubble" });

    fireEvent.change(screen.getByPlaceholderText("Escribí un mensaje…"), { target: { value: "hola como estas" } });
    fireEvent.click(screen.getByText("Enviar"));
    await screen.findByText(/hola como estas/);

    const rt = (event: unknown) => act(() => FakeSocket.last.emit(event));
    const out = { ...conversation, unread_count: 0, last_message_preview: "hola como estas" };
    rt({ type: "message", conversation: out, message: outMsg });
    rt({ type: "ack", message_id: 2, ack: 2 });
    rt({ type: "ack", message_id: 2, ack: 3 });
    rt({ type: "conversation", conversation: out });
    rt({ type: "message", conversation: out, message: { ...outMsg, id: 3 } });

    await waitFor(() => expect(screen.getAllByText(/hola como estas/).length).toBeGreaterThan(0));
    window.removeEventListener("error", onError);
    expect(errors).toEqual([]);
  });
});
