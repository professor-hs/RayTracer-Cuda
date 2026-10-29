// =============================================================================
// CENTRALIZED API CLIENT & WEBSOCKET ENGINE CONNECTOR
// =============================================================================

import { GpuInfo, ScenePreset, RenderJobStatus, CameraConfig } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || (
  window.location.hostname === 'localhost' ? 'http://127.0.0.1:8080' : ''
);

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE}/api/v1/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return res.json();
  },

  async getGpuInfo(): Promise<GpuInfo> {
    const res = await fetch(`${API_BASE}/api/v1/gpu`);
    if (!res.ok) throw new Error(`Failed to fetch GPU info: ${res.statusText}`);
    return res.json();
  },

  async getCapabilities() {
    const res = await fetch(`${API_BASE}/api/v1/capabilities`);
    if (!res.ok) throw new Error(`Failed to fetch capabilities: ${res.statusText}`);
    return res.json();
  },

  async getScenes(): Promise<ScenePreset[]> {
    const res = await fetch(`${API_BASE}/api/v1/scenes`);
    if (!res.ok) throw new Error(`Failed to fetch scenes: ${res.statusText}`);
    const data = await res.json();
    return data.scenes;
  },

  async getSceneDetails(id: string) {
    const res = await fetch(`${API_BASE}/api/v1/scenes/${id}`);
    if (!res.ok) throw new Error(`Failed to fetch scene details: ${res.statusText}`);
    return res.json();
  },

  async getMaterials() {
    const res = await fetch(`${API_BASE}/api/v1/materials`);
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
    const res = await fetch(`${API_BASE}/api/v1/render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    if (!res.ok) throw new Error(`Failed to start render: ${res.statusText}`);
    return res.json();
  },

  async getJobStatus(jobId: string): Promise<RenderJobStatus> {
    const res = await fetch(`${API_BASE}/api/v1/render/${jobId}`);
    if (!res.ok) throw new Error(`Failed to fetch job status: ${res.statusText}`);
    return res.json();
  },

  async cancelJob(jobId: string) {
    const res = await fetch(`${API_BASE}/api/v1/render/${jobId}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error(`Failed to cancel job: ${res.statusText}`);
    return res.json();
  },

  getImageUrl(jobId: string) {
    return `${API_BASE}/api/v1/render/${jobId}/image?t=${Date.now()}`;
  },

  getWebSocketUrl(jobId: string = 'default') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    if (API_BASE.startsWith('http')) {
      const url = new URL(API_BASE);
      return `${url.protocol === 'https:' ? 'wss:' : 'ws:'}//${url.host}/api/v1/ws/render/${jobId}`;
    }
    return `${protocol}//${window.location.host}/api/v1/ws/render/${jobId}`;
  }
};
