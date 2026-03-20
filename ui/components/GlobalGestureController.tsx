
import React, { useEffect, useRef, useState } from 'react';

declare global {
  interface Window {
    Hands: any;
    Camera: any;
    drawConnectors: any;
    drawLandmarks: any;
    HAND_CONNECTIONS: any;
  }
}

export const GlobalGestureController: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [cursorPos, setCursorPos] = useState({ x: -100, y: -100 });
  const [isClicking, setIsClicking] = useState(false);
  const [isHandDetected, setIsHandDetected] = useState(false); // New state for visibility
  const [status, setStatus] = useState('初始化手势引擎...');

  // Smooth cursor references
  const targetPos = useRef({ x: -100, y: -100 });
  const currentPos = useRef({ x: -100, y: -100 });
  const clickDebounce = useRef(false);

  useEffect(() => {
    let hands: any;
    let camera: any;
    let animationFrameId: number;

    const onResults = (results: any) => {
      if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
        setIsHandDetected(true);
        setStatus('手势追踪中');
        const landmarks = results.multiHandLandmarks[0];

        // 1. Cursor Tracking (Index Finger Tip - ID: 8)
        const indexTip = landmarks[8];
        // Mirror X coordinate for natural interaction
        const x = (1 - indexTip.x) * window.innerWidth;
        const y = indexTip.y * window.innerHeight;
        
        targetPos.current = { x, y };

        // 2. Click Detection (Fist Logic)
        // Check distance of fingertips to wrist (Landmark 0)
        const wrist = landmarks[0];
        // Index(8), Middle(12), Ring(16), Pinky(20)
        
        const indexDist = Math.sqrt(Math.pow(landmarks[8].x - wrist.x, 2) + Math.pow(landmarks[8].y - wrist.y, 2));
        const middleDist = Math.sqrt(Math.pow(landmarks[12].x - wrist.x, 2) + Math.pow(landmarks[12].y - wrist.y, 2));
        const ringDist = Math.sqrt(Math.pow(landmarks[16].x - wrist.x, 2) + Math.pow(landmarks[16].y - wrist.y, 2));
        const pinkyDist = Math.sqrt(Math.pow(landmarks[20].x - wrist.x, 2) + Math.pow(landmarks[20].y - wrist.y, 2));

        // Threshold 0.25 (normalized coords) usually means fingers are curled in
        const isFist = indexDist < 0.25 && middleDist < 0.25 && ringDist < 0.25 && pinkyDist < 0.25;

        if (isFist) {
            if (!clickDebounce.current) {
                setIsClicking(true);
                triggerClick();
                clickDebounce.current = true;
                setTimeout(() => { clickDebounce.current = false; setIsClicking(false); }, 600); // 600ms debounce
            }
        } else {
            setIsClicking(false);
        }

      } else {
        setIsHandDetected(false); // Hide cursor when hand is lost
        setStatus('未检测到手部');
      }
    };

    const triggerClick = () => {
        const { x, y } = currentPos.current;
        
        // Hide virtual cursor temporarily to perform click on element underneath
        const cursorEl = document.getElementById('global-cursor');
        if (cursorEl) cursorEl.style.display = 'none';
        
        const el = document.elementFromPoint(x, y) as HTMLElement;
        
        if (cursorEl) cursorEl.style.display = 'flex';

        if (el) {
            // FIXED: Log simplified info instead of the full object to avoid circular JSON error
            console.log('Gesture Click triggered on:', el.tagName, el.className);
            el.click();
            
            // Visual Ripple Effect
            const ripple = document.createElement('div');
            ripple.className = 'fixed rounded-full border-2 border-cyan-400 z-[10000] animate-ping pointer-events-none';
            ripple.style.left = (x - 20) + 'px';
            ripple.style.top = (y - 20) + 'px';
            ripple.style.width = '40px';
            ripple.style.height = '40px';
            document.body.appendChild(ripple);
            setTimeout(() => ripple.remove(), 600);
        }
    };

    const init = async () => {
        if (!window.Hands || !window.Camera) {
            // Wait for scripts to load
            setTimeout(init, 500);
            return;
        }

        try {
            hands = new window.Hands({
                locateFile: (file: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
            });

            hands.setOptions({
                maxNumHands: 1,
                modelComplexity: 1,
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            });

            hands.onResults(onResults);

            if (videoRef.current) {
                camera = new window.Camera(videoRef.current, {
                    onFrame: async () => {
                        if (videoRef.current) {
                           await hands.send({ image: videoRef.current });
                        }
                    },
                    width: 640,
                    height: 480
                });
                await camera.start();
                setStatus('摄像头已启动 - 请举手');
            }
        } catch (e) {
            console.error("Gesture Controller Init Error:", e);
            setStatus('摄像头初始化失败');
        }
    };

    init();

    // Smooth Cursor Animation Loop
    const animate = () => {
        const factor = 0.3; // Smoothing factor (0.1 = slow/smooth, 1.0 = instant)
        currentPos.current.x += (targetPos.current.x - currentPos.current.x) * factor;
        currentPos.current.y += (targetPos.current.y - currentPos.current.y) * factor;

        setCursorPos({ x: currentPos.current.x, y: currentPos.current.y });
        animationFrameId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
        cancelAnimationFrame(animationFrameId);
        if (camera) camera.stop();
        if (hands) hands.close();
    };
  }, []);

  return (
    <>
      {/* Hidden Video for AI Processing */}
      <video ref={videoRef} className="hidden" playsInline muted />

      {/* Virtual Cursor - Fades out when hand not detected */}
      <div 
        id="global-cursor"
        className={`fixed z-[9999] pointer-events-none flex items-center justify-center transition-all duration-300 will-change-transform ${isHandDetected ? 'opacity-100' : 'opacity-0'}`}
        style={{ 
            left: 0, 
            top: 0,
            transform: `translate(${cursorPos.x}px, ${cursorPos.y}px)` 
        }}
      >
        <div className={`w-8 h-8 rounded-full border-2 ${isClicking ? 'bg-cyan-500 scale-90 border-white' : 'border-cyan-400 bg-cyan-400/10'} shadow-[0_0_20px_rgba(34,211,238,0.8)] transition-all`} />
        {/* Crosshair */}
        <div className="absolute w-12 h-[1px] bg-cyan-400/30" />
        <div className="absolute h-12 w-[1px] bg-cyan-400/30" />
      </div>

      {/* Optional Debug Status (Tiny) */}
      <div className="fixed bottom-1 right-1 z-50 text-[9px] text-slate-600 font-mono pointer-events-none opacity-30">
        AI_GESTURE: {status}
      </div>
    </>
  );
};
