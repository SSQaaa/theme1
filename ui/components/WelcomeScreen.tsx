import React from 'react';
import { AppView, NavigationProps } from '../types';
import { Background } from './Background';

// Icons using SVG
const BrainIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"/>
    <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"/>
  </svg>
);

const MoonIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>
  </svg>
);

export const WelcomeScreen: React.FC<NavigationProps> = ({ onNavigate }) => {
  return (
    <div className="relative w-full h-screen flex flex-col items-center justify-center overflow-hidden">
      <Background />
      
      {/* Main Content Container */}
      <div className="z-10 flex flex-col items-center space-y-12 animate-float">
        
        {/* Header Section */}
        <div className="text-center space-y-4">
          <div className="inline-block px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-950/30 text-cyan-400 text-xs tracking-[0.2em] mb-4 backdrop-blur-sm shadow-[0_0_15px_rgba(34,211,238,0.2)]">
            SYSTEM ONLINE
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-blue-200 via-cyan-100 to-white drop-shadow-[0_0_15px_rgba(165,243,252,0.5)]">
            欢迎来到
            <br />
            <span className="text-6xl md:text-8xl bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              睡眠安抚系统
            </span>
          </h1>
          <p className="text-slate-400 text-sm md:text-base tracking-widest uppercase mt-4">
            AI-Powered Neural Relaxation Interface
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col md:flex-row gap-8 mt-8">
          {/* Emotion Detection Button */}
          <button
            onClick={() => onNavigate(AppView.EMOTION_DETECTION)}
            className="group relative w-64 h-20 rounded-2xl bg-slate-900/40 border border-slate-700 hover:border-cyan-500/50 transition-all duration-300 backdrop-blur-md overflow-hidden"
          >
            <div className="absolute inset-0 bg-cyan-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <div className="absolute bottom-0 left-0 h-[2px] w-0 bg-cyan-500 group-hover:w-full transition-all duration-500 ease-out" />
            
            <div className="relative flex items-center justify-center h-full space-x-3 text-cyan-50">
              <span className="p-2 rounded-full bg-cyan-500/20 group-hover:bg-cyan-500/40 transition-colors shadow-[0_0_10px_rgba(6,182,212,0.3)]">
                <BrainIcon />
              </span>
              <span className="text-xl font-light tracking-wide group-hover:text-cyan-300 transition-colors">{"\u538b\u529b\u68c0\u6d4b"}</span>
            </div>
          </button>

          {/* Enter Sleep Button */}
          <button
            onClick={() => onNavigate(AppView.SLEEP_MODE)}
            className="group relative w-64 h-20 rounded-2xl bg-slate-900/40 border border-slate-700 hover:border-purple-500/50 transition-all duration-300 backdrop-blur-md overflow-hidden"
          >
            <div className="absolute inset-0 bg-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <div className="absolute bottom-0 left-0 h-[2px] w-0 bg-purple-500 group-hover:w-full transition-all duration-500 ease-out" />
            
            <div className="relative flex items-center justify-center h-full space-x-3 text-purple-50">
              <span className="p-2 rounded-full bg-purple-500/20 group-hover:bg-purple-500/40 transition-colors shadow-[0_0_10px_rgba(168,85,247,0.3)]">
                <MoonIcon />
              </span>
              <span className="text-xl font-light tracking-wide group-hover:text-purple-300 transition-colors">
                进入睡眠
              </span>
            </div>
          </button>
        </div>
      </div>

      {/* Footer / Status */}
      <div className="absolute bottom-8 text-slate-600 text-xs tracking-[0.3em] flex items-center space-x-2">
        <span className="w-2 h-2 rounded-full bg-green-500/50 animate-pulse"></span>
        <span>V.1.0.4 // READY</span>
      </div>
    </div>
  );
};
