const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type RuntimeConfig = {
  API_AUTH_TOKEN?: string;
  VITE_API_AUTH_TOKEN?: string;
};

declare global {
  interface Window {
    __FUNDAMENTRACKER_CONFIG__?: RuntimeConfig;
  }
}

function getApiAuthToken(): string {
  const runtimeConfig = typeof window === 'undefined' ? undefined : window.__FUNDAMENTRACKER_CONFIG__;

  return (
    import.meta.env.VITE_API_AUTH_TOKEN ||
    runtimeConfig?.API_AUTH_TOKEN ||
    runtimeConfig?.VITE_API_AUTH_TOKEN ||
    ''
  );
}

export function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const token = getApiAuthToken();

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const url = path.startsWith('http://') || path.startsWith('https://') ? path : `${API_URL}${path}`;
  return fetch(url, { ...init, headers });
}
