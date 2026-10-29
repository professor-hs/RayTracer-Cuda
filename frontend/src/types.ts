export interface GpuInfo {
  cudaAvailable: boolean;
  gpuName: string;
  computeCapability: string;
  totalMemoryMB: number;
  freeMemoryMB: number;
  multiprocessors: number;
  driverVersion: string;
  backend: string;
  hardwareAccelerated: boolean;
}

export interface RenderMetrics {
  fps: number;
  kernelTimeMs: number;
  mraysPerSecond: number;
  totalSamples: number;
  freeMemoryMB: number;
}

export interface CameraConfig {
  position: [number, number, number];
  target: [number, number, number];
  fov: number;
  aperture: number;
  focusDist: number;
}

export interface ScenePreset {
  id: string;
  name: string;
  description: string;
  defaultCamera: CameraConfig;
  skyMode: number;
}

export interface RenderJobStatus {
  jobId: string;
  status: string;
  sceneId: string;
  width: number;
  height: number;
  targetSamples: number;
  currentSamples: number;
  progressPercent: number;
  fps: number;
  kernelTimeMs: number;
  mraysPerSecond: number;
  gpu: string;
  backend: string;
}

export interface MaterialData {
  type: string; // 'Lambertian' | 'Metal' | 'Dielectric' | 'DiffuseLight'
  id: number;
  color: string;
  roughness: number;
  ior: number;
  emission: [number, number, number];
}
