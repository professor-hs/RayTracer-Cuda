import React, { useRef, useState, useEffect } from 'react';
import { Camera, Download, Maximize2, RotateCcw, Pause, Play, Sparkles } from 'lucide-react';
import { CameraConfig } from '../types';

interface ViewportProps {
  imageSrc: string | null;
  samples: number;
  fps: number;
  kernelTimeMs: number;
  width: number;
  height: number;
  camera: CameraConfig;
  onCameraChange: (newCam: CameraConfig) => void;
  isPaused: boolean;
  onTogglePause: () => void;
  onResetAccumulation: () => void;
}

export const Viewport: React.FC<ViewportProps> = ({
  imageSrc,
  samples,
  fps,
  kernelTimeMs,
  width,
  height,
  camera,
  onCameraChange,
  isPaused,
  onTogglePause,
  onResetAccumulation
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [lastMouse, setLastMouse] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Camera Orbit / Navigation via Mouse Drag
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0 || e.button === 2) {
      setIsDragging(true);
      setLastMouse({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - lastMouse.x;
    const dy = e.clientY - lastMouse.y;
    setLastMouse({ x: e.clientX, y: e.clientY });

    // Orbit around target
    const sensitivity = 0.005;
    const [px, py, pz] = camera.position;
    const [tx, ty, tz] = camera.target;

    // Spherical coordinates offset
    const rx = px - tx;
    const ry = py - ty;
    const rz = pz - tz;

    let radius = Math.sqrt(rx * rx + ry * ry + rz * rz);
    let theta = Math.atan2(rx, rz) - dx * sensitivity;
    let phi = Math.asin(Math.max(-0.99, Math.min(0.99, ry / (radius || 1)))) + dy * sensitivity;

    const newPx = tx + radius * Math.cos(phi) * Math.sin(theta);
    const newPy = ty + radius * Math.sin(phi);
    const newPz = tz + radius * Math.cos(phi) * Math.cos(theta);

    onCameraChange({
      ...camera,
      position: [newPx, newPy, newPz]
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Wheel Zoom / Dolly
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 1.05 : 0.95;
    const [px, py, pz] = camera.position;
    const [tx, ty, tz] = camera.target;

    const newPx = tx + (px - tx) * zoomFactor;
    const newPy = ty + (py - ty) * zoomFactor;
    const newPz = tz + (pz - tz) * zoomFactor;

    onCameraChange({
      ...camera,
      position: [newPx, newPy, newPz]
    });
  };

  // Download High-Res Screenshot
  const handleDownload = () => {
    if (!imageSrc) return;
    const a = document.createElement('a');
    a.href = imageSrc;
    a.download = `cuda_raytracer_${Date.now()}_spp${samples}.jpg`;
    a.click();
  };

  return (
    <div
      ref={containerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onWheel={handleWheel}
      onContextMenu={(e) => e.preventDefault()}
      className="relative flex-1 bg-black/90 flex items-center justify-center overflow-hidden cursor-grab active:cursor-grabbing select-none"
    >
      {/* Real-time Render Output Canvas */}
      {imageSrc ? (
        <img
          src={imageSrc}
          alt="CUDA Path Traced Output"
          className="max-w-full max-h-full object-contain pointer-events-none transition-opacity duration-75"
          style={{ imageRendering: samples < 4 ? 'pixelated' : 'auto' }}
        />
      ) : (
        <div className="flex flex-col items-center justify-center text-slate-500 space-y-3">
          <Sparkles className="w-10 h-10 text-cyan-500 animate-pulse" />
          <p className="text-sm font-mono tracking-wide">Initializing GPU Kernel Pipeline...</p>
        </div>
      )}

      {/* Top Left HUD: Performance Metrics */}
      <div className="absolute top-4 left-4 bg-slate-950/80 backdrop-blur-md border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-slate-300 space-y-1 shadow-xl">
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-[#00f5d4] animate-ping" />
          <span className="text-[#00f5d4] font-semibold">{width} × {height}</span>
          <span className="text-slate-600">|</span>
          <span className="text-emerald-400 font-bold">{fps.toFixed(1)} FPS</span>
        </div>
        <div className="text-[11px] text-slate-400 flex items-center space-x-2">
          <span>GPU Kernel: <strong className="text-white">{kernelTimeMs.toFixed(2)} ms</strong></span>
          <span>•</span>
          <span>SPP: <strong className="text-cyan-300">{samples}</strong></span>
        </div>
      </div>

      {/* Bottom Floating Control Bar */}
      <div className="absolute bottom-5 left-1/2 -translate-x-1/2 flex items-center space-x-2 bg-slate-950/85 backdrop-blur-lg border border-white/10 px-3 py-1.5 rounded-full shadow-2xl">
        <button
          onClick={onTogglePause}
          className={`flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-mono transition-colors ${
            isPaused ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'bg-slate-800 text-slate-200 hover:bg-slate-700'
          }`}
          title={isPaused ? "Resume Path Tracing" : "Pause Accumulation"}
        >
          {isPaused ? <Play className="w-3.5 h-3.5 text-amber-400" /> : <Pause className="w-3.5 h-3.5" />}
          <span>{isPaused ? 'RESUME' : 'PAUSE'}</span>
        </button>

        <button
          onClick={onResetAccumulation}
          className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-mono bg-slate-800 text-slate-200 hover:bg-slate-700 transition-colors"
          title="Reset Progressive Buffer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>RESET</span>
        </button>

        <div className="w-[1px] h-4 bg-white/10" />

        <button
          onClick={handleDownload}
          className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-mono bg-cyan-600/30 text-cyan-300 hover:bg-cyan-600/50 border border-cyan-500/30 transition-colors"
          title="Export PNG Screenshot"
        >
          <Download className="w-3.5 h-3.5" />
          <span>EXPORT</span>
        </button>
      </div>

      {/* Bottom-right Camera Guide */}
      <div className="hidden lg:block absolute bottom-4 right-4 text-[10px] font-mono text-slate-500 bg-slate-950/60 px-2.5 py-1 rounded border border-white/5">
        Click & Drag to Orbit • Scroll to Zoom
      </div>
    </div>
  );
};
