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
    
    if (!token || !orgId) return;

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//localhost:8000/ws?token=${token}&org_id=${orgId}`;
      
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setConnected(true);
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'CRITICAL_ALERT') {
            addAlert(data.data);
          } else if (data.type === 'FINDING_UPDATE') {
            addFinding(data.data);
          }
          
          addEvent(data);
        } catch (e) {
          console.error('Error parsing websocket message', e);
        }
      };

      ws.current.onclose = () => {
        setConnected(false);
        setTimeout(connect, 5000); // Reconnect
      };
    };

    connect();

    return () => {
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
