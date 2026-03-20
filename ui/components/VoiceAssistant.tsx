import React, { useState, useEffect, useRef, useCallback } from 'react';
import { getAssistantWebSocketURL } from '../api';

// ============================================================
// 语音助手状态类型
// ============================================================
type AssistantState = 
  | 'idle'           // 未激活
  | 'wake'           // 唤醒（显示弹窗）
  | 'user_speaking'  // 用户说话中（慢速脉冲）
  | 'thinking'       // 助手思考中（活跃波形）
  | 'reply'          // 助手回复中（活跃波形 + 显示文字）
  | 'reply_done';    // 回复完毕（等待下一轮）

// WebSocket 消息类型
interface AssistantMessage {
  type: 'wake' | 'user_speaking' | 'thinking' | 'reply' | 'reply_done' | 'close';
  text?: string;
}

// ============================================================
// Siri 风格呼吸圆圈组件
// ============================================================
const SiriOrb: React.FC<{ state: AssistantState }> = ({ state }) => {
  // 根据状态决定动画速度
  const isActive = state === 'thinking' || state === 'reply';
  const isListening = state === 'user_speaking' || state === 'wake' || state === 'reply_done';
  
  return (
    <div className="relative w-24 h-24 flex items-center justify-center">
      {/* 外层光晕 */}
      <div 
        className={`absolute inset-0 rounded-full blur-xl opacity-60 ${
          isActive ? 'animate-pulse-fast' : 'animate-pulse-slow'
        }`}
        style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #f5576c 75%, #4facfe 100%)',
        }}
      />
      
      {/* 第二层波纹 */}
      <div 
        className={`absolute w-20 h-20 rounded-full blur-lg opacity-50 ${
          isActive ? 'animate-ripple-fast' : 'animate-ripple-slow'
        }`}
        style={{
          background: 'linear-gradient(45deg, #4facfe 0%, #00f2fe 50%, #43e97b 100%)',
        }}
      />
      
      {/* 第三层波纹 */}
      <div 
        className={`absolute w-16 h-16 rounded-full blur-md opacity-70 ${
          isActive ? 'animate-ripple-fast-delay' : 'animate-ripple-slow-delay'
        }`}
        style={{
          background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 50%, #ffecd2 100%)',
        }}
      />
      
      {/* 核心圆球 */}
      <div 
        className={`relative w-12 h-12 rounded-full shadow-lg ${
          isActive ? 'animate-core-active' : 'animate-core-idle'
        }`}
        style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%)',
          boxShadow: '0 0 30px rgba(102, 126, 234, 0.6), 0 0 60px rgba(118, 75, 162, 0.4)',
        }}
      />
      
      {/* 收听状态指示器 */}
      {isListening && (
        <div className="absolute bottom-0 w-2 h-2 bg-green-400 rounded-full animate-ping" />
      )}
    </div>
  );
};

