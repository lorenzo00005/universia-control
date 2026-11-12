import { useEffect, useRef } from "react";
import { getToken } from "../api";
import type { RealtimeEvent } from "../types";

/** WebSocket con reconexión automática. El callback siempre ve el estado más reciente. */
export function useRealtime(onEvent: (event: RealtimeEvent) => void) {
  const handler = useRef(onEvent);
  handler.current = onEvent;

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retry = 0;
    let timer: number | undefined;
    let closed = false;

    const connect = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${proto}://${location.host}/ws?token=${getToken() ?? ""}`);
      socket.onopen = () => (retry = 0);
      socket.onmessage = (e) => {
        try {
          handler.current(JSON.parse(e.data) as RealtimeEvent);
        } catch {
          /* mensaje inválido: se ignora */
        }
      };
      socket.onclose = () => {
        if (closed) return;
        retry += 1;
        timer = window.setTimeout(connect, Math.min(1000 * 2 ** retry, 15000));
      };
    };
    connect();

    return () => {
      closed = true;
      window.clearTimeout(timer);
      socket?.close();
    };
  }, []);
}
