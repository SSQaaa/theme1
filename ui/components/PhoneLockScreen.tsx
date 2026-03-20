
import React, { useState, useEffect } from 'react';
import { AppView, NavigationProps } from '../types';
import { Background } from './Background';

const LockIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
);

const UnlockIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></svg>
);

const SmartphoneIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>
);

const WindIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/><path d="M12.6 19.4A2 2 0 1 0 14 16H2"/></svg>
);

const HeadphonesIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2z"/><path d="M18 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2h-3a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2z"/><path d="M2 14v-3a6 6 0 0 1 6-6h8a6 6 0 0 1 6 6v3"/></svg>
);

export const PhoneLockScreen: React.FC<NavigationProps> = ({ onNavigate, data }) => {
  const [isLocked, setIsLocked] = useState(false);
  const [emergencyCount, setEmergencyCount] = useState(3);
  const [now, setNow] = useState(new Date());
  const [unlockTime, setUnlockTime] = useState<Date | null>(null);

  // Default alarm time if not provided: 7:30 AM
  const alarmConfig = data?.alarmTime || { hour: 7, minute: 30 };

  // Timer for clock and auto-unlock check
  useEffect(() => {
    const timer = setInterval(() => {
        const currentTime = new Date();
        setNow(currentTime);

        if (isLocked && unlockTime) {
            // Check if current time has passed the unlock time
            if (currentTime >= unlockTime) {
                // Navigate to Alarm Ringing Screen immediately
                onNavigate(AppView.ALARM_RINGING);
                setIsLocked(false); 
            }
        }
    }, 1000);
    return () => clearInterval(timer);
  }, [isLocked, unlockTime, onNavigate]);

  const handleLock = () => {
      // Calculate next unlock time based on alarmConfig
      const target = new Date();
      target.setHours(alarmConfig.hour);
      target.setMinutes(alarmConfig.minute);
      target.setSeconds(0);

      // If target time has already passed today, assume it's for tomorrow
      if (target <= new Date()) {
          target.setDate(target.getDate() + 1);
      }
      
      setUnlockTime(target);
      setIsLocked(true);
  };

  const handleEmergencyUnlock = () => {
      if (emergencyCount > 0) {
          if (confirm(`确认使用应急开锁？\n剩余次数: ${emergencyCount - 1}`)) {
              setEmergencyCount(prev => prev - 1);
              setIsLocked(false);
          }
      }
  };

  const formatTime = (d: Date) => {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
  };

  return (
    <div className="relative w-full h-screen bg-slate-950 overflow-hidden flex flex-col items-center justify-center text-white">
      <Background />
      
      {/* Dimming Overlay for Sleep Mode */}
      <div 
        className={`absolute inset-0 bg-black transition-opacity duration-1000 pointer-events-none z-0 ${isLocked ? 'opacity-70' : 'opacity-0'}`} 
      />

      {/* Header */}
      <div className="absolute top-0 w-full p-6 flex justify-between items-center z-20">
          <div className="flex items-center space-x-2 text-indigo-400">
             <span className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse" />
             <span className="text-xs tracking-[0.2em] font-mono">数字手机盒</span>
          </div>
          {!isLocked && (
            <button 
                onClick={() => onNavigate(AppView.SLEEP_STRATEGY)} 
                className="text-xs text-slate-500 hover:text-white uppercase tracking-widest transition-colors"
            >
                返回
            </button>
          )}
      </div>

      {/* Main Container */}
      <div className="relative z-10 flex flex-col items-center justify-center h-full w-full max-w-md px-6 space-y-8">
          
          {/* Locker Box Visual */}
          <div className={`relative w-64 h-80 rounded-3xl border-2 flex items-center justify-center transition-all duration-700 ${
              isLocked 
                ? 'bg-slate-900/90 border-red-500/30 shadow-[0_0_50px_rgba(239,68,68,0.2)]' 
                : 'bg-slate-900/40 border-emerald-500/30 shadow-[0_0_30px_rgba(16,185,129,0.1)]'
          }`}>
              
              {/* Internal Glow */}
              <div className={`absolute inset-0 rounded-3xl opacity-20 blur-xl ${isLocked ? 'bg-red-900' : 'bg-emerald-900'}`} />

              <div className="flex flex-col items-center space-y-6 relative z-10">
                  <div className={`transform transition-all duration-500 ${isLocked ? 'text-red-500 scale-110' : 'text-emerald-400 scale-100'}`}>
                      {isLocked ? <LockIcon /> : <UnlockIcon />}
                  </div>
                  
                  {isLocked ? (
                      <div className="text-center space-y-1">
                          <div className="text-xs text-red-400/70 uppercase tracking-widest">锁定至</div>
                          <div className="text-4xl font-mono text-red-500 font-bold tracking-widest">
                              {unlockTime ? formatTime(unlockTime) : '--:--'}
                          </div>
                          <div className="text-[10px] text-slate-500 pt-2">
                             当前时间: {formatTime(now)}
                          </div>
                      </div>
                  ) : (
                      <div className="flex flex-col items-center space-y-4 animate-float">
                          <div className="text-emerald-500/50"><SmartphoneIcon /></div>
                          <div className="text-sm text-emerald-400/80 tracking-widest uppercase">盒子已开启</div>
                          <div className="text-[10px] text-slate-400 text-center max-w-[150px]">
                              放入手机，开启数字排毒<br/>享受安稳睡眠
                          </div>
                      </div>
                  )}
              </div>

              {/* Box Door Mechanics Visuals */}
              <div className="absolute top-4 left-4 w-2 h-2 rounded-full bg-slate-700" />
              <div className="absolute top-4 right-4 w-2 h-2 rounded-full bg-slate-700" />
              <div className="absolute bottom-4 left-4 w-2 h-2 rounded-full bg-slate-700" />
              <div className="absolute bottom-4 right-4 w-2 h-2 rounded-full bg-slate-700" />
          </div>

          {/* Sleep Aid Buttons (Visible in both states) */}
          <div className="flex w-full gap-4">
              <button className="flex-1 flex items-center justify-center space-x-2 py-3 rounded-xl bg-slate-800/60 hover:bg-slate-700/80 border border-slate-700/50 transition-all text-slate-300 hover:text-cyan-300">
                    <HeadphonesIcon />
                    <span className="text-xs tracking-widest">白噪音</span>
              </button>
              <button className="flex-1 flex items-center justify-center space-x-2 py-3 rounded-xl bg-slate-800/60 hover:bg-slate-700/80 border border-slate-700/50 transition-all text-slate-300 hover:text-indigo-300">
                    <WindIcon />
                    <span className="text-xs tracking-widest">冥想</span>
              </button>
          </div>

          {/* Controls */}
          <div className="w-full flex flex-col items-center space-y-4">
              {isLocked ? (
                  <div className="w-full space-y-4">
                      <div className="bg-slate-800/50 rounded-lg p-4 text-center border border-slate-700/50">
                          <h3 className="text-xs text-slate-400 uppercase tracking-widest mb-2">应急开锁通道</h3>
                          <div className="flex justify-center space-x-1 mb-4">
                              {[...Array(3)].map((_, i) => (
                                  <div 
                                    key={i} 
                                    className={`w-8 h-2 rounded-full ${i < emergencyCount ? 'bg-orange-500' : 'bg-slate-700'}`} 
                                  />
                              ))}
                          </div>
                          <button
                            onClick={handleEmergencyUnlock}
                            disabled={emergencyCount === 0}
                            className={`w-full py-3 rounded-lg text-xs font-bold tracking-[0.2em] uppercase transition-all ${
                                emergencyCount > 0 
                                ? 'bg-orange-500/10 text-orange-500 border border-orange-500/50 hover:bg-orange-500 hover:text-white' 
                                : 'bg-slate-800 text-slate-600 cursor-not-allowed'
                            }`}
                          >
                            {emergencyCount > 0 ? '紧急开锁' : '次数耗尽'}
                          </button>
                      </div>
                      <p className="text-[10px] text-slate-500 text-center opacity-70">
                          手机已隔离，请安心入睡。祝您好梦。
                      </p>
                  </div>
              ) : (
                  <button
                    onClick={handleLock}
                    className="w-full py-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-bold tracking-[0.2em] uppercase shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/40 transform hover:scale-[1.02] transition-all"
                  >
                      锁定手机
                  </button>
              )}
          </div>
      </div>
    </div>
  );
};
