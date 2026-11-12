export function formatTime(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  const sameDay = date.toDateString() === new Date().toDateString();
  return sameDay
    ? date.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit" });
}

export function contactName(c: { name: string | null; phone: string | null; chat_id: string }): string {
  return c.name || (c.phone ? `+${c.phone}` : c.chat_id.split("@")[0]);
}

export const STATUS_LABEL: Record<string, string> = {
  WORKING: "Conectado",
  SCAN_QR_CODE: "Esperando QR",
  STARTING: "Iniciando",
  STOPPED: "Detenido",
  FAILED: "Caído",
  DELETED: "Eliminado",
};
