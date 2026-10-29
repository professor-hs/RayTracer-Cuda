import React from 'react';
import { Cpu, Zap, Activity, ShieldCheck, RefreshCw, Layers } from 'lucide-react';
import { GpuInfo } from '../types';

interface TopNavProps {
  gpuInfo: GpuInfo | null;
  isConnected: boolean;
  isRendering: boolean;
  samples: number;
  onRefresh: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({
  gpuInfo,
  isConnected,
  isRendering,
  samples,
  onRefresh
}) => {
  return (
    <header className="h-14 border-b border-white/10 bg-[#0d1326]/90 backdrop-blur-md px-4 flex items-center justify-between z-30 select-none">
      {/* Brand & Title */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#7928ca] to-[#00d2ff] p-0.5 shadow-lg shadow-cyan-500/20 flex items-center justify-center">
          <div className="w-full h-full bg-[#0a0f1d] rounded-[7px] flex items-center justify-center">
            <Zap className="w-4 h-4 text-[#00f5d4]" />
          </div>
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="font-bold text-sm tracking-wide text-white">CUDA RAY TRACER</h1>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/50">
              v2.0 PRO
            </span>
          </div>
          <p className="text-[10px] text-slate-400 font-mono tracking-tight">NVIDIA AMPERE PATH TRACING WORKSTATION</p>
        </div>
      </div>

      {/* Center Hardware Indicator */}
      <div className="hidden md:flex items-center space-x-3 bg-slate-900/60 border border-white/5 rounded-full px-3 py-1">
        <div className="flex items-center space-x-1.5">
          <Cpu className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-xs font-medium text-slate-200">
            {gpuInfo?.gpuName || "Detecting Hardware..."}
          </span>
        </div>
        {gpuInfo?.cudaAvailable && (
          <>
            <span className="text-slate-600">•</span>
            <span className="text-[11px] font-mono text-cyan-400">
              Compute {gpuInfo.computeCapability}
            </span>
            <span className="text-slate-600">•</span>
            <span className="text-[11px] font-mono text-emerald-400">
              {gpuInfo.totalMemoryMB.toFixed(0)} MB VRAM
            </span>
          </>
        )}
      </div>

      {/* Right Controls & Telemetry */}
      <div className="flex items-center space-x-3">
        {/* Connection Status Pill */}
        <div className="flex items-center space-x-1.5 bg-slate-900/80 border border-white/5 px-2.5 py-1 rounded-md text-xs font-mono">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
          <span className={isConnected ? 'text-emerald-300' : 'text-rose-400'}>
            {isConnected ? 'ONLINE' : 'DISCONNECTED'}
          </span>
        </div>

        {/* Render Mode Badge */}
        <div className="hidden sm:flex items-center space-x-1.5 bg-cyan-950/40 border border-cyan-800/40 px-2.5 py-1 rounded-md text-xs font-mono text-cyan-300">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span>{isRendering ? `SAMPLES: ${samples}` : 'IDLE'}</span>
        </div>

        {/* Quick Refresh */}
        <button
          onClick={onRefresh}
          title="Reset GPU Accumulation & Re-render"
          className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
