import React from 'react';
import { Sliders, SunMedium, Eye, Maximize } from 'lucide-react';

interface RenderControlsProps {
  width: number;
  height: number;
  onResolutionChange: (w: number, h: number) => void;
  targetSamples: number;
  onTargetSamplesChange: (samples: number) => void;
  maxBounces: number;
  onMaxBouncesChange: (bounces: number) => void;
  progressive: boolean;
  onProgressiveChange: (val: boolean) => void;
  aperture: number;
  onApertureChange: (aperture: number) => void;
  focusDist: number;
  onFocusDistChange: (dist: number) => void;
}

export const RenderControls: React.FC<RenderControlsProps> = ({
  width,
  height,
  onResolutionChange,
  targetSamples,
  onTargetSamplesChange,
  maxBounces,
  onMaxBouncesChange,
  progressive,
  onProgressiveChange,
  aperture,
  onApertureChange,
  focusDist,
  onFocusDistChange
}) => {
  const resolutions = [
    { label: '360p Preview', w: 640, h: 360 },
    { label: '540p Balanced', w: 960, h: 540 },
    { label: '720p HD', w: 1280, h: 720 },
    { label: '1080p FHD', w: 1920, h: 1080 },
    { label: '1440p 2K QHD', w: 2560, h: 1440 }
  ];

  return (
    <div className="p-3 text-xs font-mono space-y-4">
      {/* Header */}
      <div className="flex items-center space-x-2 text-slate-400 pb-2 border-b border-white/5">
        <Sliders className="w-4 h-4 text-[#00d2ff]" />
        <span className="font-semibold text-slate-200">RENDER PARAMETERS</span>
      </div>

      {/* Resolution Selector */}
      <div className="space-y-1.5">
        <label className="text-slate-400 text-[11px] flex justify-between">
          <span>Viewport Resolution:</span>
          <span className="text-cyan-400 font-semibold">{width} × {height}</span>
        </label>
        <div className="grid grid-cols-2 gap-1.5">
          {resolutions.map(r => (
            <button
              key={`${r.w}x${r.h}`}
              onClick={() => onResolutionChange(r.w, r.h)}
              className={`px-2 py-1.5 rounded text-[11px] text-center border transition-all ${
                width === r.w && height === r.h
                  ? 'bg-cyan-950/80 border-cyan-500/60 text-cyan-300 font-semibold shadow-sm'
                  : 'bg-slate-900/60 border-white/5 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Target Samples Slider */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-[11px]">
          <span className="text-slate-400">Target Samples (SPP):</span>
          <span className="text-emerald-400 font-semibold">{targetSamples} spp</span>
        </div>
        <input
          type="range"
          min="1"
          max="2000"
          step="1"
          value={targetSamples}
          onChange={(e) => onTargetSamplesChange(parseInt(e.target.value, 10))}
          className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
        />
        <div className="flex justify-between text-[9px] text-slate-500">
          <span>1 (Realtime)</span>
          <span>128</span>
          <span>512</span>
          <span>2000 (Production)</span>
        </div>
      </div>

      {/* Max Bounces Slider */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-[11px]">
          <span className="text-slate-400">Max Ray Depth:</span>
          <span className="text-purple-400 font-semibold">{maxBounces} Bounces</span>
        </div>
        <input
          type="range"
          min="1"
          max="20"
          step="1"
          value={maxBounces}
          onChange={(e) => onMaxBouncesChange(parseInt(e.target.value, 10))}
          className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
        />
        <div className="flex justify-between text-[9px] text-slate-500">
          <span>1 Direct</span>
          <span>8 Standard</span>
          <span>20 Caustic / GI</span>
        </div>
      </div>

      {/* Thin-Lens Optics (Aperture & Focus) */}
      <div className="border-t border-white/5 pt-3 space-y-3">
        <div className="text-[11px] text-slate-300 font-semibold flex items-center space-x-1.5">
          <Eye className="w-3.5 h-3.5 text-cyan-400" />
          <span>Thin-Lens Optics (Depth of Field)</span>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-[11px]">
            <span className="text-slate-400">Lens Aperture:</span>
            <span className="text-cyan-300 font-mono">{aperture.toFixed(4)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="0.2"
            step="0.005"
            value={aperture}
            onChange={(e) => onApertureChange(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
          />
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-[11px]">
            <span className="text-slate-400">Focal Distance:</span>
            <span className="text-cyan-300 font-mono">{focusDist.toFixed(2)} m</span>
          </div>
          <input
            type="range"
            min="0.5"
            max="10.0"
            step="0.1"
            value={focusDist}
            onChange={(e) => onFocusDistChange(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
          />
        </div>
      </div>

      {/* Progressive Accumulation Switch */}
      <div className="border-t border-white/5 pt-3 flex items-center justify-between">
        <div>
          <p className="text-[11px] text-slate-200">Progressive Accumulation</p>
          <p className="text-[9px] text-slate-500">Temporal sample blending (TDR-Safe)</p>
        </div>
        <input
          type="checkbox"
          checked={progressive}
          onChange={(e) => onProgressiveChange(e.target.checked)}
          className="w-4 h-4 rounded bg-slate-800 border-white/20 text-[#00f5d4] focus:ring-0"
        />
      </div>
    </div>
  );
};
