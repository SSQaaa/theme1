const getBaseURL = () => {
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.log('[API] using local API: http://localhost:8000');
    return 'http://localhost:8000';
  }

  console.log('[API] using current origin:', window.location.origin);
  return window.location.origin;
};

const BASE_URL = getBaseURL();

async function apiJson(path: string, options: RequestInit = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
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
  const wsURL = BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
  return `${wsURL}/ws/sensors`;
}

export function getEegWebSocketURL() {
  const wsURL = BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
  return `${wsURL}/ws/eeg`;
}

export function getAssistantWebSocketURL() {
  const wsURL = BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
  return `${wsURL}/ws/assistant`;
}

export async function sendCommand(cmd: string, data: Record<string, any> = {}) {
  console.log('[API] send command:', cmd, data, 'to', BASE_URL);
  const res = await fetch(`${BASE_URL}/api/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cmd, data }),
  });

  const json = await res.json();
  console.log('[API] response:', json);
  if (!res.ok || json?.ok === false) {
    throw new Error(json?.msg || json?.detail || `HTTP ${res.status}`);
  }
  return json;
}

export async function getLightState() {
  return apiJson('/api/light/state');
}

export async function setLightPower(on: boolean) {
  return apiJson('/api/light/power', {
    method: 'POST',
    body: JSON.stringify({ on }),
  });
}

export async function setLightBrightness(value: number) {
  return apiJson('/api/light/brightness', {
    method: 'POST',
    body: JSON.stringify({ value }),
  });
}

export async function setLightColorTemp(value: number) {
  return apiJson('/api/light/color_temp', {
    method: 'POST',
    body: JSON.stringify({ value }),
  });
}

export async function testConnection() {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    const json = await res.json();
    return { ok: true, url: BASE_URL, response: json };
  } catch (err: any) {
    return { ok: false, url: BASE_URL, error: err?.message || String(err) };
  }
}
