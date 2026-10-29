import React from 'react';
import { Activity, Cpu, HardDrive, Gauge, Zap } from 'lucide-react';
import { GpuInfo, RenderMetrics } from '../types';

interface PerformancePanelProps {
  gpuInfo: GpuInfo | null;
  metrics: RenderMetrics;
  samples: number;
  targetSamples: number;
}

export const PerformancePanel: React.FC<PerformancePanelProps> = ({
  gpuInfo,
  metrics,
  samples,
  targetSamples
}) => {
  const progressPercent = Math.min(100, Math.round((samples / Math.max(targetSamples, 1)) * 100));

  return (
    <div className="p-3 text-xs font-mono space-y-4">
      {/* Header */}
      <div className="flex items-center space-x-2 text-slate-400 pb-2 border-b border-white/5">
        <Activity className="w-4 h-4 text-emerald-400" />
        <span className="font-semibold text-slate-200">GPU TELEMETRY & PROFILER</span>
      </div>

      {/* Primary Convergence Progress */}
      <div className="space-y-1.5 bg-slate-900/60 border border-white/5 p-2.5 rounded-lg">
        <div className="flex justify-between text-[11px]">
          <span className="text-slate-400">Monte Carlo Convergence:</span>
          <span className="text-[#00f5d4] font-bold">{progressPercent}%</span>
        </div>
        <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-cyan-500 via-blue-500 to-emerald-400 transition-all duration-150"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-slate-500">
          <span>{samples} SPP Completed</span>
          <span>Target: {targetSamples} SPP</span>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-slate-900/60 border border-white/5 p-2.5 rounded-lg space-y-1">
          <div className="flex items-center space-x-1.5 text-slate-400 text-[10px]">
            <Gauge className="w-3.5 h-3.5 text-emerald-400" />
            <span>RENDER FPS</span>
          </div>
          <p className="text-lg font-bold text-emerald-400">{metrics.fps.toFixed(1)}</p>
          <p className="text-[9px] text-slate-500">Viewport Framerate</p>
        </div>

        <div className="bg-slate-900/60 border border-white/5 p-2.5 rounded-lg space-y-1">
          <div className="flex items-center space-x-1.5 text-slate-400 text-[10px]">
            <Zap className="w-3.5 h-3.5 text-cyan-400" />
            <span>KERNEL TIME</span>
          </div>
          <p className="text-lg font-bold text-cyan-300">{metrics.kernelTimeMs.toFixed(2)} ms</p>
          <p className="text-[9px] text-slate-500">GPU Pass Duration</p>
        </div>

        <div className="bg-slate-900/60 border border-white/5 p-2.5 rounded-lg space-y-1">
          <div className="flex items-center space-x-1.5 text-slate-400 text-[10px]">
            <Activity className="w-3.5 h-3.5 text-purple-400" />
            <span>THROUGHPUT</span>
          </div>
          <p className="text-lg font-bold text-purple-400">{metrics.mraysPerSecond.toFixed(1)}</p>
          <p className="text-[9px] text-slate-500">MRays / Second</p>
        </div>

        <div className="bg-slate-900/60 border border-white/5 p-2.5 rounded-lg space-y-1">
          <div className="flex items-center space-x-1.5 text-slate-400 text-[10px]">
            <HardDrive className="w-3.5 h-3.5 text-amber-400" />
            <span>VRAM TOTAL</span>
          </div>
          <p className="text-lg font-bold text-amber-300">{gpuInfo ? `${gpuInfo.totalMemoryMB.toFixed(0)} MB` : '4096 MB'}</p>
          <p className="text-[9px] text-slate-500">GDDR6 Dedicated</p>
        </div>
      </div>

      {/* Hardware Audit Box */}
      <div className="bg-slate-900/60 border border-white/5 rounded-lg p-2.5 space-y-1.5 text-[11px]">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Device:</span>
          <span className="text-slate-200 font-semibold truncate max-w-[150px]">{gpuInfo?.gpuName || "RTX 3050"}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Compute Capability:</span>
          <span className="text-cyan-400">SM {gpuInfo?.computeCapability || "8.6"}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Multiprocessors:</span>
          <span className="text-slate-300">{gpuInfo?.multiprocessors || 16} SMs</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Acceleration Backend:</span>
          <span className="px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/40 text-[9px] font-bold">
            {gpuInfo?.backend.toUpperCase() || "CUDA_GPU"}
          </span>
        </div>
      </div>
    </div>
  );
};
