
import React, { useEffect, useRef, useState } from 'react';
import { AppView, NavigationProps } from '../types';
import { Background } from './Background';
import { sendCommand, getLightState, setLightBrightness, setLightColorTemp, setLightPower, getWebSocketURL } from "../api";
import { useWebSocket } from '../hooks/useWebSocket';


const handlePlayWhiteNoise = async () => {
  try {
    console.log("[DEBUG] 发送白噪音播放命令...");
    const response = await sendCommand("PLAY_MUSIC", {
      volume: 80,
      loop: true,
    });
    console.log("[DEBUG] 后端响应:", response);
    alert("白噪音正在香橙派上播放！\n路径: " + response.path);
  } catch (err) {
    console.error("[ERROR] 播放白噪音失败:", err);
    alert("播放失败: " + err.message);
  }
};

const handlePlayMeditation = async () => {
  try {
    console.log("[DEBUG] 发送冥想音乐播放命令...");
    const response = await sendCommand("PLAY_MEDITATION", {
      volume: 80,
      loop: true,
    });
    console.log("[DEBUG] 后端响应:", response);
    alert("冥想音乐正在香橙派上播放！\n路径: " + response.path);
  } catch (err) {
    console.error("[ERROR] 播放冥想音乐失败:", err);
    alert("播放失败: " + err.message);
  }
};

const handleSpinWheel = async (sector: number) => {
  try {
    await sendCommand("SPIN_WHEEL", {
      sector: sector,
    });
    console.log(`转盘将转到扇区 ${sector}`);
  } catch (err) {
    console.error("转盘控制失败", err);
  }
};



// Icons
const BackIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
);
const WindIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/><path d="M12.6 19.4A2 2 0 1 0 14 16H2"/></svg>
);
const SunIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>
);
const CloudRainIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="M8 19v2"/><path d="M8 13v2"/><path d="M16 19v2"/><path d="M16 13v2"/><path d="M12 21v2"/><path d="M12 15v2"/></svg>
);
const WavesIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/></svg>
);
const HeadphonesIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2z"/><path d="M18 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2h-3a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2z"/><path d="M2 14v-3a6 6 0 0 1 6-6h8a6 6 0 0 1 6 6v3"/></svg>
);
const MoonStarIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/><path d="M19 3v4"/><path d="M21 5h-4"/></svg>
);
const CheckIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
);

// Constants for ScrollPicker
const ITEM_HEIGHT = 50; 
const VISIBLE_ITEMS = 3; 
const CONTAINER_HEIGHT = ITEM_HEIGHT * VISIBLE_ITEMS; // 150px

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const MINUTES = Array.from({ length: 60 }, (_, i) => i);

// --- WheelPicker Component ---
interface WheelPickerProps {
  onSectorSelect: (sector: number) => void;
}

