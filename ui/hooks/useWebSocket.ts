import { useEffect, useRef, useState } from 'react';

interface WebSocketOptions {
  url: string;
  onMessage: (data: any) => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
}

export function useWebSocket({ url, onMessage, onError, reconnectInterval = 3000 }: WebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    let shouldReconnect = true;

    const connect = () => {
      try {
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('[WS] Connected to', url);
          setIsConnected(true);
          setError(null);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            onMessage(data);
          } catch (err) {
            console.error('[WS] Failed to parse message:', err);
          }
        };

        ws.onerror = (event) => {
          console.error('[WS] Error:', event);
          setError('WebSocket连接错误');
          onError?.(event);
        };

        ws.onclose = () => {
          console.log('[WS] Disconnected');
          setIsConnected(false);
          wsRef.current = null;

          // Auto-reconnect
          if (shouldReconnect) {
            reconnectTimeoutRef.current = setTimeout(() => {
              console.log('[WS] Attempting to reconnect...');
              connect();
            }, reconnectInterval);
          }
        };
      } catch (err) {
        console.error('[WS] Connection failed:', err);
        setError('WebSocket连接失败');

        // Retry connection
        if (shouldReconnect) {
          reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval);
        }
      }
    };

    connect();

    // Cleanup
    return () => {
      shouldReconnect = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url, onMessage, onError, reconnectInterval]);

  return { isConnected, error };
}
