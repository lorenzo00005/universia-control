import type { Conversation, Message, Stage, User, WaNumber } from "./types";

const TOKEN_KEY = "rcm_token";
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token: string | null) =>
  token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY);

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function failure(res: Response): Promise<ApiError> {
  let detail = res.statusText;
  try {
    const body = await res.json();
    detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {
    /* sin cuerpo JSON */
  }
  return new ApiError(res.status, detail);
}

function authHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return headers;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = authHeaders(init.headers);
  if (typeof init.body === "string") headers.set("Content-Type", "application/json");
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401 && path !== "/auth/login") {
    setToken(null);
    window.dispatchEvent(new Event("rcm-logout"));
  }
  if (!res.ok) throw await failure(res);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const json = (body: unknown) => ({ body: JSON.stringify(body) });

export const api = {
  async login(email: string, password: string): Promise<string> {
    const res = await fetch("/auth/login", {
      method: "POST",
      body: new URLSearchParams({ username: email, password }),
    });
    if (!res.ok) throw await failure(res);
    return (await res.json()).access_token as string;
  },
  me: () => request<User>("/auth/me"),
  users: () => request<User[]>("/users"),

  numbers: () => request<WaNumber[]>("/numbers"),
  syncNumbers: () => request<WaNumber[]>("/numbers/sync", { method: "POST" }),
  createNumber: (session_name: string, label: string) =>
    request<WaNumber>("/numbers", { method: "POST", ...json({ session_name, label }) }),
  numberStatus: (id: number) => request<WaNumber>(`/numbers/${id}/status`),
  restartNumber: (id: number) => request<void>(`/numbers/${id}/restart`, { method: "POST" }),
  deleteNumber: (id: number) => request<void>(`/numbers/${id}`, { method: "DELETE" }),
  async qr(id: number): Promise<string> {
    const res = await fetch(`/numbers/${id}/qr`, { headers: authHeaders() });
    if (!res.ok) throw await failure(res);
    return URL.createObjectURL(await res.blob());
  },

  stages: () => request<Stage[]>("/stages"),
  conversations: (params: Record<string, string | number | undefined> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && query.set(k, String(v)));
    return request<Conversation[]>(`/conversations?${query}`);
  },
  messages: (id: number) => request<Message[]>(`/conversations/${id}/messages`),
  markRead: (id: number) => request<void>(`/conversations/${id}/read`, { method: "POST" }),
  sendMessage: (id: number, text: string) =>
    request<Message>(`/conversations/${id}/messages`, { method: "POST", ...json({ text }) }),
  updateConversation: (id: number, changes: Partial<Pick<Conversation, "stage_id" | "assigned_to" | "status">>) =>
    request<Conversation>(`/conversations/${id}`, { method: "PATCH", ...json(changes) }),
  // Marca el chat como venta, lo pasa a "Ganado" y envía Purchase a Meta (segundo plano)
  markSale: (id: number, value: number | null) =>
    request<Conversation>(`/conversations/${id}/sale`, { method: "POST", ...json({ value }) }),
};
