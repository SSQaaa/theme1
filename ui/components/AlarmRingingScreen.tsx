
import React, { useEffect, useRef, useState } from 'react';
import { AppView, NavigationProps } from '../types';
import { Background } from './Background';

// Icons
const SunIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>
);
const CloudRainIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="M8 19v2"/><path d="M8 13v2"/><path d="M16 19v2"/><path d="M16 13v2"/><path d="M12 21v2"/><path d="M12 15v2"/></svg>
);
const BellOffIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8.7 3A6 6 0 0 1 18 8a21.3 21.3 0 0 0 .6 5"/><path d="M17 17H3s3-2 3-9"/><path d="M10.3 21a1.95 1.95 0 0 0 3.4 0"/><path d="m2 2 20 20"/></svg>
);
const CalendarIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
);
const MapPinIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
);

export const AlarmRingingScreen: React.FC<NavigationProps> = ({ onNavigate }) => {
  const [time, setTime] = useState(new Date());
  const [weatherData] = useState({
      temp: 26,
      condition: 'Sunny',
      aqi: 35,
      humidity: 42,
      location: 'Shanghai, CN'
  });

  // Clock Timer
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Audio Alarm Logic
  useEffect(() => {
    let audioCtx: AudioContext | null = null;
    let oscillator: OscillatorNode | null = null;
    let gainNode: GainNode | null = null;
    let isPlaying = true;
    let animationFrameId: number;

    const startAlarm = () => {
        try {
            const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
            if (!AudioContextClass) return;

            audioCtx = new AudioContextClass();
            oscillator = audioCtx.createOscillator();
            gainNode = audioCtx.createGain();

            // Use a square wave for a harsh alarm sound
            oscillator.type = 'square';
            oscillator.connect(gainNode);
            gainNode.connect(audioCtx.destination);
            
            oscillator.start();

            // Loop logic to create "Beep-Beep-Beep" pattern
            let nextBeepTime = audioCtx.currentTime;

            const scheduleBeeps = () => {
                if (!isPlaying || !audioCtx || !oscillator || !gainNode) return;

                const currentTime = audioCtx.currentTime;
                // Schedule ahead 
                while (nextBeepTime < currentTime + 1.0) {
                    // Beep 1
                    oscillator.frequency.setValueAtTime(880, nextBeepTime); // High pitch A5
                    gainNode.gain.setValueAtTime(0.15, nextBeepTime);
                    gainNode.gain.setValueAtTime(0, nextBeepTime + 0.1);

                    // Beep 2
                    oscillator.frequency.setValueAtTime(880, nextBeepTime + 0.15);
                    gainNode.gain.setValueAtTime(0.15, nextBeepTime + 0.15);
                    gainNode.gain.setValueAtTime(0, nextBeepTime + 0.25);

                    // Beep 3
                    oscillator.frequency.setValueAtTime(880, nextBeepTime + 0.3);
                    gainNode.gain.setValueAtTime(0.15, nextBeepTime + 0.3);
                    gainNode.gain.setValueAtTime(0, nextBeepTime + 0.4);

                    // Pause before next cycle
                    nextBeepTime += 1.2; 
                }
                animationFrameId = requestAnimationFrame(scheduleBeeps);
            };
            
            scheduleBeeps();

        } catch (e) {
            console.error("Audio Context Error", e);
        }
    };

    // User interaction is technically required for AudioContext in some browsers,
    // but since we navigated here from a user flow, we try to auto-play.
    // If blocked, we rely on the pulsing visual.
    startAlarm();

    return () => {
        isPlaying = false;
        if (animationFrameId) cancelAnimationFrame(animationFrameId);
        if (oscillator) try { oscillator.stop(); } catch(e){}
        if (audioCtx) try { audioCtx.close(); } catch(e){}
    };
  }, []);

  const handleStopAlarm = () => {
      onNavigate(AppView.WELCOME);
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('zh-CN', { 
        weekday: 'long', 
        month: 'long', 
        day: 'numeric' 
    });
  };

  return (
    <div className="relative w-full h-screen bg-slate-950 overflow-hidden flex flex-col items-center justify-center text-white">
      {/* Intense Pulsing Background for Alarm */}
      <div className="absolute inset-0 bg-gradient-to-br from-orange-600/20 via-slate-900 to-red-900/20 z-0 animate-pulse-slow" />
      
      {/* Radial Warning Waves */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
         <div className="w-[500px] h-[500px] rounded-full border border-orange-500/30 animate-[ping_2s_linear_infinite]" />
         <div className="w-[700px] h-[700px] rounded-full border border-orange-500/20 animate-[ping_2s_linear_infinite_1s]" />
      </div>

      <div className="z-10 flex flex-col items-center w-full max-w-lg px-6 space-y-12">
        
        {/* Top: Date & Location */}
        <div className="flex w-full justify-between items-end border-b border-white/10 pb-4">
            <div className="flex flex-col">
                <div className="flex items-center space-x-2 text-slate-400 mb-1">
                    <CalendarIcon />
                    <span className="text-sm font-light tracking-wide">{formatDate(time)}</span>
                </div>
                <div className="flex items-center space-x-2 text-slate-500">
                    <MapPinIcon />
                    <span className="text-xs font-mono tracking-widest uppercase">{weatherData.location}</span>
                </div>
            </div>
            <div className="text-right">
                <div className="text-4xl font-light text-white flex items-center justify-end gap-2">
                    <SunIcon />
                    <span>{weatherData.temp}°</span>
                </div>
                <div className="text-xs text-slate-400 uppercase tracking-widest mt-1">
                    AQI {weatherData.aqi} • {weatherData.condition}
                </div>
            </div>
        </div>

        {/* Center: Time Display */}
        <div className="flex flex-col items-center animate-bounce-slow">
            <h1 className="text-8xl md:text-9xl font-bold font-mono tracking-tighter text-white drop-shadow-[0_0_40px_rgba(255,165,0,0.6)]">
                {time.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' })}
            </h1>
            <p className="text-orange-500 tracking-[0.5em] font-bold text-lg mt-4 animate-pulse">
                WAKE UP
            </p>
        </div>

        {/* Middle: Weather Forecast Cards (Futuristic) */}
        <div className="w-full grid grid-cols-3 gap-3">
             <div className="bg-slate-800/40 backdrop-blur border border-slate-700 p-3 rounded-xl flex flex-col items-center justify-center">
                 <span className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">Morning</span>
                 <SunIcon />
                 <span className="text-sm font-bold mt-1">26°</span>
             </div>
             <div className="bg-slate-800/40 backdrop-blur border border-slate-700 p-3 rounded-xl flex flex-col items-center justify-center">
                 <span className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">Afternoon</span>
                 <SunIcon />
                 <span className="text-sm font-bold mt-1">29°</span>
             </div>
             <div className="bg-slate-800/40 backdrop-blur border border-slate-700 p-3 rounded-xl flex flex-col items-center justify-center">
                 <span className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">Evening</span>
                 <div className="scale-75"><CloudRainIcon /></div>
                 <span className="text-sm font-bold mt-1">24°</span>
             </div>
        </div>

        {/* Bottom: Stop Button */}
        <button
            onClick={handleStopAlarm}
            className="group relative w-full h-20 rounded-full bg-gradient-to-r from-orange-500 to-red-600 overflow-hidden shadow-[0_0_40px_rgba(234,88,12,0.4)] transition-transform active:scale-95"
        >
            <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
            <div className="flex items-center justify-center space-x-4 h-full relative z-10">
                <div className="p-2 bg-black/20 rounded-full animate-shake">
                    <BellOffIcon />
                </div>
                <span className="text-2xl font-bold tracking-[0.2em] uppercase">
                    关闭闹钟
                </span>
            </div>
        </button>

      </div>
    </div>
  );
};