const WheelPicker: React.FC<WheelPickerProps> = ({ onSectorSelect }) => {
  const [rotation, setRotation] = useState(0);
  const [isCooldown, setIsCooldown] = useState(false); // 整个流程的冷却锁定
  const [highlightedSector, setHighlightedSector] = useState<number | null>(null);
  const [transitionDuration, setTransitionDuration] = useState(2000); // 动态控制动画时长
  const wheelRef = useRef<SVGSVGElement>(null);
  const rotationRef = useRef(0); // 记录当前累计旋转角度
  
  const SECTORS = 6;
  const SECTOR_ANGLE = 360 / SECTORS; // 60度每个扇区
  const WHEEL_SIZE = 280;
  const CENTER = WHEEL_SIZE / 2;
  const RADIUS = WHEEL_SIZE / 2 - 10;

  // 计算每个扇区的路径
  const getSectorPath = (index: number) => {
    const startAngle = (index * SECTOR_ANGLE - 90) * (Math.PI / 180);
    const endAngle = ((index + 1) * SECTOR_ANGLE - 90) * (Math.PI / 180);
    
    const x1 = CENTER + RADIUS * Math.cos(startAngle);
    const y1 = CENTER + RADIUS * Math.sin(startAngle);
    const x2 = CENTER + RADIUS * Math.cos(endAngle);
    const y2 = CENTER + RADIUS * Math.sin(endAngle);
    
    const largeArcFlag = SECTOR_ANGLE > 180 ? 1 : 0;
    
    return `M ${CENTER} ${CENTER} L ${x1} ${y1} A ${RADIUS} ${RADIUS} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;
  };

  // 获取扇区文字位置
  const getTextPosition = (index: number) => {
    const angle = (index * SECTOR_ANGLE + SECTOR_ANGLE / 2 - 90) * (Math.PI / 180);
    const textRadius = RADIUS * 0.65;
    const x = CENTER + textRadius * Math.cos(angle);
    const y = CENTER + textRadius * Math.sin(angle);
    return { x, y };
  };

  // 计算点击的扇区
  const getSectorFromClick = (x: number, y: number): number => {
    const dx = x - CENTER;
    const dy = y - CENTER;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    if (distance > RADIUS) return -1;
    
    let angle = Math.atan2(dy, dx) * (180 / Math.PI);
    angle = (angle + 90 + 360) % 360; // 调整角度，使0度在顶部
    
    const sector = Math.floor(angle / SECTOR_ANGLE);
    return sector % SECTORS;
  };

  const handleWheelClick = (e: React.MouseEvent<SVGSVGElement>) => {
    // 冷却期间忽略所有点击
    if (isCooldown) {
      return;
    }

    const rect = wheelRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const sector = getSectorFromClick(x, y);

    if (sector < 0) return;

    // 立即进入冷却锁定状态，防止重复点击
    setIsCooldown(true);
    setTransitionDuration(2000); // 旋转动画 2 秒

    // 计算目标角度：使指针指向点击的扇区
    // 扇区0中心在30°，扇区1在90°，扇区2在150°...
    const sectorCenterAngle = sector * SECTOR_ANGLE + SECTOR_ANGLE / 2;
    // 指针在顶部(0°位置)，需要旋转使扇区中心对准顶部
    // 顺时针旋转角度 = 360 - sectorCenterAngle + 30 (因为扇区1在顶部时rotation=0)
    let targetAngle = (360 - sectorCenterAngle + 30) % 360;
    if (targetAngle <= 0) targetAngle += 360;

    // 从当前位置继续顺时针旋转：2圈(720°) + 对齐角度
    const newRotation = rotationRef.current + 720 + targetAngle;
    rotationRef.current = newRotation;
    setRotation(newRotation);

    // t=2s: 旋转完成 → 高亮扇区 + 发送串口
    setTimeout(() => {
      setHighlightedSector(sector);
      onSectorSelect(sector + 1);
    }, 2000);

    // t=4s: 取消高亮 → 开始顺时针旋转回到初始位置
    setTimeout(() => {
      setHighlightedSector(null);
      setTransitionDuration(2000); // 回归动画 2 秒
      
      // 计算回到初始位置需要旋转的角度
      // 继续顺时针旋转到下一个 360° 的整数倍
      const currentRotation = rotationRef.current;
      const remainder = currentRotation % 360;
      const additionalRotation = remainder === 0 ? 360 : (360 - remainder);
      const resetRotation = currentRotation + additionalRotation;
      
      rotationRef.current = resetRotation;
      setRotation(resetRotation);
    }, 4000);

    // t=6s: 回归完成 → 开始 5 秒冷却
    // t=11s: 冷却结束 → 解除锁定
    setTimeout(() => {
      setIsCooldown(false);
    }, 11000); // 2s旋转 + 2s高亮 + 2s回归 + 5s冷却 = 11s
  };

  return (
    <div className="relative flex flex-col items-center">
      {/* 箭头指示器 */}
      <div className="absolute -top-8 z-20 flex flex-col items-center">
        <div className="w-0 h-0 border-l-[12px] border-r-[12px] border-t-[20px] border-l-transparent border-r-transparent border-t-cyan-400 drop-shadow-[0_0_10px_rgba(34,211,238,0.8)]" />
        <div className="w-1 h-6 bg-cyan-400/50" />
      </div>
      
      {/* 转盘容器 */}
      <div className="relative">
        <svg
          ref={wheelRef}
          width={WHEEL_SIZE}
          height={WHEEL_SIZE}
          className="cursor-pointer ease-out"
          style={{ 
            transform: `rotate(${rotation}deg)`,
            transition: `transform ${transitionDuration}ms ease-out`
          }}
          onClick={handleWheelClick}
        >
          {/* 转盘背景圆环 */}
          <circle
            cx={CENTER}
            cy={CENTER}
            r={RADIUS}
            fill="none"
            stroke="rgba(148, 163, 184, 0.2)"
            strokeWidth="2"
            className="transition-all"
          />
          
          {/* 绘制6个扇区 */}
          {Array.from({ length: SECTORS }).map((_, index) => {
            const textPos = getTextPosition(index);
            return (
              <g key={index}>
                <path
                  d={getSectorPath(index)}
                  className={`stroke-slate-700/50 stroke-[1.5] transition-all ${
                    highlightedSector === index
                      ? 'fill-yellow-400/80'
                      : 'fill-slate-900/60 hover:fill-slate-800/70'
                  } ${isCooldown ? '' : 'cursor-pointer'}`}
                />
                {/* 扇区文字 */}
                <text
                  x={textPos.x}
                  y={textPos.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="font-mono font-bold text-white fill-white text-4xl pointer-events-none"
                  style={{ userSelect: 'none' }}
                >
                  {index + 1}
                </text>
              </g>
            );
          })}
          
          {/* 中心圆 */}
          <circle
            cx={CENTER}
            cy={CENTER}
            r={20}
            fill="rgba(30, 41, 59, 0.8)"
            stroke="rgba(148, 163, 184, 0.3)"
            strokeWidth="2"
            className="pointer-events-none"
          />
          <circle
            cx={CENTER}
            cy={CENTER}
            r={8}
            fill="rgba(148, 163, 184, 0.4)"
            className="pointer-events-none"
          />
        </svg>
        
        {/* 外圈装饰 */}
        <div className="absolute inset-0 rounded-full border-2 border-slate-700/30 pointer-events-none" />
      </div>
      
      {/* 底部提示文字 */}
      <div className="mt-6 text-xs text-slate-500 tracking-widest uppercase font-mono">
        {isCooldown ? '冷却中...' : '点击扇区旋转'}
      </div>
    </div>
  );
};

// --- Fixed ScrollPicker Component ---
const ScrollPicker = ({ 
  items, 
  value, 
  onChange 
}: { items: number[], value: number, onChange: (v: number) => void }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const isScrolling = useRef(false);
    const timer = useRef<ReturnType<typeof setTimeout>>(null);

    // Initial Position
    useEffect(() => {
        if (containerRef.current) {
            const index = items.indexOf(value);
            containerRef.current.scrollTop = index * ITEM_HEIGHT;
        }
    }, []); 

    const handleScroll = () => {
        if (!containerRef.current) return;
        
        isScrolling.current = true;
        if (timer.current) clearTimeout(timer.current);

        const scrollTop = containerRef.current.scrollTop;
        const index = Math.round(scrollTop / ITEM_HEIGHT);
        const validIndex = Math.max(0, Math.min(index, items.length - 1));
        
        const newValue = items[validIndex];
        if (newValue !== value) {
            onChange(newValue);
        }

        timer.current = setTimeout(() => {
            isScrolling.current = false;
        }, 150);
    };

    const handleClick = (item: number) => {
        if (containerRef.current) {
            const index = items.indexOf(item);
            containerRef.current.scrollTo({
                top: index * ITEM_HEIGHT,
                behavior: 'smooth'
            });
        }
    };

    return (
        <div 
          className="relative w-24 group overflow-hidden select-none"
          style={{ height: CONTAINER_HEIGHT }}
        >
            {/* Highlight Bar - No frosted glass */}
            <div 
              className="absolute left-0 right-0 pointer-events-none z-10 border-t border-b border-white/20"
              style={{ 
                height: ITEM_HEIGHT, 
                top: '50%', 
                transform: 'translateY(-50%)' 
              }} 
            />
            
            <div 
                ref={containerRef}
                onScroll={handleScroll}
                className="h-full w-full overflow-y-auto snap-y snap-mandatory no-scrollbar"
                style={{ scrollBehavior: 'auto' }}
            >
                <div style={{ height: (CONTAINER_HEIGHT - ITEM_HEIGHT) / 2 }} />
                
                {items.map(item => (
                    <div 
                      key={item} 
                      onClick={() => handleClick(item)}
                      className={`flex items-center justify-center snap-center cursor-pointer transition-all duration-200 ${
                          item === value 
                          ? 'text-white font-bold scale-110 opacity-100' 
                          : 'text-slate-500 scale-90 opacity-40 hover:opacity-70'
                      }`}
                      style={{ height: ITEM_HEIGHT }}
                    >
                        <span className="font-mono text-3xl">{item.toString().padStart(2, '0')}</span>
                    </div>
                ))}

                <div style={{ height: (CONTAINER_HEIGHT - ITEM_HEIGHT) / 2 }} />
            </div>
        </div>
    );
};

interface VerticalSliderProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  onCommit: () => void;
  topIcon: React.ReactNode;
  gradientClass: string;
}

const VerticalSlider: React.FC<VerticalSliderProps> = ({ label, value, onChange, onCommit, topIcon, gradientClass }) => {
  const trackRef = useRef<HTMLDivElement>(null);
  const clamped = Math.max(0, Math.min(100, value));

  const updateFromClientY = (clientY: number) => {
    if (!trackRef.current) return;
    const rect = trackRef.current.getBoundingClientRect();
    const y = Math.max(rect.top, Math.min(rect.bottom, clientY));
    const pct = 100 - ((y - rect.top) / rect.height) * 100;
    onChange(Math.round(Math.max(0, Math.min(100, pct))));
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    updateFromClientY(event.clientY);
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.pressure === 0 && event.buttons === 0) return;
    updateFromClientY(event.clientY);
  };

  const handlePointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    onCommit();
  };

  return (
    <div className="flex flex-col items-center gap-3 select-none">
      <div className="text-slate-300/80">{topIcon}</div>
      <div
        ref={trackRef}
        className="relative h-56 w-10 flex items-center justify-center cursor-pointer touch-none"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      >
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="relative h-full w-2 rounded-full bg-slate-700/60 overflow-hidden">
            <div
              className={`absolute bottom-0 w-full ${gradientClass}`}
              style={{ height: `${clamped}%` }}
            />
          </div>
        </div>
        <div
          className="absolute"
          style={{ bottom: `calc(${clamped}% - 8px)` }}
        >
          <div className="w-4 h-4 rounded-full bg-white/90 shadow-[0_0_12px_rgba(255,255,255,0.8)] border border-white/60" />
        </div>
      </div>
      <div className="text-xs text-slate-400 tracking-widest">{label}</div>
    </div>
  );
};

export const SleepStrategyScreen: React.FC<NavigationProps> = ({ onNavigate }) => {
  // Clock State
  const [time, setTime] = useState(new Date());

  // Alarm State
  const [showAlarmModal, setShowAlarmModal] = useState(false);
  const [alarmTime, setAlarmTime] = useState({ hour: 7, minute: 30 });
  const [isAlarmActive, setIsAlarmActive] = useState(true);
  
  // Feedback State
  const [showSuccessToast, setShowSuccessToast] = useState(false);

  // Simulating Environment Data
  const [envData, setEnvData] = useState({
    temp: 24.5, // Celsius
    humidity: 45, // %
    light: 120, // Lux
    pm25: 15, // PM2.5
    noise: 35, // dB
    co2: 450, // ppm
    sensorConnected: false,
    sensorError: ""
  });

  const [lightOn, setLightOn] = useState(false);
  const [brightness, setBrightness] = useState(50);
  const [colorTemp, setColorTemp] = useState(50);
  const [lightError, setLightError] = useState<string | null>(null);
  const brightnessCacheRef = useRef(50);
  const lastBrightnessCommitRef = useRef<number | null>(null);
  const lastColorCommitRef = useRef<number | null>(null);

  // Update Clock
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let isMounted = true;

    const loadLightState = async () => {
      try {
        const res = await getLightState();
        if (!isMounted) return;
        if (res?.ok) {
          const bright = typeof res.brightness === "number" ? res.brightness : 0;
          const temp = typeof res.colorTemp === "number" ? res.colorTemp : 50;
          setLightOn(!!res.on);
          setBrightness(bright);
          setColorTemp(temp);
          if (bright > 0) {
            brightnessCacheRef.current = bright;
          }
          lastBrightnessCommitRef.current = bright;
          lastColorCommitRef.current = temp;
          setLightError(null);
        } else {
          setLightError(res?.msg || "灯带状态获取失败");
        }
      } catch (err: any) {
        setLightError(err?.message || "灯带状态获取失败");
      }
    };

    loadLightState();
    return () => {
      isMounted = false;
    };
  }, []);

  // WebSocket for real-time sensor data
  const { isConnected: wsConnected } = useWebSocket({
    url: getWebSocketURL(),
    onMessage: (message) => {
      if (message.ok && message.data) {
        setEnvData(prev => ({
          ...prev,
          co2: message.data.co2 !== null && message.data.co2 !== undefined ? message.data.co2 : prev.co2,
          temp: message.data.temperature !== null && message.data.temperature !== undefined ? message.data.temperature : prev.temp,
          humidity: message.data.humidity !== null && message.data.humidity !== undefined ? message.data.humidity : prev.humidity,
          pm25: message.data.pm25 !== null && message.data.pm25 !== undefined ? message.data.pm25 : prev.pm25,
          sensorConnected: message.data.connected,
          sensorError: message.data.error_message || ""
        }));
      }
    },
    onError: (error) => {
      console.error('[SleepStrategy] WebSocket error:', error);
    }
  });

  // Update other environment data (light, air, noise) locally
  useEffect(() => {
    const interval = setInterval(() => {
      setEnvData(prev => ({
        ...prev,
        light: Math.max(0, Math.round(prev.light + (Math.random() - 0.5) * 5)),
        noise: Math.max(20, Math.round(prev.noise + (Math.random() - 0.5) * 3)),
      }));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit' 
    });
  };

  const formatSeconds = (date: Date) => {
      return date.getSeconds().toString().padStart(2, '0');
  }

  const handleGoodNight = () => {
    onNavigate(AppView.PHONE_LOCK, { alarmTime });
  };

  const handleSaveAlarm = () => {
      setIsAlarmActive(true);
      setShowAlarmModal(false);
      setShowSuccessToast(true);
      setTimeout(() => setShowSuccessToast(false), 4000);
  };

  const handleToggleLight = async () => {
    const nextOn = !lightOn;
    try {
      if (!nextOn) {
        await setLightPower(false);
        setLightOn(false);
        lastBrightnessCommitRef.current = 0;
        setBrightness(0);
      } else {
        const restore = brightnessCacheRef.current > 0 ? brightnessCacheRef.current : 50;
        setBrightness(restore);
        await setLightBrightness(restore);
        lastBrightnessCommitRef.current = restore;
        setLightOn(true);
      }
      setLightError(null);
    } catch (err: any) {
      setLightError(err?.message || "灯带控制失败");
    }
  };

  const commitBrightness = async () => {
    const value = Math.round(brightness);
    if (lastBrightnessCommitRef.current === value) return;
    try {
      await setLightBrightness(value);
      lastBrightnessCommitRef.current = value;
      if (value > 0) {
        setLightOn(true);
        brightnessCacheRef.current = value;
      } else {
        setLightOn(false);
      }
      setLightError(null);
    } catch (err: any) {
      setLightError(err?.message || "灯带控制失败");
    }
  };

  const commitColorTemp = async () => {
    const value = Math.round(colorTemp);
    if (lastColorCommitRef.current === value) return;
    try {
      await setLightColorTemp(value);
      lastColorCommitRef.current = value;
      setLightOn(true);
      setLightError(null);
    } catch (err: any) {
      setLightError(err?.message || "灯带控制失败");
    }
  };

  return (
    <div className="relative w-full h-screen bg-slate-950 overflow-hidden flex flex-col text-white">
      <Background />
      
      {/* Top Header */}
      <div className="z-20 flex justify-between items-center p-6 border-b border-slate-800/50 bg-slate-900/60 backdrop-blur-md">
         <button 
          onClick={() => onNavigate(AppView.SLEEP_MODE)}
          className="flex items-center space-x-2 text-slate-400 hover:text-cyan-400 transition-colors"
        >
          <div className="p-2 border border-slate-700 rounded-full bg-slate-900/50 backdrop-blur">
            <BackIcon />
          </div>
          <span className="tracking-widest text-xs uppercase">返回监测</span>
        </button>
        <span className="text-xs text-indigo-400 tracking-[0.2em] font-mono">助眠策略执行</span>
      </div>

      <div className="relative z-10 flex-1 flex flex-col items-center justify-between p-6 md:p-8 overflow-y-auto">
        
        {/* 1. Large Alarm Clock */}
        <div 
            onClick={() => setShowAlarmModal(true)}
            className="flex flex-col items-center justify-center py-6 cursor-pointer group transition-transform active:scale-95 select-none"
        >
            <div className="relative">
                <div className="absolute inset-0 bg-indigo-500/20 blur-[60px] rounded-full group-hover:bg-indigo-500/30 transition-all" />
                <div className="relative flex items-baseline space-x-4">
                     <span className="text-7xl md:text-9xl font-light tracking-tighter text-white drop-shadow-[0_0_30px_rgba(255,255,255,0.3)] font-mono group-hover:text-indigo-100 transition-colors">
                        {formatTime(time)}
                     </span>
                     <span className="text-2xl md:text-4xl font-light text-slate-500 font-mono w-16 group-hover:text-slate-400">
                        {formatSeconds(time)}
                     </span>
                </div>
            </div>
            
            <div className={`mt-4 flex items-center space-x-2 px-4 py-2 rounded-full border transition-all ${isAlarmActive ? 'bg-slate-800/50 border-emerald-500/30' : 'bg-slate-800/30 border-slate-700'}`}>
                <div className={`w-2 h-2 rounded-full ${isAlarmActive ? 'bg-emerald-500 animate-pulse' : 'bg-slate-600'}`} />
                <span className={`text-xs tracking-widest uppercase ${isAlarmActive ? 'text-emerald-400' : 'text-slate-500'}`}>
                    {isAlarmActive 
                        ? `闹钟已开启 • ${alarmTime.hour.toString().padStart(2,'0')}:${alarmTime.minute.toString().padStart(2,'0')}` 
                        : '闹钟未开启'}
                </span>
            </div>
        </div>

        {/* 2. Environment Grid & Wheel */}
        <div className="w-full max-w-6xl flex gap-6 items-center justify-center">
            {/* 左侧：环境数据 2x2 */}
            <div className="grid grid-cols-2 gap-3 flex-1 max-w-md">
                <div className="bg-slate-900/40 border border-slate-700/50 rounded-2xl p-3 backdrop-blur-sm flex flex-col items-center justify-center space-y-2 group hover:border-orange-500/30 transition-colors">
                    <div className="text-orange-400/80"><SunIcon /></div>
                    <div className="text-xl font-light text-white">{envData.temp}°C</div>
                    <div className="text-[15px] text-slate-500 tracking-wider uppercase">环境温度</div>
                </div>
                <div className="bg-slate-900/40 border border-slate-700/50 rounded-2xl p-3 backdrop-blur-sm flex flex-col items-center justify-center space-y-2 group hover:border-blue-500/30 transition-colors">
                    <div className="text-blue-400/80"><WavesIcon /></div>
                    <div className="text-xl font-light text-white">{envData.humidity}%</div>
                    <div className="text-[15px] text-slate-500 tracking-wider uppercase">空气湿度</div>
                </div>
                <div className="bg-slate-900/40 border border-slate-700/50 rounded-2xl p-3 backdrop-blur-sm flex flex-col items-center justify-center space-y-2 group hover:border-emerald-500/30 transition-colors">
                    <div className="text-emerald-400/80"><WindIcon /></div>
                    <div className="text-xl font-light text-white">{envData.pm25 !== null && envData.pm25 !== undefined ? envData.pm25 : "--"}</div>
                    <div className="text-[15px] text-slate-500 tracking-wider uppercase">PM2.5浓度</div>
                </div>
                <div className="bg-slate-900/40 border border-slate-700/50 rounded-2xl p-3 backdrop-blur-sm flex flex-col items-center justify-center space-y-2 group hover:border-purple-500/30 transition-colors">
                    <div className="text-purple-400/80"><CloudRainIcon /></div>
                    <div className="text-xl font-light text-white">
                        {envData.sensorConnected ? (
                            <>{envData.co2} <span className="text-sm">ppm</span></>
                        ) : (
                            <span className="text-xs text-red-400">{envData.sensorError || '未连接'}</span>
                        )}
                    </div>
                    <div className="text-[15px] text-slate-500 tracking-wider uppercase">二氧化碳浓度</div>
                </div>
            </div>

            {/* 右侧：转盘 */}
            <div className="flex-1 flex justify-center items-center">
                <div className="bg-slate-900/40 border border-slate-700/50 rounded-2xl p-8 backdrop-blur-sm">
                    <WheelPicker onSectorSelect={handleSpinWheel} />
                </div>
            </div>

            <div className="w-64 flex items-center justify-center">
                <div className="w-full bg-slate-900/40 border border-slate-700/50 rounded-2xl p-4 backdrop-blur-sm">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-xs text-slate-400 tracking-widest uppercase">灯带</span>
                        <button
                          onClick={handleToggleLight}
                          className={`relative w-11 h-6 rounded-full transition-colors ${lightOn ? 'bg-emerald-500/70' : 'bg-slate-700/70'}`}
                          aria-pressed={lightOn}
                        >
                          <span
                            className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${lightOn ? 'translate-x-5' : 'translate-x-0'}`}
                          />
                        </button>
                    </div>

                    <div className="flex items-end justify-center gap-6">
                        <VerticalSlider
                          label="亮度"
                          value={brightness}
                          onChange={setBrightness}
                          onCommit={commitBrightness}
                          topIcon={<div className="text-amber-300/80"><SunIcon /></div>}
                          gradientClass="bg-gradient-to-t from-slate-400/10 via-amber-300/60 to-yellow-200"
                        />
                        <VerticalSlider
                          label="色温"
                          value={colorTemp}
                          onChange={setColorTemp}
                          onCommit={commitColorTemp}
                          topIcon={<div className="text-orange-300/80"><SunIcon /></div>}
                          gradientClass="bg-gradient-to-t from-sky-400/30 via-amber-300/60 to-orange-300/90"
                        />
                    </div>

                    {lightError && (
                      <div className="mt-3 text-[10px] text-red-400 text-center">
                        {lightError}
                      </div>
                    )}
                </div>
            </div>
        </div>

        {/* 3. Action Buttons & Good Night Button */}
        <div className="w-full max-w-4xl flex flex-col gap-4 mt-6">
          <div className="flex gap-4">
            <button
             onClick={handlePlayWhiteNoise}
             className="flex-1 group relative overflow-hidden rounded-2xl bg-gradient-to-br from-cyan-900/40 to-slate-900 border border-cyan-500/20 p-6 hover:border-cyan-400/50 transition-all active:scale-[0.98]"
            >

                 <div className="absolute inset-0 bg-cyan-400/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                 <div className="flex flex-col items-center space-y-2 relative z-10">
                     <div className="p-2 bg-cyan-500/10 rounded-full text-cyan-400 group-hover:scale-110 transition-transform"><HeadphonesIcon /></div>
                     <span className="text-lg font-light tracking-widest text-white group-hover:text-cyan-200">白噪音</span>
                 </div>
            </button>

            <button
             onClick={handlePlayMeditation}
             className="flex-1 group relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-900/40 to-slate-900 border border-indigo-500/20 p-6 hover:border-indigo-400/50 transition-all active:scale-[0.98]"
            >
                 <div className="absolute inset-0 bg-indigo-400/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                 <div className="flex flex-col items-center space-y-2 relative z-10">
                     <div className="p-2 bg-indigo-500/10 rounded-full text-indigo-400 group-hover:scale-110 transition-transform"><WindIcon /></div>
                     <span className="text-lg font-light tracking-widest text-white group-hover:text-indigo-200">冥想</span>
                 </div>
            </button>
          </div>

          {/* GOOD NIGHT BUTTON */}
          <button 
            onClick={handleGoodNight}
            className="w-full relative group overflow-hidden rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 p-6 shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/50 transition-all active:scale-[0.99]"
          >
            <div className="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative z-10 flex items-center justify-center space-x-4">
                <MoonStarIcon />
                <div className="flex flex-col items-start">
                   <span className="text-2xl font-bold tracking-widest text-white uppercase">晚安</span>
                   <span className="text-[10px] text-indigo-200 tracking-widest uppercase">开启手机锁定程序</span>
                </div>
            </div>
          </button>
        </div>

      </div>

      {/* --- Alarm Modal --- */}
      {showAlarmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-[#1c1c1e] rounded-[2rem] p-6 w-80 shadow-2xl border border-slate-700/30 flex flex-col items-center relative overflow-hidden">
                <h3 className="text-orange-500 font-medium mb-6">编辑闹钟</h3>
                
                <div className="flex items-center justify-center space-x-2 bg-[#2c2c2e] rounded-xl px-6 py-6 mb-8 w-full">
                    <ScrollPicker 
                        items={HOURS} 
                        value={alarmTime.hour} 
                        onChange={(h) => setAlarmTime(prev => ({...prev, hour: h}))} 
                    />
                    <span className="text-white font-bold pb-2 text-xl">:</span>
                    <ScrollPicker 
                        items={MINUTES} 
                        value={alarmTime.minute} 
                        onChange={(m) => setAlarmTime(prev => ({...prev, minute: m}))} 
                    />
                </div>
                
                <div className="grid grid-cols-2 gap-4 w-full">
                    <button 
                        onClick={() => setShowAlarmModal(false)}
                        className="py-3 bg-[#2c2c2e] hover:bg-[#3a3a3c] rounded-full text-slate-300 font-medium transition-colors"
                    >
                        取消
                    </button>
                    <button 
                        onClick={handleSaveAlarm}
                        className="py-3 bg-orange-500 hover:bg-orange-600 rounded-full text-white font-bold shadow-lg shadow-orange-500/20 transition-colors"
                    >
                        设置
                    </button>
                </div>

                {isAlarmActive && (
                    <button 
                        onClick={() => { setIsAlarmActive(false); setShowAlarmModal(false); }}
                        className="mt-4 text-red-500 text-sm font-medium hover:text-red-400"
                    >
                        删除闹钟
                    </button>
                )}
            </div>
        </div>
      )}

      {/* --- Success Toast --- */}
      {showSuccessToast && (
        <div className="fixed top-20 left-1/2 transform -translate-x-1/2 z-[60] animate-in fade-in slide-in-from-top-8 duration-500 pointer-events-none">
            <div className="bg-emerald-500/90 backdrop-blur-md text-white px-8 py-4 rounded-2xl shadow-[0_0_30px_rgba(16,185,129,0.6)] flex items-center space-x-4 border border-emerald-400/50">
                <div className="bg-white/20 p-2 rounded-full ring-2 ring-emerald-300/30">
                    <CheckIcon />
                </div>
                <div className="flex flex-col">
                    <span className="text-lg font-bold tracking-widest">设置成功</span>
                    <span className="text-xs text-emerald-100 font-mono">闹钟将在 {alarmTime.hour.toString().padStart(2,'0')}:{alarmTime.minute.toString().padStart(2,'0')} 响铃</span>
                </div>
            </div>
        </div>
      )}

    </div>
  );
};
