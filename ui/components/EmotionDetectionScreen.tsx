import React from 'react';
import { AppView, NavigationProps } from '../types';
import { Background } from './Background';

const BackIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m15 18-6-6 6-6"/>
  </svg>
);

const EightElectrodeCapSVG = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" className="w-full h-full text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.6)]">
    <defs>
      <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="2" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
    </defs>

    {/* Head Contour */}
    <path d="M30,85 C20,75 15,55 15,45 C15,20 30,5 50,5 C70,5 85,20 85,45 C85,55 80,75 70,85" 
          fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.4" />
    
    {/* Connection Lines (Neural Mesh) */}
    <path d="M35,30 L65,30 M35,30 L20,50 M35,30 L40,50 M65,30 L60,50 M65,30 L80,50 
             M20,50 L40,50 M40,50 L60,50 M60,50 L80,50
             M20,50 L35,70 M40,50 L35,70 M60,50 L65,70 M80,50 L65,70 M35,70 L65,70" 
          stroke="currentColor" strokeWidth="0.5" opacity="0.3" />

    {/* 8 Electrodes */}
    {/* Frontal */}
    <g className="animate-pulse">
      <circle cx="35" cy="30" r="3" fill="currentColor" filter="url(#glow)" />
      <circle cx="65" cy="30" r="3" fill="currentColor" filter="url(#glow)" />
    </g>
    
    {/* Temporal */}
    <g className="animate-pulse delay-75">
      <circle cx="20" cy="50" r="3" fill="currentColor" filter="url(#glow)" />
      <circle cx="80" cy="50" r="3" fill="currentColor" filter="url(#glow)" />
    </g>

    {/* Central */}
    <g className="animate-pulse delay-150">
      <circle cx="40" cy="50" r="3" fill="currentColor" filter="url(#glow)" />
      <circle cx="60" cy="50" r="3" fill="currentColor" filter="url(#glow)" />
    </g>

    {/* Parietal/Occipital */}
    <g className="animate-pulse delay-300">
      <circle cx="35" cy="70" r="3" fill="currentColor" filter="url(#glow)" />
      <circle cx="65" cy="70" r="3" fill="currentColor" filter="url(#glow)" />
    </g>
    
    {/* Cap Bands */}
    <path d="M15,45 Q50,35 85,45" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.2" strokeDasharray="2 2" />
  </svg>
);

