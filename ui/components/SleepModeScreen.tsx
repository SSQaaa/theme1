
import React, { useEffect, useRef, useState } from 'react';
import { AppView, NavigationProps } from '../types';
import { Background } from './Background';

// --- Icons ---
const PowerIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/></svg>
);
const CameraIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/></svg>
);
const BrainIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"/></svg>
);
const EyeIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
);

declare global {
  interface Window {
    faceapi: any;
  }
}

export const SleepModeScreen: React.FC<NavigationProps> = ({ onNavigate }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // State
  const [isModelLoaded, setIsModelLoaded] = useState(false);
  const [debugStatus, setDebugStatus] = useState('等待摄像头...');
  const [showStrategyModal, setShowStrategyModal] = useState(false);
  
  // Emotion State
  const [currentEmotion, setCurrentEmotion] = useState('检测中...');
  const [emotionConfidence, setEmotionConfidence] = useState(0);

  // 1. Initialize Face API Models
  useEffect(() => {
    const loadModels = async () => {
      setDebugStatus('正在加载 AI 模型...');
      const MODEL_URL = 'https://justadudewhohacks.github.io/face-api.js/models';
      
      try {
        if (!window.faceapi) {
            setDebugStatus('FaceAPI 未加载');
            return;
        }

        await Promise.all([
          window.faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
          window.faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL)
        ]);
        
        setIsModelLoaded(true);
        setDebugStatus('AI 模型就绪');
        startVideo();
      } catch (error) {
        console.error("Model Load Error:", error);
        setDebugStatus('AI 模型加载失败');
      }
    };

    loadModels();
  }, []);

  // 2. Start Camera
  const startVideo = async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (videoRef.current) {
            videoRef.current.srcObject = stream;
        }
    } catch (err) {
        console.error("Camera Error:", err);
        setDebugStatus('摄像头权限被拒绝');
    }
  };

  // 3. Real-time Detection Loop
  const handleVideoPlay = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    if (!video || !canvas || !isModelLoaded) return;

    // Adjust canvas to match video dimensions
    const displaySize = { width: video.videoWidth, height: video.videoHeight };
    window.faceapi.matchDimensions(canvas, displaySize);

    const interval = setInterval(async () => {
        if (video.paused || video.ended) return;

        // Detect faces and expressions
        const detections = await window.faceapi
            .detectAllFaces(video, new window.faceapi.TinyFaceDetectorOptions())
            .withFaceExpressions();

        // Clear canvas and draw
        const ctx = canvas.getContext('2d');
        if (ctx) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }

        if (detections.length > 0) {
            setDebugStatus('正在分析面部特征...');
            
            // Extract Dominant Emotion
            const expressions = detections[0].expressions;
            const keys = Object.keys(expressions);
            let maxEmotion = 'neutral';
            let maxVal = 0;

            keys.forEach(key => {
                if (expressions[key] > maxVal) {
                    maxVal = expressions[key];
                    maxEmotion = key;
                }
            });

            // Map to Chinese
            const emotionMap: Record<string, string> = {
                neutral: '平静',
                happy: '愉悦',
                sad: '悲伤',
                angry: '愤怒',
                fearful: '恐惧',
                disgusted: '厌恶',
                surprised: '惊讶'
            };
            
            setCurrentEmotion(emotionMap[maxEmotion] || '未知');
            setEmotionConfidence(maxVal);

        } else {
            setDebugStatus('寻找目标...');
            setCurrentEmotion('未检测到');
            setEmotionConfidence(0);
        }

    }, 200);

    return () => clearInterval(interval);
  };

  // Helper for Emotion Color
  const getEmotionColor = (emotion: string) => {
      switch(emotion) {
          case '愉悦': return 'text-amber-400 drop-shadow-[0_0_15px_rgba(251,191,36,0.6)]';
          case '平静': return 'text-cyan-400 drop-shadow-[0_0_15px_rgba(34,211,238,0.6)]';
          case '悲伤': return 'text-indigo-400 drop-shadow-[0_0_15px_rgba(129,140,248,0.6)]';
          case '愤怒': return 'text-red-500 drop-shadow-[0_0_15px_rgba(239,68,68,0.6)]';
          case '恐惧': return 'text-purple-500 drop-shadow-[0_0_15px_rgba(168,85,247,0.6)]';
          case '惊讶': return 'text-pink-400 drop-shadow-[0_0_15px_rgba(244,114,182,0.6)]';
          default: return 'text-slate-400';
      }
  };

  return (
    <div className="relative w-full h-screen bg-slate-950 overflow-hidden flex flex-col">
      <Background />
      
      {/* Top Header */}
      <div className="z-20 flex justify-between items-center p-6 border-b border-slate-800/50 bg-slate-900/60 backdrop-blur-md">
        <div className="flex items-center space-x-3">
            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"/>
            <span className="text-emerald-500 text-xs font-mono tracking-widest">
                SLEEP_SYS // MONITORING
            </span>
        </div>
        <button 
          onClick={() => onNavigate(AppView.WELCOME)}
          className="group flex items-center space-x-2 px-4 py-2 rounded-full border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 transition-all z-50 cursor-pointer"
        >
          <PowerIcon />
          <span className="text-xs text-red-400 font-bold tracking-widest group-hover:text-red-300">退出会话</span>
        </button>
      </div>

      <div className="flex-1 flex flex-col md:flex-row overflow-hidden relative z-10 p-4 md:p-8 gap-6">
        
        {/* LEFT: VISION MODULE VISUALIZATION */}
        <div className="flex-1 relative rounded-2xl overflow-hidden border border-slate-700 bg-black shadow-2xl group flex flex-col items-center justify-center">
             
             {/* Camera Feed */}
             <video 
                ref={videoRef}
                autoPlay 
                muted 
                playsInline
                onPlay={handleVideoPlay}
                className="absolute inset-0 w-full h-full object-cover transform -scale-x-100 opacity-80" 
             />
             
             {/* Canvas Overlay for FaceAPI */}
             <canvas 
                ref={canvasRef}
                className="absolute inset-0 w-full h-full object-cover transform -scale-x-100 pointer-events-none"
             />

             {/* UI Overlays */}
             {/* Corner Brackets */}
             <div className="absolute top-6 left-6 w-8 h-8 border-t-2 border-l-2 border-emerald-500/50 rounded-tl-lg" />
             <div className="absolute top-6 right-6 w-8 h-8 border-t-2 border-r-2 border-emerald-500/50 rounded-tr-lg" />
             <div className="absolute bottom-6 left-6 w-8 h-8 border-b-2 border-l-2 border-emerald-500/50 rounded-bl-lg" />
             <div className="absolute bottom-6 right-6 w-8 h-8 border-b-2 border-r-2 border-emerald-500/50 rounded-br-lg" />
             
             {/* Bottom Scanner Graphic */}
             <div className="absolute bottom-0 w-full flex justify-center pb-8 pointer-events-none">
                 <div className="relative">
                    <div className="w-32 h-16 border-t border-l border-r border-cyan-500/30 rounded-t-full relative overflow-hidden">
                         <div className="absolute inset-0 bg-cyan-500/5 animate-pulse" />
                         <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-full h-0.5 bg-cyan-500 shadow-[0_0_10px_#06b6d4]" />
                    </div>
                    <div className="absolute bottom-2 left-1/2 -translate-x-1/2">
                         <CameraIcon />
                    </div>
                 </div>
             </div>
            
            {/* Status Label */}
            <div className="absolute bottom-4 left-8 text-[10px] text-emerald-500 font-mono bg-black/40 px-2 py-1 rounded backdrop-blur">
                VISION_MODULE: ONLINE
            </div>
            <div className="absolute bottom-4 right-8 text-[10px] text-slate-500 font-mono">
                {debugStatus}
            </div>
        </div>

        {/* RIGHT: CONTROLS & STATUS */}
        <div className="w-full md:w-80 flex flex-col gap-4">
            
            {/* 1. RESTORED: Emotion Recognition Panel */}
            <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm shadow-lg flex flex-col items-center justify-center min-h-[160px]">
                <div className="w-full flex items-center justify-start space-x-2 border-b border-slate-800 pb-2 mb-4">
                    <EyeIcon />
                    <span className="text-xs font-bold text-slate-300 tracking-wider">视觉情绪识别</span>
                </div>
                
                <div className="flex-1 flex flex-col items-center justify-center space-y-2">
                    {/* Large, Prominent Emotion Text */}
                    <div className={`text-5xl font-bold tracking-widest transition-all duration-500 ${getEmotionColor(currentEmotion)}`}>
                        {currentEmotion}
                    </div>
                    
                    {currentEmotion !== '未检测到' && (
                        <div className="text-[10px] text-slate-500 font-mono mt-2">
                            置信度: {(emotionConfidence * 100).toFixed(0)}%
                        </div>
                    )}
                </div>
            </div>

            {/* 2. Prepare Sleep Button */}
            <div className="flex-1 flex flex-col justify-end">
                <button 
                    onClick={() => setShowStrategyModal(true)}
                    className="group relative w-full py-6 rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-700 border border-indigo-400/30 shadow-lg shadow-indigo-900/40 hover:scale-[1.02] hover:shadow-indigo-500/30 transition-all duration-300 overflow-hidden"
                >
                    <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-20 transition-opacity" />
                    <div className="flex flex-col items-center justify-center space-y-2">
                        <span className="text-3xl filter drop-shadow-[0_0_10px_rgba(255,255,255,0.5)]">💤</span>
                        <span className="text-white font-bold tracking-[0.2em] text-lg uppercase">准备睡眠</span>
                        <span className="text-[10px] text-indigo-200 font-mono">INITIATE SLEEP SEQUENCE</span>
                    </div>
                </button>
            </div>

            {/* 3. System Status */}
            <div className="p-3 bg-emerald-900/05 border border-emerald-500/10 rounded-xl">
                 <div className="text-[10px] text-emerald-600/70 font-mono leading-relaxed space-y-1">
                    <div className="flex justify-between"><span>系统:</span> <span>正常</span></div>
                    <div className="flex justify-between"><span>助眠程序:</span> <span>待命</span></div>
                    <div className="flex justify-between"><span>AI 引擎:</span> <span>{isModelLoaded ? '在线' : '加载中...'}</span></div>
                 </div>
            </div>

        </div>
      </div>

      {/* STRATEGY MODAL */}
      {showStrategyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in zoom-in duration-300">
            <div className="bg-slate-900 border border-indigo-500/30 p-8 rounded-2xl max-w-md w-full shadow-2xl relative flex flex-col items-center text-center">
                
                {/* Decoration */}
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500 to-transparent" />
                <div className="w-16 h-16 bg-indigo-500/10 rounded-full flex items-center justify-center mb-6 text-indigo-400 ring-1 ring-indigo-500/30">
                    <BrainIcon />
                </div>

                <h3 className="text-xl text-white font-light tracking-[0.1em] mb-6">
                    助眠策略生成
                </h3>
                
                <p className="text-slate-300 mb-8 leading-relaxed font-light border-t border-b border-slate-800 py-6 w-full">
                    基于脑电诊断和视觉识别给出综合的助眠策略
                </p>

                <button 
                    onClick={() => {
                        setShowStrategyModal(false);
                        onNavigate(AppView.SLEEP_STRATEGY);
                    }}
                    className="w-full py-3 bg-slate-800 hover:bg-slate-700 border border-slate-600 hover:border-slate-500 rounded-xl text-slate-300 hover:text-white text-xs tracking-[0.2em] transition-all uppercase"
                >
                    确认 / Confirm
                </button>
            </div>
        </div>
      )}

    </div>
  );
};
