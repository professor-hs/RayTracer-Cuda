import React, { useState, useEffect, useRef, useCallback } from 'react';
import { TopNav } from './components/TopNav';
import { Viewport } from './components/Viewport';
import { SceneExplorer } from './components/SceneExplorer';
import { RenderControls } from './components/RenderControls';
import { MaterialEditor } from './components/MaterialEditor';
import { PerformancePanel } from './components/PerformancePanel';
import { ScenePresets } from './components/ScenePresets';
import { api } from './api';
import { GpuInfo, RenderMetrics, CameraConfig, ScenePreset } from './types';
import { Layers, Sliders, Palette, Activity, Box, Settings } from 'lucide-react';

export const App: React.FC = () => {
  // Backend & GPU State
  const [gpuInfo, setGpuInfo] = useState<GpuInfo | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [scenes, setScenes] = useState<ScenePreset[]>([]);
  const [activeSceneId, setActiveSceneId] = useState<string>('cornell-box');

  // Viewport & Rendering State
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [samples, setSamples] = useState<number>(0);
  const [targetSamples, setTargetSamples] = useState<number>(256);
  const [maxBounces, setMaxBounces] = useState<number>(10);
  const [width, setWidth] = useState<number>(960);
  const [height, setHeight] = useState<number>(540);
  const [progressive, setProgressive] = useState<boolean>(true);
  const [isPaused, setIsPaused] = useState<boolean>(false);

  // Camera State
  const [camera, setCamera] = useState<CameraConfig>({
    position: [0.0, 1.0, 3.2],
    target: [0.0, 1.0, 0.0],
    fov: 45.0,
    aperture: 0.00001,
    focusDist: 3.2
  });

  // Performance Telemetry
  const [metrics, setMetrics] = useState<RenderMetrics>({
    fps: 0,
    kernelTimeMs: 0,
    mraysPerSecond: 0,
    totalSamples: 0,
    freeMemoryMB: 0
  });

  // UI Tabs
  const [leftTab, setLeftTab] = useState<'explorer' | 'presets'>('presets');
  const [rightTab, setRightTab] = useState<'controls' | 'materials' | 'performance'>('controls');

  // WebSocket Ref
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  // Initial Hardware & Scene Fetch
  useEffect(() => {
    const initBackend = async () => {
      try {
        const gpu = await api.getGpuInfo();
        setGpuInfo(gpu);
        setIsConnected(true);

        const sceneList = await api.getScenes();
        setScenes(sceneList);
      } catch (err) {
        console.warn("Backend not yet connected:", err);
        setIsConnected(false);
      }
    };
    initBackend();
  }, []);

  // WebSocket Streaming Connection
  const connectWebSocket = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    try {
      const wsUrl = api.getWebSocketUrl('default');
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        console.log("[WS] Connected to CUDA raytracer stream.");
        // Send initial config
        ws.send(JSON.stringify({
          action: 'config',
          width,
          height,
          maxBounces,
          samplesPerFrame: 1
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'frame') {
            setImageSrc(data.image);
            setSamples(data.samples);
            setMetrics({
              fps: data.fps,
              kernelTimeMs: data.kernelTimeMs,
              mraysPerSecond: data.mraysPerSec,
              totalSamples: data.samples,
              freeMemoryMB: data.freeMemoryMB
            });
          }
        } catch (e) {
          console.error("Frame decode error:", e);
        }
      };

      ws.onerror = (e) => {
        console.warn("[WS] Socket error:", e);
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Attempt reconnect in 2 seconds
        reconnectTimeoutRef.current = window.setTimeout(connectWebSocket, 2000);
      };

      wsRef.current = ws;
    } catch (e) {
      console.warn("WS connection setup failed:", e);
    }
  }, [width, height, maxBounces]);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, [connectWebSocket]);

  // Send Camera Updates over WebSocket
  const handleCameraChange = (newCam: CameraConfig) => {
    setCamera(newCam);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'camera',
        camera: newCam
      }));
    }
  };

  // Change Scene Preset
  const handleSelectScene = (sceneId: string) => {
    setActiveSceneId(sceneId);
    // Find preset camera
    const preset = scenes.find(s => s.id === sceneId);
    if (preset) {
      setCamera(preset.defaultCamera);
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'scene',
        sceneId
      }));
    }
  };

  // Reset GPU Accumulation Buffer
  const handleResetAccumulation = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'reset' }));
    }
    setSamples(0);
  };

  // Resolution Change
  const handleResolutionChange = (w: number, h: number) => {
    setWidth(w);
    setHeight(h);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'config',
        width: w,
        height: h
      }));
    }
    handleResetAccumulation();
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[#0a0f1d] text-slate-100 overflow-hidden font-sans">
      {/* Top Header */}
      <TopNav
        gpuInfo={gpuInfo}
        isConnected={isConnected}
        isRendering={!isPaused && samples < targetSamples}
        samples={samples}
        onRefresh={handleResetAccumulation}
      />

      {/* Main Workspace Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Technical Panel (Scene Hierarchy & Presets) */}
        <aside className="w-72 bg-[#0d1326]/90 backdrop-blur-md border-r border-white/5 flex flex-col shrink-0 z-10">
          {/* Tab Switcher */}
          <div className="flex border-b border-white/5 bg-slate-950/40 text-xs font-mono">
            <button
              onClick={() => setLeftTab('presets')}
              className={`flex-1 py-2 flex items-center justify-center space-x-1.5 transition-colors border-b-2 ${
                leftTab === 'presets'
                  ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Box className="w-3.5 h-3.5" />
              <span>PRESETS</span>
            </button>
            <button
              onClick={() => setLeftTab('explorer')}
              className={`flex-1 py-2 flex items-center justify-center space-x-1.5 transition-colors border-b-2 ${
                leftTab === 'explorer'
                  ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>SCENE TREE</span>
            </button>
          </div>

          {/* Panel Content */}
          <div className="flex-1 overflow-y-auto">
            {leftTab === 'presets' ? (
              <ScenePresets
                presets={scenes}
                activeSceneId={activeSceneId}
                onSelectScene={handleSelectScene}
              />
            ) : (
              <SceneExplorer sceneId={activeSceneId} />
            )}
          </div>
        </aside>

        {/* Center Canvas Viewport */}
        <main className="flex-1 flex flex-col relative overflow-hidden bg-black/95">
          <Viewport
            imageSrc={imageSrc}
            samples={samples}
            fps={metrics.fps}
            kernelTimeMs={metrics.kernelTimeMs}
            width={width}
            height={height}
            camera={camera}
            onCameraChange={handleCameraChange}
            isPaused={isPaused}
            onTogglePause={() => setIsPaused(!isPaused)}
            onResetAccumulation={handleResetAccumulation}
            isConnected={isConnected}
          />
        </main>

        {/* Right Studio Panel (Parameters, Materials, Profiler) */}
        <aside className="w-80 bg-[#0d1326]/90 backdrop-blur-md border-l border-white/5 flex flex-col shrink-0 z-10">
          {/* Tab Switcher */}
          <div className="flex border-b border-white/5 bg-slate-950/40 text-xs font-mono">
            <button
              onClick={() => setRightTab('controls')}
              className={`flex-1 py-2 flex items-center justify-center space-x-1 transition-colors border-b-2 ${
                rightTab === 'controls'
                  ? 'border-[#00d2ff] text-[#00d2ff] bg-cyan-950/20 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
              title="Render Parameters"
            >
              <Sliders className="w-3.5 h-3.5" />
              <span>PARAMS</span>
            </button>
            <button
              onClick={() => setRightTab('materials')}
              className={`flex-1 py-2 flex items-center justify-center space-x-1 transition-colors border-b-2 ${
                rightTab === 'materials'
                  ? 'border-[#7928ca] text-purple-300 bg-purple-950/20 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
              title="Material Inspector"
            >
              <Palette className="w-3.5 h-3.5" />
              <span>MATERIAL</span>
            </button>
            <button
              onClick={() => setRightTab('performance')}
              className={`flex-1 py-2 flex items-center justify-center space-x-1 transition-colors border-b-2 ${
                rightTab === 'performance'
                  ? 'border-emerald-400 text-emerald-300 bg-emerald-950/20 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
              title="GPU Profiler"
            >
              <Activity className="w-3.5 h-3.5" />
              <span>STATS</span>
            </button>
          </div>

          {/* Panel Content */}
          <div className="flex-1 overflow-y-auto">
            {rightTab === 'controls' && (
              <RenderControls
                width={width}
                height={height}
                onResolutionChange={handleResolutionChange}
                targetSamples={targetSamples}
                onTargetSamplesChange={setTargetSamples}
                maxBounces={maxBounces}
                onMaxBouncesChange={(b) => {
                  setMaxBounces(b);
                  if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                    wsRef.current.send(JSON.stringify({ action: 'config', maxBounces: b }));
                  }
                  handleResetAccumulation();
                }}
                progressive={progressive}
                onProgressiveChange={setProgressive}
                aperture={camera.aperture}
                onApertureChange={(ap) => handleCameraChange({ ...camera, aperture: ap })}
                focusDist={camera.focusDist}
                onFocusDistChange={(fd) => handleCameraChange({ ...camera, focusDist: fd })}
              />
            )}
            {rightTab === 'materials' && <MaterialEditor />}
            {rightTab === 'performance' && (
              <PerformancePanel
                gpuInfo={gpuInfo}
                metrics={metrics}
                samples={samples}
                targetSamples={targetSamples}
              />
            )}
          </div>
        </aside>
      </div>
    </div>
  );
};
