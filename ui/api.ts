// 自动检测：优先使用环境变量，否则根据当前访问地址判断
const getBaseURL = () => {
  // 如果设置了环境变量，优先使用
  if (import.meta.env.VITE_ORANGE_PI_API) {
    console.log("[API] 使用环境变量 API 地址:", import.meta.env.VITE_ORANGE_PI_API);
    return import.meta.env.VITE_ORANGE_PI_API;
  }

  // 如果当前是 localhost，使用 localhost（本地开发）
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.log("[API] 使用本地 API 地址: http://localhost:8000");
    return "http://localhost:8000";
  }

  // 否则使用香橙派 IP（生产环境）
  console.log("[API] 使用香橙派 API 地址: http://192.168.31.160:8000");
  return "http://192.168.31.160:8000";
};

const BASE_URL = getBaseURL();

async function apiJson(path: string, options: RequestInit = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  let json: any = null;
  try {
    json = await res.json();
  } catch {
    json = null;
  }

  if (!res.ok || json?.ok === false) {
    throw new Error(json?.msg || json?.detail || `HTTP ${res.status}`);
  }

  return json;
}

export function getWebSocketURL() {
  // Use same base URL logic but convert to ws://
  const baseURL = getBaseURL();
  const wsURL = baseURL.replace('http://', 'ws://').replace('https://', 'wss://');
  return `${wsURL}/ws/sensors`;
}

export function getEegWebSocketURL() {
  const baseURL = getBaseURL();
  const wsURL = baseURL.replace('http://', 'ws://').replace('https://', 'wss://');
  return `${wsURL}/ws/eeg`;
}

export function getAssistantWebSocketURL() {
  // WebSocket URL for AI assistant events
  const baseURL = getBaseURL();
  const wsURL = baseURL.replace('http://', 'ws://').replace('https://', 'wss://');
  return `${wsURL}/ws/assistant`;
}

export async function sendCommand(cmd: string, data: Record<string, any> = {}) {
  console.log(`[API] 发送命令: ${cmd}, 数据:`, data, "到", BASE_URL);
  const res = await fetch(`${BASE_URL}/api/command`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cmd, data }),
  });

  const json = await res.json();
  console.log(`[API] 响应:`, json);
  if (!res.ok || json?.ok === false) {
    throw new Error(json?.msg || json?.detail || `HTTP ${res.status}`);
  }
  return json;
}

// 测试 API 连接
export async function getLightState() {
  return apiJson("/api/light/state");
}

export async function setLightPower(on: boolean) {
  return apiJson("/api/light/power", {
    method: "POST",
    body: JSON.stringify({ on }),
  });
}

export async function setLightBrightness(value: number) {
  return apiJson("/api/light/brightness", {
    method: "POST",
    body: JSON.stringify({ value }),
  });
}

export async function setLightColorTemp(value: number) {
  return apiJson("/api/light/color_temp", {
    method: "POST",
    body: JSON.stringify({ value }),
  });
}

export async function testConnection() {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    const json = await res.json();
    return { ok: true, url: BASE_URL, response: json };
  } catch (err) {
    return { ok: false, url: BASE_URL, error: err.message };
  }
}