export const EmotionDetectionScreen: React.FC<NavigationProps> = ({ onNavigate }) => {
  
  const handleCheck = () => {
    // Navigate to the actual Impedance Check Screen
    onNavigate(AppView.IMPEDANCE_CHECK);
  };

  const handleSkip = () => {
    onNavigate(AppView.EMOTION_ANALYSIS);
  };


  return (
    <div className="relative w-full h-screen flex flex-col overflow-hidden">
      <Background />
      
      {/* Top Bar */}
      <div className="absolute top-0 left-0 w-full p-6 z-20 flex justify-between items-center">
        <button 
          onClick={() => onNavigate(AppView.WELCOME)}
          className="flex items-center space-x-2 text-slate-400 hover:text-cyan-400 transition-colors group"
        >
          <div className="p-2 border border-slate-700 rounded-full group-hover:border-cyan-400/50 bg-slate-900/50 backdrop-blur">
            <BackIcon />
          </div>
          <span className="tracking-widest text-xs uppercase hidden md:block">Return to Hub</span>
        </button>
        <div className="text-right">
          <div className="text-xs text-cyan-500 tracking-[0.2em] font-semibold">STATUS: STANDBY</div>
          <div className="text-[10px] text-slate-500 tracking-widest">MODULE: EEG_STRESS</div>
        </div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 flex flex-col items-center justify-center h-full space-y-10">
        
        {/* Central Graphic Container - Square Frame */}
        <div className="relative w-64 h-64 md:w-80 md:h-80 lg:w-96 lg:h-96 flex items-center justify-center flex-shrink-0">
          
          {/* Square Frame Border */}
          <div className="absolute inset-0 border-2 border-indigo-500/30 bg-slate-900/20 backdrop-blur-sm z-0" />
          
          {/* Corner Accents */}
          <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-cyan-400" />
          <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-cyan-400" />
          <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-cyan-400" />
          <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-cyan-400" />

          {/* Crosshairs */}
          <div className="absolute top-1/2 left-0 w-full h-px bg-cyan-500/20" />
          <div className="absolute left-1/2 top-0 h-full w-px bg-cyan-500/20" />
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-2 bg-cyan-500" />
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-px h-2 bg-cyan-500" />
          <div className="absolute left-0 top-1/2 -translate-y-1/2 h-px w-2 bg-cyan-500" />
          <div className="absolute right-0 top-1/2 -translate-y-1/2 h-px w-2 bg-cyan-500" />

          {/* Inner Glow Background */}
          <div className="absolute inset-0 bg-blue-900/10 blur-xl animate-pulse-slow" />

          {/* Holographic Head Representation */}
          <div className="w-3/4 h-3/4 relative z-10">
             <EightElectrodeCapSVG />
             {/* Scanning Effect - Confined to box */}
             <div className="absolute -inset-4 bg-gradient-to-b from-transparent via-cyan-400/10 to-transparent h-1/4 w-[120%] animate-scan pointer-events-none" />
          </div>
          
          {/* Radial radar lines background */}
          <div className="absolute inset-0 border border-slate-700/30 rounded-full scale-125 opacity-20" />
          <div className="absolute inset-0 border border-slate-700/30 rounded-full scale-75 opacity-20" />
        </div>

        {/* Text Instructions */}
        <div className="text-center space-y-4 max-w-lg px-4 w-full">
          <h2 className="text-3xl md:text-4xl font-light text-white tracking-wide">
            请佩戴<span className="text-cyan-400 font-bold ml-2">脑电帽</span>
          </h2>
          <div className="h-px w-32 bg-gradient-to-r from-transparent via-slate-700 to-transparent mx-auto" />
          
          {/* Precautions / Instructions Panel */}
          <div className="w-full bg-slate-800/30 border border-slate-700/50 rounded-lg p-4 backdrop-blur-sm text-left relative overflow-hidden group hover:border-slate-600/50 transition-colors">
            <div className="absolute top-0 left-0 w-0.5 h-full bg-cyan-500/30 group-hover:bg-cyan-500 transition-colors" />
            <h3 className="text-cyan-400 text-[10px] tracking-[0.2em] uppercase mb-3 font-semibold flex items-center">
              <span className="mr-2 text-base">⚠</span> 注意事项 / PRECAUTIONS
            </h3>
            <ul className="space-y-2 text-xs md:text-sm text-slate-300 font-light">
               <li className="flex items-start">
                  <span className="text-cyan-500/70 mr-2 font-mono">01.</span>
                  <span>保持额头及耳垂区域皮肤清洁干燥</span>
               </li>
               <li className="flex items-start">
                  <span className="text-cyan-500/70 mr-2 font-mono">02.</span>
                  <span>请务必<span className="text-cyan-200 font-medium border-b border-cyan-500/30 pb-0.5 mx-1">正确夹好耳垂参考电极</span>以确保信号稳定</span>
               </li>
               <li className="flex items-start">
                  <span className="text-cyan-500/70 mr-2 font-mono">03.</span>
                  <span>调整脑电帽位置，确保电极紧贴头皮</span>
               </li>
            </ul>
          </div>

          <p className="text-[10px] text-slate-500 font-mono pt-2">
            Ready for impedance check sequence
          </p>
        </div>

        {/* Check Button */}
        <button
          onClick={handleCheck}
          className="group relative px-16 py-4 bg-transparent overflow-hidden rounded-full transition-all active:scale-95"
        >
          {/* Button Background & Borders */}
          <div className="absolute inset-0 border border-cyan-500/30 rounded-full group-hover:border-cyan-400/80 transition-colors duration-500 box-border" />
          <div className="absolute inset-[3px] border border-slate-700/50 rounded-full" />
          <div className="absolute inset-0 bg-cyan-950/40 rounded-full backdrop-blur-md group-hover:bg-cyan-900/60 transition-colors duration-500" />
          
          {/* Active Glow */}
          <div className="absolute inset-0 bg-cyan-400/10 blur-md opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

          {/* Text Content */}
          <span className="relative z-10 flex items-center justify-center space-x-3 text-lg font-light tracking-widest text-cyan-100 group-hover:text-white transition-colors">
            <span>开启阻抗测试</span>
          </span>
        </button>

        <button
          onClick={handleSkip}
          className="group relative px-10 py-3 bg-transparent overflow-hidden rounded-full transition-all active:scale-95"
        >
          <div className="absolute inset-0 border border-slate-600/40 rounded-full group-hover:border-cyan-500/50 transition-colors duration-500 box-border" />
          <div className="absolute inset-[3px] border border-slate-700/40 rounded-full" />
          <div className="absolute inset-0 bg-slate-900/40 rounded-full backdrop-blur-md group-hover:bg-slate-800/60 transition-colors duration-500" />
          <span className="relative z-10 flex items-center justify-center space-x-3 text-sm font-light tracking-widest text-slate-200 group-hover:text-white transition-colors">
            <span>{"\u76f4\u63a5\u8fdb\u5165\u538b\u529b\u68c0\u6d4b"}</span>
          </span>
        </button>

        

      </div>
    </div>
  );
};
