import React, { createContext, useEffect, useRef } from 'react';
import useRealtimeStore from '../store/useRealtimeStore';
import useFindingsStore from '../store/useFindingsStore';

export const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children }) => {
  const ws = useRef(null);
  const setConnected = useRealtimeStore((s) => s.setConnected);
  const addAlert = useRealtimeStore((s) => s.addAlert);
  const addEvent = useRealtimeStore((s) => s.addEvent);
  const addFinding = useFindingsStore((s) => s.addFinding);
  
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    const orgId = localStorage.getItem('org_id');
    
    let reconnectDelay = 2000;
    let reconnectTimeout = null;
    
    if (!token || !orgId) return;

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//localhost:8000/api/ws?token=${token}&org=${orgId}`;
      
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setConnected(true);
        reconnectDelay = 2000; // Reset backoff on successful connection
        console.log('[WebSocket] Connection open, synchronization layer active');
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Trace correlation logs
          if (data.correlation_id) {
            console.debug(`[WebSocket] Trace: ${data.correlation_id} Event: ${data.type}`);
          }
          
          if (data.type === 'CRITICAL_ALERT') {
            addAlert(data.data);
          } else if (data.type === 'FINDING_UPDATE') {
            addFinding(data.data);
          } else if (data.type === 'SCAN_UPDATE') {
            // Forward live scan indicators to UI
            console.debug('Scan update received:', data.data);
          }
          
          addEvent(data);
        } catch (e) {
          console.error('Error parsing websocket message', e);
        }
      };

      ws.current.onclose = () => {
        setConnected(false);
        console.log(`[WebSocket] Connection closed. Retrying in ${reconnectDelay / 1000}s...`);
        reconnectTimeout = setTimeout(() => {
          reconnectDelay = Math.min(30000, reconnectDelay * 1.5);
          connect();
        }, reconnectDelay);
      };
    };

    connect();

    return () => {
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [setConnected, addAlert, addEvent, addFinding]);

  return (
    <WebSocketContext.Provider value={ws.current}>
      {children}
    </WebSocketContext.Provider>
  );
};

