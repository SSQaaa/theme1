
import React, { useState } from 'react';
import { WelcomeScreen } from './components/WelcomeScreen';
import { EmotionDetectionScreen } from './components/EmotionDetectionScreen';
import { ImpedanceResultScreen } from './components/ImpedanceResultScreen';
import { EmotionAnalysisScreen } from './components/EmotionAnalysisScreen';
import { EmotionResultScreen } from './components/EmotionResultScreen';
import { SleepModeScreen } from './components/SleepModeScreen';
import { SleepStrategyScreen } from './components/SleepStrategyScreen';
import { PhoneLockScreen } from './components/PhoneLockScreen';
import { AlarmRingingScreen } from './components/AlarmRingingScreen';
import { VoiceAssistant } from './components/VoiceAssistant';
import { AppView } from './types';

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<AppView>(AppView.WELCOME);
  const [impedanceTestCount, setImpedanceTestCount] = useState(0);
  const [navData, setNavData] = useState<any>(null);

  const handleNavigate = (view: AppView, data?: any) => {
    // If navigating TO impedance check, increment the counter to show a new scenario
    if (view === AppView.IMPEDANCE_CHECK) {
      setImpedanceTestCount(prev => prev + 1);
    }
    
    // Store any data passed (like alarm time)
    if (data) {
      setNavData(data);
    }

    setCurrentView(view);
  };

  const renderView = () => {
    switch (currentView) {
      case AppView.WELCOME:
        return <WelcomeScreen currentView={currentView} onNavigate={handleNavigate} />;
      case AppView.EMOTION_DETECTION:
        return <EmotionDetectionScreen currentView={currentView} onNavigate={handleNavigate} />;
      case AppView.IMPEDANCE_CHECK:
        return (
          <ImpedanceResultScreen 
            currentView={currentView} 
            onNavigate={handleNavigate} 
            data={{ testId: impedanceTestCount }} 
          />
        );
      case AppView.EMOTION_ANALYSIS:
        return <EmotionAnalysisScreen currentView={currentView} onNavigate={handleNavigate} />;
      case AppView.EMOTION_RESULT:
        return <EmotionResultScreen currentView={currentView} onNavigate={handleNavigate} data={navData} />;
      case AppView.SLEEP_MODE:
        return <SleepModeScreen currentView={currentView} onNavigate={handleNavigate} />;
      case AppView.SLEEP_STRATEGY:
        return <SleepStrategyScreen currentView={currentView} onNavigate={handleNavigate} />;
      case AppView.PHONE_LOCK:
        return <PhoneLockScreen currentView={currentView} onNavigate={handleNavigate} data={navData} />;
      case AppView.ALARM_RINGING:
        return <AlarmRingingScreen currentView={currentView} onNavigate={handleNavigate} />;
      default:
        return <WelcomeScreen currentView={currentView} onNavigate={handleNavigate} />;
    }
  };

  return (
    <main className="min-h-screen bg-slate-900 text-white selection:bg-cyan-500/30">
      {renderView()}
      {/* AI 语音助手弹窗（全局组件，根据 WebSocket 信号显示/隐藏） */}
      <VoiceAssistant />
    </main>
  );
};

export default App;