// ============================================================
// 主组件：VoiceAssistant
// ============================================================
export const VoiceAssistant: React.FC = () => {
  const [state, setState] = useState<AssistantState>('idle');
  const [replyText, setReplyText] = useState<string>('');
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  // WebSocket 消息处理
  const handleMessage = useCallback((message: AssistantMessage) => {
    console.log('[VoiceAssistant] 收到消息:', message);
    
    switch (message.type) {
      case 'wake':
        setState('wake');
        setReplyText('');
        break;
      case 'user_speaking':
        setState('user_speaking');
        break;
      case 'thinking':
        setState('thinking');
        break;
      case 'reply':
        setState('reply');
        if (message.text) {
          setReplyText(message.text);
        }
        break;
      case 'reply_done':
        setState('reply_done');
        break;
      case 'close':
        setState('idle');
        setReplyText('');
        break;
    }
  }, []);

  // WebSocket 连接
  useEffect(() => {
    let shouldReconnect = true;

    const connect = () => {
      try {
        const url = getAssistantWebSocketURL();
        console.log('[VoiceAssistant] 连接 WebSocket:', url);
        
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('[VoiceAssistant] WebSocket 已连接');
          setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as AssistantMessage;
            handleMessage(data);
          } catch (err) {
            console.error('[VoiceAssistant] 解析消息失败:', err);
          }
        };

        ws.onerror = (event) => {
          console.error('[VoiceAssistant] WebSocket 错误:', event);
        };

        ws.onclose = () => {
          console.log('[VoiceAssistant] WebSocket 断开');
          setIsConnected(false);
          wsRef.current = null;

          // 自动重连
          if (shouldReconnect) {
            reconnectTimeoutRef.current = setTimeout(() => {
              console.log('[VoiceAssistant] 尝试重连...');
              connect();
            }, 3000);
          }
        };
      } catch (err) {
        console.error('[VoiceAssistant] 连接失败:', err);
        
        // 重试连接
        if (shouldReconnect) {
          reconnectTimeoutRef.current = setTimeout(connect, 3000);
        }
      }
    };

    connect();

    // 清理
    return () => {
      shouldReconnect = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [handleMessage]);

  // 如果是 idle 状态，不显示任何内容
  if (state === 'idle') {
    return null;
  }

  // 获取状态文字提示
  const getStatusText = () => {
    switch (state) {
      case 'wake':
        return '你好，我在听...';
      case 'user_speaking':
        return '正在聆听...';
      case 'thinking':
        return '思考中...';
      case 'reply':
      case 'reply_done':
        return replyText || '';
      default:
        return '';
    }
  };

  return (
    <>
      {/* 自定义动画样式 */}
      <style>{`
        @keyframes pulse-slow {
          0%, 100% { transform: scale(1); opacity: 0.6; }
          50% { transform: scale(1.15); opacity: 0.8; }
        }
        @keyframes pulse-fast {
          0%, 100% { transform: scale(1); opacity: 0.6; }
          50% { transform: scale(1.25); opacity: 0.9; }
        }
        @keyframes ripple-slow {
          0%, 100% { transform: scale(0.9); opacity: 0.5; }
          50% { transform: scale(1.1); opacity: 0.7; }
        }
        @keyframes ripple-fast {
          0%, 100% { transform: scale(0.85); opacity: 0.5; }
          50% { transform: scale(1.2); opacity: 0.8; }
        }
        @keyframes ripple-slow-delay {
          0%, 100% { transform: scale(1); opacity: 0.7; }
          50% { transform: scale(1.15); opacity: 0.5; }
        }
        @keyframes ripple-fast-delay {
          0%, 100% { transform: scale(0.9); opacity: 0.7; }
          50% { transform: scale(1.25); opacity: 0.6; }
        }
        @keyframes core-idle {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.05); }
        }
        @keyframes core-active {
          0%, 100% { transform: scale(1); }
          25% { transform: scale(1.1); }
          50% { transform: scale(0.95); }
          75% { transform: scale(1.08); }
        }
        .animate-pulse-slow { animation: pulse-slow 3s ease-in-out infinite; }
        .animate-pulse-fast { animation: pulse-fast 0.8s ease-in-out infinite; }
        .animate-ripple-slow { animation: ripple-slow 2.5s ease-in-out infinite; }
        .animate-ripple-fast { animation: ripple-fast 0.6s ease-in-out infinite; }
        .animate-ripple-slow-delay { animation: ripple-slow-delay 2.8s ease-in-out infinite 0.3s; }
        .animate-ripple-fast-delay { animation: ripple-fast-delay 0.7s ease-in-out infinite 0.1s; }
        .animate-core-idle { animation: core-idle 2s ease-in-out infinite; }
        .animate-core-active { animation: core-active 0.5s ease-in-out infinite; }
      `}</style>

      {/* 弹窗容器 - 顶部居中，尽量不遮挡内容 */}
      <div 
        className="fixed top-4 left-1/2 -translate-x-1/2 z-50 flex flex-col items-center gap-3 p-4 rounded-2xl backdrop-blur-lg bg-black/40 border border-white/10 shadow-2xl pointer-events-none"
        style={{
          minWidth: '200px',
          maxWidth: '300px',
        }}
      >
        {/* Siri 呼吸圆圈 */}
        <SiriOrb state={state} />
        
        {/* 状态文字 */}
        <div className="text-center">
          <p className="text-white text-sm font-medium leading-relaxed">
            {getStatusText()}
          </p>
        </div>

        {/* 连接状态指示（仅开发时显示） */}
        {process.env.NODE_ENV === 'development' && (
          <div className={`text-xs ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
            {isConnected ? 'WebSocket 已连接' : 'WebSocket 未连接'}
          </div>
        )}
      </div>
    </>
  );
};

export default VoiceAssistant;
