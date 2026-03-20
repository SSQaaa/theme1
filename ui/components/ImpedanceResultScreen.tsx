import React, { useEffect, useState } from 'react';
import { AppView, NavigationProps } from '../types';
import { Background } from './Background';

const BackIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m15 18-6-6 6-6"/>
  </svg>
);

const CheckIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

// --- Types & Data ---

type ChannelStatus = 'excellent' | 'acceptable' | 'poor' | 'measuring';

interface ChannelData {
  id: string;
  name: string;
  impedance: number; // kOhm
  status: ChannelStatus;
}

const CHANNEL_NAMES = ['F3', 'F4', 'T3', 'T4', 'C3', 'C4', 'P3', 'P4'];

// Helper to get random float
const rnd = (min: number, max: number) => Math.random() * (max - min) + min;

// --- Visual Component: Cap with dynamic status colors ---

interface ImpedanceCapProps {
  channels: ChannelData[];
}

const ImpedanceCapSVG: React.FC<ImpedanceCapProps> = ({ channels }) => {
  // Map impedance value to color class dynamically
  const getColor = (impedance: number) => {
    if (impedance < 10) return "text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.8)]"; // Green
    if (impedance < 50) return "text-yellow-400 drop-shadow-[0_0_8px_rgba(250,204,21,0.8)]"; // Yellow
    return "text-red-500 drop-shadow-[0_0_8px_rgba(239,68,68,0.8)]"; // Red
  };

  // Helper to render an electrode at cx, cy for a specific channel name
  const Electrode = ({ name, cx, cy }: { name: string; cx: string; cy: string }) => {
    const channel = channels.find(c => c.name === name);
    // Format value
    const valNum = channel ? channel.impedance : 99.9;
    const value = channel ? valNum.toFixed(1) : '--';
    
    // Determine fill color based on current impedance value (real-time feedback)
    const colorClass = getColor(valNum);
    const isMeasuring = channel?.status === 'measuring';

    return (
      <g className="transition-all duration-300">
         {/* Glow effect for measuring state */}
         {isMeasuring && (
            <circle cx={cx} cy={cy} r="11" className={`${colorClass} opacity-20 animate-ping`} fill="none" stroke="none" />
         )}

        {/* Main Circle */}
        <circle 
            cx={cx} 
            cy={cy} 
            r="7" 
            fill="currentColor" 
            className={`${colorClass} transition-colors duration-200`} 
        />
        
        {/* Value Inside Circle */}
        <text 
            x={cx} 
            y={cy} 
            dy="2.5" 
            textAnchor="middle" 
            className="text-[3.5px] font-bold fill-slate-900 font-mono pointer-events-none"
                    >
                      {value}
        </text>

        {/* Label Below */}
        <text 
            x={cx} 
            y={parseInt(cy) + 13} 
            textAnchor="middle" 
            className="text-[4px] fill-slate-400 font-mono tracking-wider pointer-events-none"
        >
          {name}
        </text>
      </g>
    );
  };

  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 120" className="w-full h-full">
       <defs>
        <filter id="glow-cap" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Head Outline */}
      <path d="M30,95 C20,85 15,60 15,50 C15,25 30,10 50,10 C70,10 85,25 85,50 C85,60 80,85 70,95" 
            fill="none" stroke="#334155" strokeWidth="1" />
      
      {/* Nose */}
      <path d="M45,10 L50,5 L55,10" fill="none" stroke="#334155" strokeWidth="1" />

      {/* Ears */}
      <path d="M15,45 C10,45 10,55 15,55" fill="none" stroke="#334155" strokeWidth="1" />
      <path d="M85,45 C90,45 90,55 85,55" fill="none" stroke="#334155" strokeWidth="1" />

      {/* Connections (Background Mesh) */}
      <path d="M35,35 L65,35 M35,35 L20,55 M35,35 L40,55 M65,35 L60,55 M65,35 L80,55 
               M20,55 L40,55 M40,55 L60,55 M60,55 L80,55
               M20,55 L35,75 M40,55 L35,75 M60,55 L65,75 M80,55 L65,75 M35,75 L65,75" 
            stroke="#1e293b" strokeWidth="0.5" />

      {/* Electrodes Mapping */}
      {/* Frontal: F3, F4 */}
      <Electrode name="F3" cx="35" cy="35" />
      <Electrode name="F4" cx="65" cy="35" />
      
      {/* Temporal: T3, T4 */}
      <Electrode name="T3" cx="20" cy="55" />
      <Electrode name="T4" cx="80" cy="55" />

      {/* Central: C3, C4 */}
      <Electrode name="C3" cx="40" cy="55" />
      <Electrode name="C4" cx="60" cy="55" />

      {/* Parietal: P3, P4 */}
      <Electrode name="P3" cx="35" cy="75" />
      <Electrode name="P4" cx="65" cy="75" />
    </svg>
  );
};

