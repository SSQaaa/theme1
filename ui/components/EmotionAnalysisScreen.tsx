
import React, { useEffect, useRef, useState } from 'react';
import { AppView, NavigationProps } from '../types';
import { Background } from './Background';
import { getEegWebSocketURL } from '../api';

// --- 图标 ---

const BackIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m15 18-6-6 6-6"/>
  </svg>
);

const PlayIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none">
    <polygon points="5 3 19 12 5 21 5 3"/>
  </svg>
);

const PauseIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none">
    <rect x="6" y="4" width="4" height="16"/>
    <rect x="14" y="4" width="4" height="16"/>
  </svg>
);

const SettingsIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1Z"/>
  </svg>
);

const SignalIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 20h.01"/><path d="M7 20v-4"/><path d="M12 20v-8"/><path d="M17 20V8"/><path d="M22 20V4"/>
  </svg>
);

// --- 配置 ---

const CHANNELS = [
  { id: 1, label: 'F3', color: '#a855f7', region: 'frontal' }, 
  { id: 2, label: 'F4', color: '#8b5cf6', region: 'frontal' }, 
  { id: 3, label: 'T3', color: '#3b82f6', region: 'temporal' }, 
  { id: 4, label: 'T4', color: '#06b6d4', region: 'temporal' }, 
  { id: 5, label: 'C3', color: '#10b981', region: 'central' }, 
  { id: 6, label: 'C4', color: '#eab308', region: 'central' }, 
  { id: 7, label: 'P3', color: '#f97316', region: 'parietal' }, 
  { id: 8, label: 'P4', color: '#ef4444', region: 'parietal' }, 
];

// 五套生理模型场景
const SCENARIOS = [
    { name: "Alpha 放松模式 (闭眼)", desc: "10Hz Alpha波主导 (顶叶区增强)" },
    { name: "高压/焦虑模式 (Beta)", desc: "低幅高频 Beta波 + 肌电干扰 (颞叶区)" },
    { name: "深度睡眠模式 (Delta)", desc: "高幅慢速 Delta波 (0.5-3Hz)" },
    { name: "浅睡/昏沉模式 (Theta)", desc: "Theta波背景 + 14Hz 睡眠纺锤波 (中央区)" },
    { name: "清醒眼动模式 (Artifacts)", desc: "混合波形 + 眨眼伪迹 (额叶区)" }
];

const BG_COLOR = '#151925'; 
const GRID_COLOR = '#334155'; 

const MAX_DURATION = 30; // seconds

