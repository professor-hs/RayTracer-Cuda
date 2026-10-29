// =============================================================================
// CENTRALIZED API CLIENT & WEBSOCKET ENGINE CONNECTOR
// =============================================================================

import { GpuInfo, ScenePreset, RenderJobStatus, CameraConfig } from './types';

export function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const custom = localStorage.getItem('cuda_raytracer_api_url');
    if (custom && custom.trim().length > 0) {
      return custom.trim().replace(/\/+$/, '');
    }
  }
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? 'http://127.0.0.1:8080'
    : '';
}

export function setApiBaseUrl(url: string | null): void {
  if (typeof window === 'undefined') return;
  if (url && url.trim().length > 0) {
    localStorage.setItem('cuda_raytracer_api_url', url.trim().replace(/\/+$/, ''));
  } else {
    localStorage.removeItem('cuda_raytracer_api_url');
  }
}

export const api = {
  getBaseUrl() {
    return getApiBaseUrl();
  },

  async getHealth() {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/v1/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return res.json();
  },

  async getGpuInfo(): Promise<GpuInfo> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/v1/gpu`);
    if (!res.ok) throw new Error(`Failed to fetch GPU info: ${res.statusText}`);
    return res.json();
  },

  async getCapabilities() {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/v1/capabilities`);
    if (!res.ok) throw new Error(`Failed to fetch capabilities: ${res.statusText}`);
    return res.json();
  },

  async getScenes(): Promise<ScenePreset[]> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/v1/scenes`);
    if (!res.ok) throw new Error(`Failed to fetch scenes: ${res.statusText}`);
    const data = await res.json();
    return data.scenes;
  },

  async getSceneDetails(id: string) {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/v1/scenes/${id}`);
    if (!res.ok) throw new Error(`Failed to fetch scene details: ${res.statusText}`);
    return res.json();
  },

  async getMaterials() {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/v1/materials`);
    if (!res.ok) throw new Error(`Failed to fetch materials: ${res.statusText}`);
    return res.json();
  },

  async startRender(config: {
    sceneId: string;
    width: number;
    height: number;
    samplesPerPixel: number;
    maxBounces: number;
    progressive: boolean;
    camera?: CameraConfig;
  }) {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/v1/render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    if (!res.ok) throw new Error(`Failed to start render: ${res.statusText}`);
    return res.json();
  },

  async getJobStatus(jobId: string): Promise<RenderJobStatus> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/v1/render/${jobId}`);
    if (!res.ok) throw new Error(`Failed to fetch job status: ${res.statusText}`);
    return res.json();
  },

  async cancelJob(jobId: string) {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/v1/render/${jobId}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error(`Failed to cancel job: ${res.statusText}`);
    return res.json();
  },

  getImageUrl(jobId: string, format: 'png' | 'jpeg' = 'png') {
    const base = getApiBaseUrl();
    return `${base}/api/v1/render/${jobId}/image?format=${format}&t=${Date.now()}`;
  },

  getWebSocketUrl(jobId: string = 'default') {
    const base = getApiBaseUrl();
    if (base.startsWith('http://') || base.startsWith('https://')) {
      const isHttps = base.startsWith('https://');
      const wsProto = isHttps ? 'wss:' : 'ws:';
      const host = base.replace(/^https?:\/\//, '');
      return `${wsProto}//${host}/api/v1/ws/render/${jobId}`;
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/api/v1/ws/render/${jobId}`;
  }
};
