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

/** Cada número tiene su propio tono, estable y distinto: se usa en lista, thread y pipeline. */
export function numberHue(id: number): number {
  return (id * 67 + 215) % 360;
}

export function initials(name: string): string {
  const parts = name.replace(/^\+/, "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const letters = parts.length === 1 ? parts[0].slice(0, 2) : parts[0][0] + parts[1][0];
  return letters.toUpperCase();
}
