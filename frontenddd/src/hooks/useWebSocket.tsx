
import { useEffect, useRef, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';

interface WebSocketMessage {
  type: string;
  data: any;
}

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const ws = useRef<WebSocket | null>(null);
  const { isAuthenticated, user } = useAuth();
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!isAuthenticated || !user) return;

    const connectWebSocket = () => {
      try {
        // WebSocket ulanishida token yuborish
        const token = localStorage.getItem('access_token');
        if (!token) {
          console.log('WebSocket: No token available');
          return;
        }

        ws.current = new WebSocket(`ws://127.0.0.1:8000/ws?token=${token}`);
        
        ws.current.onopen = () => {
          console.log('WebSocket connected');
          setIsConnected(true);
          // Reconnect timeout ni tozalash
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
          }
        };

        ws.current.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            setMessages(prev => [...prev.slice(-9), message]); // Faqat oxirgi 10 ta xabarni saqlash
            console.log('WebSocket message received:', message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        ws.current.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason);
          setIsConnected(false);
          
          // Faqat authentikatsiya mavjud bo'lsa qayta ulanishga harakat qilish
          if (isAuthenticated && event.code !== 1000) {
            reconnectTimeoutRef.current = setTimeout(() => {
              console.log('Attempting to reconnect WebSocket...');
              connectWebSocket();
            }, 5000);
          }
        };

        ws.current.onerror = (error) => {
          console.error('WebSocket error:', error);
          setIsConnected(false);
        };
      } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        setIsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (ws.current) {
        ws.current.close(1000, 'Component unmounting');
      }
    };
  }, [isAuthenticated, user]);

  const sendMessage = (message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  };

  return {
    isConnected,
    messages,
    sendMessage,
    clearMessages: () => setMessages([])
  };
};