// --- Main Component ---

export const ImpedanceResultScreen: React.FC<NavigationProps> = ({ onNavigate, data }) => {
  const [channels, setChannels] = useState<ChannelData[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [progress, setProgress] = useState(0);

  // Initialize Data based on Scenario ID (data.testId)
  useEffect(() => {
    const testId = data?.testId || 0;
    const scenarioIndex = testId % 5;
    
    // Define Scenarios (Target Impedance Targets)
    let targets: {name: string, type: 'excellent' | 'acceptable'}[] = CHANNEL_NAMES.map(n => ({ name: n, type: 'excellent' }));

    switch(scenarioIndex) {
        case 0: // All Perfect
            break;
        case 1: // 1 Acceptable (T3)
            targets.find(t => t.name === 'T3')!.type = 'acceptable';
            break;
        case 2: // 2 Acceptable (F3, P4)
            targets.find(t => t.name === 'F3')!.type = 'acceptable';
            targets.find(t => t.name === 'P4')!.type = 'acceptable';
            break;
        case 3: // 1 Acceptable (C4)
            targets.find(t => t.name === 'C4')!.type = 'acceptable';
            break;
        case 4: // 2 Acceptable (T4, P3)
            targets.find(t => t.name === 'T4')!.type = 'acceptable';
            targets.find(t => t.name === 'P3')!.type = 'acceptable';
            break;
    }

    // Initialize state with high values (Red state)
    const initialData: ChannelData[] = targets.map(t => ({
        id: t.name,
        name: t.name,
        impedance: rnd(55, 120), // Start high (Red)
        status: 'measuring'
    }));
    setChannels(initialData);
    setIsComplete(false);
    setProgress(0);

    // Animation Loop
    let step = 0;
    const intervalTime = 300; // SLOWER FLASH: 300ms (was 100ms)
    const totalDuration = 12000; // SLOWER DURATION: 12 seconds (was 8s)
    const totalSteps = totalDuration / intervalTime; 
    
    const interval = setInterval(() => {
        step++;
        const pct = Math.min((step / totalSteps) * 100, 100);
        setProgress(pct);

        setChannels(prev => prev.map(ch => {
            const targetType = targets.find(t => t.name === ch.name)!.type;
            const targetVal = targetType === 'excellent' ? rnd(1.5, 9.5) : rnd(15.0, 45.0);
            
            // While measuring, fluctuate
            let newVal = ch.impedance;
            
            if (step < totalSteps * 0.6) {
                // Wild fluctuation phase (mostly high/red, occasionally dipping)
                // Gradually bias towards target as we progress
                const bias = step / (totalSteps * 0.6);
                const randomFluc = rnd(5, 150);
                // Linear interp between random fluctuation and target
                newVal = (randomFluc * (1 - bias)) + (targetVal * bias);
            } else {
                // Settling phase
                const current = ch.impedance;
                const diff = targetVal - current;
                // Smooth easing
                newVal = current + (diff * 0.15) + rnd(-2, 2);
            }
            
            // Lock in at end
            if (step >= totalSteps) {
                newVal = targetVal;
            }

            // Determine status based on value (for final table) or 'measuring' if not done
            const currentStatus = step >= totalSteps 
                ? targetType 
                : 'measuring';

            return {
                ...ch,
                impedance: Math.abs(newVal),
                status: currentStatus
            };
        }));

        if (step >= totalSteps) {
            clearInterval(interval);
            setIsComplete(true);
        }
    }, intervalTime);

    return () => clearInterval(interval);
  }, [data?.testId]);

  return (
    <div className="relative w-full h-screen flex flex-col bg-slate-900 text-white overflow-hidden">
      <Background />

      {/* Top Bar */}
      <div className="absolute top-0 left-0 w-full p-6 z-20 flex justify-between items-center bg-gradient-to-b from-slate-900 to-transparent">
        <button 
          onClick={() => onNavigate(AppView.EMOTION_DETECTION)}
          className="flex items-center space-x-2 text-slate-400 hover:text-emerald-400 transition-colors"
        >
          <div className="p-2 border border-slate-700 rounded-full hover:border-emerald-400/50">
            <BackIcon />
          </div>
          <span className="tracking-widest text-xs uppercase">Abort Check</span>
        </button>
        <div className="text-right">
          <div className="text-xs text-emerald-500 tracking-[0.2em] font-semibold">
            {isComplete ? 'CHECK COMPLETE' : 'CALIBRATING SIGNAL...'}
          </div>
          <div className="w-32 h-1 bg-slate-800 mt-2 rounded-full overflow-hidden">
            <div 
              className="h-full bg-emerald-500 transition-all duration-100 ease-out" 
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Main Content: Split View */}
      <div className="relative z-10 flex flex-col md:flex-row w-full h-full pt-20 pb-10 px-4 md:px-10 gap-8">
        
        {/* Left: Visualization (Head Map) */}
        <div className="flex-1 flex flex-col items-center justify-center relative">
          <div className="relative w-full max-w-lg aspect-square"> 
            {/* Decoration Rings */}
            <div className="absolute inset-0 border border-slate-700/30 rounded-full animate-[spin_20s_linear_infinite]" />
            <div className="absolute inset-8 border border-slate-700/30 rounded-full animate-[spin_15s_linear_infinite_reverse]" />
            
            {/* The Cap */}
            <div className="absolute inset-0 p-2"> 
               <ImpedanceCapSVG channels={channels} />
            </div>
          </div>
          
          {/* Legend */}
          <div className="flex space-x-6 mt-4 text-[10px] md:text-xs tracking-wider">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
              <span className="text-slate-300">EXCELLENT (&lt;10kΩ)</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-yellow-400 shadow-[0_0_8px_rgba(250,204,21,0.8)]" />
              <span className="text-slate-300">ACCEPTABLE (&lt;50kΩ)</span>
            </div>
             <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]" />
              <span className="text-slate-300">POOR (&gt;50kΩ)</span>
            </div>
          </div>
        </div>

        {/* Right: Data Table */}
        <div className="flex-1 flex flex-col justify-center max-w-xl mx-auto w-full">
            <div className="bg-slate-900/60 backdrop-blur-md border border-slate-700/50 rounded-2xl overflow-hidden shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-slate-700/50 bg-slate-800/40">
                    <h3 className="text-sm font-light tracking-[0.2em] text-emerald-100">CHANNEL IMPEDANCE</h3>
                    <span className="text-xs font-mono text-slate-500">REF: EAR_LOBES</span>
                </div>

                {/* Table Header */}
                <div className="grid grid-cols-4 gap-4 p-4 text-[10px] uppercase tracking-widest text-slate-500 font-semibold border-b border-slate-800">
                    <div className="col-span-1">Channel</div>
                    <div className="col-span-1 text-right">Value (kΩ)</div>
                    <div className="col-span-2 text-right">Status</div>
                </div>

                {/* Rows */}
                <div className="max-h-[400px] overflow-y-auto">
                    {channels.map((ch) => {
                        // Determine text color based on value for the table
                        let valueColor = "text-white";
                        if (ch.impedance < 10) valueColor = "text-emerald-400";
                        else if (ch.impedance < 50) valueColor = "text-yellow-400";
                        else valueColor = "text-red-400";

                        return (
                            <div key={ch.id} className="grid grid-cols-4 gap-4 p-3 items-center border-b border-slate-800/50 hover:bg-white/5 transition-colors">
                                <div className="col-span-1 font-mono text-slate-300">{ch.name}</div>
                                <div className={`col-span-1 text-right font-mono ${valueColor}`}>
                                    {ch.impedance.toFixed(1)}
                                </div>
                                <div className="col-span-2 flex justify-end">
                                    {ch.status === 'measuring' ? (
                                        <span className="text-xs text-slate-500 animate-pulse">MEASURING...</span>
                                    ) : (
                                        <span className={`flex items-center space-x-1 text-xs font-bold tracking-wider px-2 py-1 rounded ${
                                            ch.status === 'excellent' 
                                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                                                : 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                                        }`}>
                                            {ch.status === 'excellent' && <CheckIcon />}
                                            <span>{ch.status === 'excellent' ? 'EXCELLENT' : 'PASS'}</span>
                                        </span>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Action Area */}
            <div className="mt-8 flex flex-col items-end justify-center space-y-4 min-h-[6rem]">
               {isComplete && (
                   <>
                     <div className="text-right">
                       <div className="text-xl md:text-2xl font-bold text-emerald-400 drop-shadow-[0_0_10px_rgba(52,211,153,0.5)]">
                         通过阻抗测试 ✅
                       </div>
                      <div className="text-xs md:text-sm text-slate-400 font-mono tracking-wider mt-1">
                        {"\u53ef\u4ee5\u8fdb\u5165\u538b\u529b\u68c0\u6d4b"}
                      </div>
                     </div>
                     <button 
                       onClick={() => onNavigate(AppView.EMOTION_ANALYSIS)} 
                      className="animate-float px-8 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 rounded-full text-white font-light tracking-widest hover:shadow-[0_0_20px_rgba(52,211,153,0.4)] transition-all transform hover:scale-105"
                     >
                       {"\u8fdb\u5165\u538b\u529b\u68c0\u6d4b"}
                     </button>
                   </>
               )}
            </div>
        </div>

      </div>
    </div>
  );
};
