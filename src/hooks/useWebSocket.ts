import { useEffect, useRef } from "react";

type Options = {
  onMessage: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  reconnectInterval?: number;
};

export function useWebSocket(path = "/ws", options: Options) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number>(0);

  useEffect(() => {
    let mounted = true;
    let retry = 0;

    function connect() {
      const token = localStorage.getItem("token");
      if (!token) return;
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const host = process.env.REACT_APP_WS_HOST || window.location.host;
      const url = `${protocol}://${host}${path}?token=${token}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        retry = 0;
        options.onOpen?.();
      };

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          options.onMessage(data);
        } catch (e) {
          options.onMessage(ev.data);
        }
      };

      ws.onclose = () => {
        options.onClose?.();
        if (!mounted) return;
        // exponential backoff
        retry = Math.min(5, retry + 1);
        const wait = Math.pow(2, retry) * 1000;
        reconnectRef.current = window.setTimeout(connect, wait);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      mounted = false;
      if (reconnectRef.current) window.clearTimeout(reconnectRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return wsRef;
}
