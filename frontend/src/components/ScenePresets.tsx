import React from 'react';
import { Box, Sparkles, Sun, Orbit } from 'lucide-react';
import { ScenePreset } from '../types';

interface ScenePresetsProps {
  presets: ScenePreset[];
  activeSceneId: string;
  onSelectScene: (sceneId: string) => void;
}

export const ScenePresets: React.FC<ScenePresetsProps> = ({
  presets,
  activeSceneId,
  onSelectScene
}) => {
  const getSceneIcon = (id: string) => {
    switch (id) {
      case 'cornell-box':
        return <Box className="w-4 h-4 text-cyan-400" />;
      case 'glass-metal-showroom':
        return <Sparkles className="w-4 h-4 text-purple-400" />;
      case 'spheres-gallery':
        return <Orbit className="w-4 h-4 text-emerald-400" />;
      default:
        return <Sun className="w-4 h-4 text-amber-400" />;
    }
  };

  return (
    <div className="p-3 text-xs font-mono space-y-3">
      <div className="flex items-center justify-between text-slate-400 pb-2 border-b border-white/5">
        <span className="font-semibold text-slate-200">PHYSICAL SCENE PRESETS</span>
        <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-cyan-400">
          {presets.length} Ready
        </span>
      </div>

      <div className="space-y-2">
        {presets.map(p => {
          const isActive = p.id === activeSceneId;
          return (
            <div
              key={p.id}
              onClick={() => onSelectScene(p.id)}
              className={`p-3 rounded-lg border transition-all cursor-pointer ${
                isActive
                  ? 'bg-cyan-950/40 border-cyan-500/50 shadow-lg shadow-cyan-950/50'
                  : 'bg-slate-900/60 border-white/5 hover:bg-slate-800/60 hover:border-white/10'
              }`}
            >
              <div className="flex items-center space-x-2 mb-1.5">
                {getSceneIcon(p.id)}
                <h4 className={`font-semibold text-xs ${isActive ? 'text-cyan-300' : 'text-slate-200'}`}>
                  {p.name}
                </h4>
              </div>
              <p className="text-[10px] text-slate-400 line-clamp-2 leading-relaxed">
                {p.description}
              </p>
              <div className="mt-2 flex items-center justify-between text-[9px] text-slate-500 pt-1.5 border-t border-white/5">
                <span>FOV: {p.defaultCamera.fov}°</span>
                <span className={isActive ? 'text-emerald-400 font-bold' : ''}>
                  {isActive ? '● ACTIVE ON GPU' : 'CLICK TO LOAD'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
