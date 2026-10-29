import React, { useState } from 'react';
import { Cpu, Zap, Activity, RefreshCw, Settings, Globe, Check, AlertCircle, X } from 'lucide-react';
import { GpuInfo } from '../types';
import { getApiBaseUrl, setApiBaseUrl, api } from '../api';

interface TopNavProps {
  gpuInfo: GpuInfo | null;
  isConnected: boolean;
  isRendering: boolean;
  samples: number;
  onRefresh: () => void;
  onEndpointChange?: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({
  gpuInfo,
  isConnected,
  isRendering,
  samples,
  onRefresh,
  onEndpointChange
}) => {
  const [showConfig, setShowConfig] = useState(false);
  const [customUrl, setCustomUrl] = useState(getApiBaseUrl());
  const [testStatus, setTestStatus] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  const handleTestConnection = async () => {
    setTesting(true);
    setTestStatus(null);
    try {
      const url = customUrl.trim().replace(/\/+$/, '');
      const res = await fetch(`${url}/api/v1/health`, { signal: AbortSignal.timeout(4000) });
      if (res.ok) {
        const data = await res.json();
        setTestStatus(`Connected! GPU: ${data.gpuName} (${data.backend})`);
      } else {
        setTestStatus(`Failed: HTTP ${res.status}`);
      }
    } catch (err: any) {
      setTestStatus(`Connection error: ${err.message || 'Host unreachable'}`);
    } finally {
      setTesting(false);
    }
  };

  const handleSaveEndpoint = () => {
    setApiBaseUrl(customUrl.trim());
    setShowConfig(false);
    onEndpointChange?.();
    window.location.reload();
  };

  const handleResetToDefault = () => {
    setApiBaseUrl(null);
    setCustomUrl(getApiBaseUrl());
    setShowConfig(false);
    onEndpointChange?.();
    window.location.reload();
  };

  return (
    <>
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
            <Cpu className={`w-3.5 h-3.5 ${gpuInfo?.cudaAvailable ? 'text-emerald-400' : 'text-amber-400'}`} />
            <span className="text-xs font-medium text-slate-200">
              {gpuInfo?.gpuName || (isConnected ? "No GPU Detected" : "Connecting to Backend...")}
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
          <button
            onClick={() => setShowConfig(true)}
            className="flex items-center space-x-1.5 bg-slate-900/80 border border-white/10 px-2.5 py-1 rounded-md text-xs font-mono hover:bg-slate-800 transition-colors"
            title="Configure Backend API URL"
          >
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
            <span className={isConnected ? 'text-emerald-300' : 'text-rose-400'}>
              {isConnected ? 'ONLINE' : 'OFFLINE'}
            </span>
            <Settings className="w-3 h-3 text-slate-400 ml-1" />
          </button>

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

      {/* Backend Connection Modal */}
      {showConfig && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0e1629] border border-cyan-500/30 rounded-xl p-5 max-w-md w-full shadow-2xl space-y-4 font-mono text-xs">
            <div className="flex justify-between items-center border-b border-white/10 pb-3">
              <div className="flex items-center space-x-2 text-cyan-400 font-bold text-sm">
                <Globe className="w-4 h-4" />
                <span>BACKEND API CONFIGURATION</span>
              </div>
              <button onClick={() => setShowConfig(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-slate-300 text-[11px] leading-relaxed">
              Connect this workstation interface to either your publicly hosted GPU backend (e.g. Render/RunPod/Cloud GPU) or local CUDA service.
            </p>

            <div className="space-y-1.5">
              <label className="text-slate-400 text-[11px]">Backend API Base URL:</label>
              <input
                type="text"
                value={customUrl}
                onChange={(e) => setCustomUrl(e.target.value)}
                placeholder="https://your-public-gpu-backend.com or http://localhost:8080"
                className="w-full bg-slate-950 border border-white/20 rounded-md p-2 text-slate-200 text-xs focus:outline-none focus:border-cyan-400"
              />
            </div>

            {testStatus && (
              <div className={`p-2.5 rounded text-[11px] flex items-center space-x-2 ${
                testStatus.startsWith('Connected')
                  ? 'bg-emerald-950/60 border border-emerald-500/40 text-emerald-300'
                  : 'bg-rose-950/60 border border-rose-500/40 text-rose-300'
              }`}>
                {testStatus.startsWith('Connected') ? <Check className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
                <span className="truncate">{testStatus}</span>
              </div>
            )}

            <div className="flex space-x-2 pt-2">
              <button
                onClick={handleTestConnection}
                disabled={testing}
                className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-200 py-2 rounded-md font-semibold transition-colors disabled:opacity-50"
              >
                {testing ? 'Testing...' : 'Test Connection'}
              </button>
              <button
                onClick={handleSaveEndpoint}
                className="flex-1 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white py-2 rounded-md font-semibold transition-colors shadow-lg shadow-cyan-600/30"
              >
                Apply & Reload
              </button>
            </div>

            <div className="flex justify-between items-center text-[10px] text-slate-500 pt-1">
              <button
                onClick={() => setCustomUrl('http://localhost:8080')}
                className="hover:text-cyan-400 underline"
              >
                Use Localhost (Port 8080)
              </button>
              <button
                onClick={handleResetToDefault}
                className="hover:text-amber-400 underline"
              >
                Reset to Default (.env)
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
