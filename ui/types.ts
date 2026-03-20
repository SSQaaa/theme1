
export enum AppView {
  WELCOME = 'WELCOME',
  EMOTION_DETECTION = 'EMOTION_DETECTION',
  IMPEDANCE_CHECK = 'IMPEDANCE_CHECK',
  EMOTION_ANALYSIS = 'EMOTION_ANALYSIS',
  EMOTION_RESULT = 'EMOTION_RESULT',
  SLEEP_MODE = 'SLEEP_MODE',
  SLEEP_STRATEGY = 'SLEEP_STRATEGY',
  PHONE_LOCK = 'PHONE_LOCK',
  ALARM_RINGING = 'ALARM_RINGING'
}

export interface NavigationProps {
  currentView: AppView;
  onNavigate: (view: AppView, data?: any) => void;
  // Optional prop for passing data between views (like test cycle index or alarm time)
  data?: any;
}
