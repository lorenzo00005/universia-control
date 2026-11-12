export interface User { id: number; email: string; name: string; role: string }
export interface WaNumber {
  id: number; session_name: string; label: string; phone: string | null;
  provider: string; status: string; status_changed_at: string;
}
export interface Stage { id: number; name: string; position: number; is_won: boolean; is_lost: boolean }
export interface Contact { id: number; chat_id: string; name: string | null; phone: string | null }
export interface Conversation {
  id: number; number_id: number; contact: Contact; stage_id: number | null;
  assigned_to: number | null; status: string; unread_count: number;
  last_message_at: string | null; last_message_preview: string | null;
  first_inbound_at: string | null; first_response_at: string | null;
}
export interface Message {
  id: number; conversation_id: number; direction: "in" | "out"; body: string;
  has_media: boolean; ack: number; sent_by: number | null; created_at: string;
}
export type RealtimeEvent =
  | { type: "message"; conversation: Conversation; message: Message }
  | { type: "conversation"; conversation: Conversation }
  | { type: "session"; number_id: number; status: string }
  | { type: "ack"; message_id: number; ack: number };