export const EmotionAnalysisScreen: React.FC<NavigationProps> = ({ onNavigate }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const [isRunning, setIsRunning] = useState(true);
  const [channelReadouts, setChannelReadouts] = useState<number[]>(new Array(8).fill(0));
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [scenarioIndex, setScenarioIndex] = useState(0);
  const [pressureResult, setPressureResult] = useState<{ label: string; confidence: number } | null>(null);
  const [eegConnected, setEegConnected] = useState(false);
  const [eegError, setEegError] = useState<string | null>(null);
  const [hasRealData, setHasRealData] = useState(false);
  const [sampleRate, setSampleRate] = useState(250);
  const hasRealDataRef = useRef(false);
  const sampleRateRef = useRef(250);
  const lastRenderAtRef = useRef(0);
  const sampleQueueRef = useRef<number[][]>([]);
  const lastSampleAtRef = useRef(0);

  // 初始化随机场景
  useEffect(() => {
    setScenarioIndex(Math.floor(Math.random() * 5));
  }, []);

  useEffect(() => {
    let isMounted = true;
    const ws = new WebSocket(getEegWebSocketURL());

    ws.onopen = () => {
      if (!isMounted) return;
      setEegConnected(true);
      setEegError(null);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "samples" && Array.isArray(message.samples)) {
          sampleQueueRef.current.push(...message.samples);
          lastSampleAtRef.current = Date.now();
          if (!hasRealDataRef.current) {
            hasRealDataRef.current = true;
            setHasRealData(true);
          }
        } else if (message.type === "meta") {
          const sr = Number(message.sample_rate || message.sampleRate || 0);
          if (sr > 0) {
            sampleRateRef.current = sr;
            setSampleRate(sr);
          }
        } else if (message.type === "result") {
          if (!isMounted) return;
          setPressureResult({ label: message.label || "MID", confidence: message.confidence || 0 });
          setElapsedTime(MAX_DURATION);
          setIsRunning(false);
          setIsComplete(true);
        } else if (message.type === "error") {
          if (!isMounted) return;
          setEegError(message.message || "EEG 连接失败");
        }
      } catch (err) {
        if (!isMounted) return;
        setEegError("EEG 数据解析失败");
      }
    };

    ws.onerror = () => {
      if (!isMounted) return;
      setEegError("EEG 连接错误");
    };

    ws.onclose = () => {
      if (!isMounted) return;
      setEegConnected(false);
    };

    return () => {
      isMounted = false;
      try {
        ws.close();
      } catch {}
    };
  }, []);

  const handleToggleStream = () => {
    if (!isRunning && isComplete) {
       // 重置
       setElapsedTime(0);
       setIsComplete(false);
       setPressureResult(null);
       sampleQueueRef.current = [];
       setEegError(null);
       setHasRealData(false);
       hasRealDataRef.current = false;
       lastSampleAtRef.current = 0;
       setScenarioIndex((prev) => (prev + 1) % 5); // 切换下一个场景
    }
    setIsRunning(!isRunning);
  };

  const handleShowResult = () => {
    if (!pressureResult) return;
    onNavigate(AppView.EMOTION_RESULT, { pressure: pressureResult.label, confidence: pressureResult.confidence });
  };

  // 计时器
  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    if (isRunning && !isComplete) {
      timer = setInterval(() => {
        setElapsedTime(prev => {
          if (prev >= MAX_DURATION) {
            setIsRunning(false);
            return MAX_DURATION;
          }
          return prev + 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isRunning, isComplete]);

  useEffect(() => {
    if (elapsedTime >= MAX_DURATION && !pressureResult) {
      setEegError((prev) => prev || "\u672a\u6536\u5230AI\u7ed3\u679c\uff0c\u8bf7\u68c0\u67e5\u540e\u7aef\u65e5\u5fd7");
    }
  }, [elapsedTime, pressureResult]);

  // --- 真实 EEG 物理引擎 ---
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 提高采样率以获得更细腻的波形
    let width = canvas.width;
    let height = canvas.height;
    
    // Buffer: [ChannelIndex][DataPoints]
    const secondsVisible = 10;
    let maxSamples = Math.max(600, Math.floor(sampleRateRef.current * secondsVisible));

    const buffers: number[][] = CHANNELS.map(() => new Array(maxSamples).fill(0));

    const baseline: number[] = CHANNELS.map(() => 0);
    const smooth: number[] = CHANNELS.map(() => 0);
    const rms: number[] = CHANNELS.map(() => 10);
    const notchX1: number[] = CHANNELS.map(() => 0);
    const notchX2: number[] = CHANNELS.map(() => 0);
    const notchY1: number[] = CHANNELS.map(() => 0);
    const notchY2: number[] = CHANNELS.map(() => 0);



    
    let globalTime = 0;
    let nextBlinkTime = 100 + Math.random() * 200;

    let animationFrameId: number;

    const render = () => {
      // 响应式画布调整
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        if (canvas.width !== clientWidth || canvas.height !== clientHeight) {
          canvas.width = clientWidth;
          canvas.height = clientHeight;
          width = clientWidth;
          height = clientHeight;
        }
      }

      // 清空与网格绘制
      ctx.fillStyle = BG_COLOR;
      ctx.fillRect(0, 0, width, height);

      ctx.strokeStyle = GRID_COLOR;
      ctx.lineWidth = 1;
      ctx.beginPath();
      // 时间垂直网格
      for (let i = 1; i < 10; i++) {
        const x = (width / 10) * i;
        ctx.moveTo(x, 0); ctx.lineTo(x, height);
      }
      // 通道水平网格
      const chH = height / 8;
      for (let i = 1; i < 8; i++) {
        const y = chH * i;
        ctx.moveTo(0, y); ctx.lineTo(width, y);
      }
      ctx.stroke();

      // --- 信号生成核心逻辑 ---
      if (isRunning) {
        globalTime++;

        const currentValues: number[] = new Array(CHANNELS.length).fill(0);

        // Sync buffer length with sample rate (slower, OpenBCI-like scroll)
        const desiredSamples = Math.max(600, Math.floor(sampleRateRef.current * secondsVisible));
        if (desiredSamples !== maxSamples) {
          const diff = desiredSamples - maxSamples;
          maxSamples = desiredSamples;
          buffers.forEach((buf) => {
            if (diff > 0) {
              buf.unshift(...new Array(diff).fill(0));
            } else if (diff < 0) {
              buf.splice(0, Math.min(buf.length, -diff));
            }
          });
        }

        const now = performance.now();
        const last = lastRenderAtRef.current || now;
        lastRenderAtRef.current = now;
        const dt = Math.max(1, now - last);
        const expected = Math.max(1, Math.round((sampleRateRef.current * dt) / 1000));
        let maxConsume = Math.min(20, expected + 2);

        // Notch filter coefficients (50Hz)
        const fs = Math.max(1, sampleRateRef.current);
        const w0 = (2 * Math.PI * 50) / fs;
        const cosW0 = Math.cos(w0);
        const r = 0.96;
        const b0 = 1;
        const b1 = -2 * cosW0;
        const b2 = 1;
        const a1 = -2 * r * cosW0;
        const a2 = r * r;

        const dcAlpha = 0.01;
        const smoothAlpha = 0.05;
        const rmsAttack = 0.002;
        const rmsRelease = 0.05;
        const maxAmp = chH * 0.4;
        const minRms = 15;
        const maxGain = 4;

        let consumed = 0;
        while (sampleQueueRef.current.length > 0 && consumed < maxConsume) {
          const sample = sampleQueueRef.current.shift();
          if (!sample || sample.length < CHANNELS.length) {
            continue;
          }
          consumed += 1;
          CHANNELS.forEach((ch, idx) => {
            const buffer = buffers[idx];
            const raw = Number(sample[idx] ?? 0);

            // DC removal (high-pass)
            const base = baseline[idx] + dcAlpha * (raw - baseline[idx]);
            baseline[idx] = base;
            let val = raw - base;

            // Notch 50Hz
            const x0 = val;
            const y0 = b0 * x0 + b1 * notchX1[idx] + b2 * notchX2[idx] - a1 * notchY1[idx] - a2 * notchY2[idx];
            notchX2[idx] = notchX1[idx];
            notchX1[idx] = x0;
            notchY2[idx] = notchY1[idx];
            notchY1[idx] = y0;
            val = y0;

            // Light smoothing (preserve texture)
            const sm = smooth[idx] + smoothAlpha * (val - smooth[idx]);
            smooth[idx] = sm;
            const textured = sm + (val - sm) * 0.8;
            val = textured;

            // Auto-gain using running RMS
            const absVal = Math.abs(val);
            const rPrev = rms[idx];
            const rNext = absVal > rPrev
              ? rPrev + rmsAttack * (absVal - rPrev)
              : rPrev + rmsRelease * (absVal - rPrev);
            rms[idx] = rNext;
            const scale = Math.min(maxGain, maxAmp / Math.max(rNext, minRms));

            const px = maxAmp * Math.tanh((val * scale) / maxAmp);

            buffer.shift();
            buffer.push(px);
            currentValues[idx] = val;
          });
        }

        CHANNELS.forEach((ch, idx) => {
          const buffer = buffers[idx];
          const centerY = (idx * chH) + (chH / 2);
          const stepX = width / maxSamples;

          ctx.beginPath();
          ctx.strokeStyle = ch.color;
          ctx.lineWidth = 1.2;
          ctx.moveTo(0, centerY + buffer[0]);
          for (let i = 1; i < maxSamples; i++) {
            ctx.lineTo(i * stepX, centerY + buffer[i]);
          }
          ctx.stroke();
        });

        if (consumed > 0 && globalTime % 2 === 0) {
          setChannelReadouts(currentValues);
        }
      } else {
        // 暂停状态：重绘静态缓冲区
        CHANNELS.forEach((ch, idx) => {
             const buffer = buffers[idx];
             const centerY = (idx * chH) + (chH / 2);
             const stepX = width / maxSamples;
             ctx.beginPath();
             ctx.strokeStyle = ch.color;
             ctx.lineWidth = 1.2;
             ctx.moveTo(0, centerY + buffer[0]);
             for (let i = 1; i < maxSamples; i++) {
                ctx.lineTo(i * stepX, centerY + buffer[i]);
             }
             ctx.stroke();
        });
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationFrameId);
  }, [isRunning, scenarioIndex]);

  return (
    <div className="flex flex-col h-screen w-full bg-slate-900 text-slate-200 font-sans overflow-hidden">
      {/* 顶部控制栏 */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#1e2330] border-b border-slate-700 h-14 shrink-0 z-20">
        
        <div className="flex items-center space-x-4">
          <button 
            onClick={() => onNavigate(AppView.EMOTION_DETECTION)}
            className="flex items-center space-x-2 px-3 py-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
          >
            <BackIcon />
            <span className="text-xs font-bold tracking-wider uppercase">返回</span>
          </button>
          
          <div className="h-6 w-px bg-slate-700 mx-2" />
          
          <button 
            onClick={handleToggleStream}
            disabled={isComplete}
            className={`flex items-center space-x-2 px-4 py-1.5 rounded shadow-sm transition-all ${
              isComplete 
                ? 'bg-slate-700 text-slate-400 cursor-not-allowed border border-slate-600'
                : isRunning 
                  ? 'bg-red-500/10 text-red-400 border border-red-500/50 hover:bg-red-500/20' 
                  : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/50 hover:bg-emerald-500/20'
            }`}
          >
            {isRunning ? <PauseIcon /> : <PlayIcon />}
            <span className="text-xs font-bold tracking-wider uppercase">
              {isComplete ? '检测完毕' : isRunning ? '停止数据流' : '开始数据流'}
            </span>
          </button>
        </div>

        {/* 中央进度条 */}
        <div className="flex flex-col items-center flex-1 mx-4">
             <div className="flex items-center justify-between w-full max-w-md mb-1">
                <span className="text-[10px] font-bold text-slate-400 tracking-widest">检测进度</span>
                <span className="text-[10px] font-mono text-cyan-400">{elapsedTime}s / {MAX_DURATION}s</span>
             </div>
             <div className="w-full max-w-md h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-1000 linear ${isComplete ? 'bg-emerald-500' : 'bg-cyan-500'}`} 
                  style={{ width: `${(elapsedTime / MAX_DURATION) * 100}%` }}
                />
             </div>
        </div>

        <div className="flex items-center space-x-3">
             <button className="flex items-center space-x-2 px-3 py-1.5 bg-slate-800 rounded border border-slate-700 text-xs hover:border-cyan-500/50 transition-colors">
                <SettingsIcon />
                <span className="hidden md:inline">设置</span>
             </button>
             <div className="px-3 py-1 bg-slate-900 rounded border border-slate-700 text-[10px] font-mono text-cyan-500">
                {Math.round(sampleRate)}Hz
             </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden relative">
        
        {/* 左侧通道栏 */}
        <div className="w-32 md:w-48 bg-[#1e2330] border-r border-slate-700 flex flex-col shrink-0 z-10 transition-all">
            <div className="p-3 border-b border-slate-700 bg-slate-800/50">
                <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500">通道状态</h3>
            </div>
            
            <div className="flex-1 overflow-y-auto p-2 space-y-2 custom-scrollbar">
                {CHANNELS.map((ch, i) => (
                    <div key={ch.id} className="bg-slate-800/40 rounded border border-slate-700/50 p-2 flex flex-col space-y-1">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                                <span 
                                  className="w-3 h-3 md:w-4 md:h-4 rounded-sm flex items-center justify-center text-[8px] md:text-[9px] font-bold text-slate-900"
                                  style={{ backgroundColor: ch.color }}
                                >
                                  {ch.label}
                                </span>
                                <span className="text-[10px] md:text-xs font-bold text-slate-300">{ch.region.toUpperCase()}</span>
                            </div>
                            <div className="hidden md:block text-slate-600"><SignalIcon /></div>
                        </div>
                        
                        <div className="flex items-end justify-between mt-1">
                            <span className="text-[10px] md:text-xs font-mono text-white">
                                {channelReadouts[i]?.toFixed(1)} <span className="text-[8px] text-slate-500">µV</span>
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </div>

        {/* 中央波形画布 */}
        <div className="flex-1 flex flex-col bg-[#151925] relative">
            {!hasRealData && !eegError && (
              <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none">
                <div className="px-4 py-2 rounded-lg bg-slate-900/70 border border-slate-700 text-xs text-slate-300 tracking-widest">
                  {!eegConnected ? "\u6b63\u5728\u8fde\u63a5EEG..." : "\u7b49\u5f85EEG\u6570\u636e..."}
                </div>
              </div>
            )}
            {eegError && (
              <div className="absolute top-3 right-3 z-30 px-3 py-2 rounded-lg bg-red-900/60 border border-red-500/40 text-xs text-red-200">
                {eegError}
              </div>
            )}

            <div ref={containerRef} className="w-full h-full">
                <canvas ref={canvasRef} className="block w-full h-full cursor-crosshair" />
            </div>

            {/* 完成时的弹窗 */}
            {isComplete && (
              <div className="absolute inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center animate-in fade-in duration-500">
                <div className="bg-slate-900 border border-cyan-500/30 p-8 rounded-2xl shadow-2xl flex flex-col items-center space-y-6 max-w-md text-center">
                  <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center mb-2">
                    <svg className="w-8 h-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <div>
                    <h2 className="text-2xl font-light text-white mb-2">检测完毕</h2>
                    <p className="text-slate-400 text-sm">30秒 生理数据采集已完成。AI 分析报告已生成。</p>
                  </div>
                  <button 
                    onClick={handleShowResult}
                    className="w-full py-4 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 rounded-xl text-white font-bold tracking-widest transition-all transform hover:scale-[1.02] shadow-lg shadow-cyan-500/20"
                  >
                    <span className="text-white text-base tracking-widest">{"\u5c55\u793a\u538b\u529b\u72b6\u6001"}</span>
                  </button>
                </div>
              </div>
            )}
        </div>
      </div>
    </div>
  );
};
