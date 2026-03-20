
import React, { useEffect, useState } from 'react';
import { AppView, NavigationProps } from '../types';
import { Background } from './Background';

type PressureLevel = 'low' | 'mid' | 'high';

interface PressureConfig {
  label: string;
  subLabel: string;
  color: string;
  accentColor: string;
  description: string;
  icon: React.ReactNode;
}

// --- Icons / Expressions ---

const LowStressFace = () => (
  <svg viewBox="0 0 100 100" className="w-full h-full drop-shadow-[0_0_15px_rgba(251,191,36,0.5)]">
    <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="2" className="animate-pulse-slow" />
    <path d="M30 40 Q35 30 40 40" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    <path d="M60 40 Q65 30 70 40" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    <path d="M30 60 Q50 80 70 60" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    <circle cx="20" cy="20" r="2" fill="currentColor" className="animate-twinkle" />
    <circle cx="80" cy="80" r="3" fill="currentColor" className="animate-twinkle delay-100" />
  </svg>
);

const MidStressFace = () => (
  <svg viewBox="0 0 100 100" className="w-full h-full drop-shadow-[0_0_15px_rgba(34,211,238,0.5)]">
    <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="2" className="animate-pulse-slow" />
    <line x1="30" y1="40" x2="40" y2="40" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    <line x1="60" y1="40" x2="70" y2="40" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    <line x1="35" y1="65" x2="65" y2="65" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    <circle cx="50" cy="50" r="35" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.3" className="animate-spin-slow" />
  </svg>
);

const HighStressFace = () => (
  <svg viewBox="0 0 100 100" className="w-full h-full drop-shadow-[0_0_15px_rgba(232,121,249,0.5)]">
    <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" className="animate-[spin_4s_linear_infinite]" />
    <circle cx="35" cy="40" r="3" fill="currentColor" />
    <circle cx="65" cy="40" r="3" fill="currentColor" />
    <path d="M30 65 Q40 55 50 65 T70 65" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="animate-pulse" />
    <path d="M10 50 L20 40 L30 60" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.5" />
    <path d="M70 40 L80 60 L90 50" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.5" />
  </svg>
);

// --- Component ---

export const EmotionResultScreen: React.FC<NavigationProps> = ({ onNavigate, data }) => {
  const [result, setResult] = useState<PressureConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const label = typeof data?.pressure === "string" ? data.pressure : "MID";
    const normalized = label.toUpperCase();
    const level: PressureLevel = normalized === "LOW" ? "low" : normalized === "HIGH" ? "high" : "mid";

    const pressureConfigs: Record<PressureLevel, PressureConfig> = {
      low: {
        label: "低压力",
        subLabel: "Low Stress",
        color: "text-amber-400",
        accentColor: "border-amber-500/50 from-amber-900/40 to-slate-900",
        description: "脑电信号表现为稳定、平衡的节律活动，神经系统处于放松与专注的良好状态。",
        icon: <LowStressFace />
      },
      mid: {
        label: "中等压力",
        subLabel: "Moderate Stress",
        color: "text-cyan-400",
        accentColor: "border-cyan-500/50 from-cyan-900/40 to-slate-900",
        description: "检测到适度唤醒水平，注意力集中但负荷可控，建议保持节奏并进行短暂放松。",
        icon: <MidStressFace />
      },
      high: {
        label: "高压力",
        subLabel: "High Stress",
        color: "text-fuchsia-400",
        accentColor: "border-fuchsia-500/50 from-fuchsia-900/40 to-slate-900",
        description: "高频活动明显增强，显示出较高的紧张与负荷水平，建议立即进行放松与呼吸训练。",
        icon: <HighStressFace />
      }
    };

    // Simulate "Processing" delay
    setTimeout(() => {
      setResult(pressureConfigs[level]);
      setLoading(false);
    }, 800);
  }, [data]);

  if (loading || !result) {
    return (
      <div className="relative w-full h-screen flex flex-col items-center justify-center bg-slate-900 text-white">
         <Background />
         <div className="z-10 flex flex-col items-center space-y-4">
            <div className="w-16 h-16 border-4 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin"></div>
            <div className="text-cyan-400 tracking-widest text-xs font-mono animate-pulse">GENERATING REPORT...</div>
         </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-screen flex flex-col items-center justify-center bg-slate-900 text-white overflow-hidden">
      <Background />

      {/* Main Card */}
      <div className={`relative z-10 w-full max-w-sm md:max-w-2xl bg-gradient-to-br ${result.accentColor} backdrop-blur-xl border ${result.accentColor.split(' ')[0]} rounded-3xl p-1 shadow-2xl animate-float transition-all duration-1000`}>
        
        {/* Inner Content */}
        <div className="bg-slate-950/40 rounded-[1.3rem] p-8 md:p-12 flex flex-col md:flex-row items-center gap-8 md:gap-12 relative overflow-hidden">
            
            {/* Decorative Background Glow */}
            <div className={`absolute -top-20 -right-20 w-64 h-64 ${result.color.replace('text-', 'bg-')}/20 blur-[80px] rounded-full pointer-events-none`} />
            <div className={`absolute -bottom-20 -left-20 w-64 h-64 ${result.color.replace('text-', 'bg-')}/10 blur-[80px] rounded-full pointer-events-none`} />

            {/* Left: Visual Icon */}
            <div className={`w-40 h-40 md:w-56 md:h-56 flex-shrink-0 ${result.color}`}>
                {result.icon}
            </div>

            {/* Right: Text Data */}
            <div className="flex flex-col text-center md:text-left space-y-4">
                <div>
                    <div className="text-[10px] uppercase tracking-[0.3em] text-slate-400 mb-2">Pressure Result</div>
                    <h1 className={`text-5xl md:text-6xl font-light tracking-wide ${result.color} drop-shadow-md`}>
                        {result.label}
                    </h1>
                    <p className="text-sm text-slate-500 font-mono mt-1 tracking-wider uppercase opacity-80">{result.subLabel}</p>
                </div>

                <div className="h-px w-full bg-gradient-to-r from-transparent via-slate-700 to-transparent my-4" />

                <p className="text-sm md:text-base text-slate-300 font-light leading-relaxed">
                    {result.description}
                </p>

                <div className="pt-6 flex flex-col md:flex-row gap-4 justify-center md:justify-start">
                     <button 
                        onClick={() => onNavigate(AppView.SLEEP_MODE)}
                        className={`px-8 py-3 rounded-full bg-slate-100/5 hover:bg-slate-100/10 border border-slate-700 hover:border-${result.color.split('-')[1]}-400/50 transition-all text-sm tracking-widest uppercase hover:text-white`}
                     >
                        进入睡眠模式
                     </button>
                     <button 
                        onClick={() => onNavigate(AppView.WELCOME)}
                        className="text-xs text-slate-500 hover:text-white transition-colors tracking-widest uppercase py-3"
                     >
                        返回主页
                     </button>
                </div>
            </div>
        </div>
      </div>
      
      {/* Footer ID */}
      <div className="absolute bottom-8 text-[10px] text-slate-600 font-mono">
        SESSION_ID: {Math.random().toString(36).substring(7).toUpperCase()}
      </div>
    </div>
  );
};
