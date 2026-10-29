import React, { useState } from 'react';
import { Box, Circle, Eye, Sun, Layers, ChevronRight, ChevronDown } from 'lucide-react';

interface SceneExplorerProps {
  sceneId: string;
  onSelectObject?: (objId: string) => void;
}

export const SceneExplorer: React.FC<SceneExplorerProps> = ({ sceneId, onSelectObject }) => {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    geometry: true,
    lights: true,
    materials: true
  });

  const toggle = (key: string) => {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const getSceneObjects = () => {
    if (sceneId === 'cornell-box') {
      return [
        { id: 'enclosure', name: 'Cornell Box Enclosure', type: 'Mesh (Quads)', mat: 'Red/Green/White Diffuse' },
        { id: 'bunny', name: 'Stanford Bunny Low-Poly', type: 'Polygonal Mesh (32 Tri)', mat: 'Cyan Ceramic' },
        { id: 'sphere-metal', name: 'Gold Specular Sphere', type: 'Sphere (r=0.32)', mat: 'Rough Metal (0.05)' },
        { id: 'sphere-glass', name: 'Dielectric Glass Sphere', type: 'Sphere (r=0.32)', mat: 'Refractive Glass (IOR 1.5)' },
        { id: 'ceiling-light', name: 'Ceiling Area Light', type: 'Quad Emitter', mat: 'DiffuseLight (15.0 rad)' }
      ];
    } else if (sceneId === 'glass-metal-showroom') {
      return [
        { id: 'floor', name: 'Studio Ground Plane', type: 'Quad', mat: 'Matte Charcoal' },
        { id: 'light', name: 'Overhead Softbox', type: 'Quad Emitter', mat: 'Warm DiffuseLight (12.0 rad)' },
        { id: 'silver', name: 'Silver Polished Sphere', type: 'Sphere (r=0.5)', mat: 'Specular Metal' },
        { id: 'glass-hero', name: 'Crown Glass Sphere', type: 'Sphere (r=0.5)', mat: 'Dielectric (IOR 1.52)' },
        { id: 'gold', name: 'Brushed Gold Sphere', type: 'Sphere (r=0.5)', mat: 'Rough Metal (0.25)' },
        { id: 'copper', name: 'Copper Satellite Sphere', type: 'Sphere (r=0.25)', mat: 'Polished Metal' },
        { id: 'water', name: 'Water Bubble Sphere', type: 'Sphere (r=0.25)', mat: 'Dielectric (IOR 1.33)' }
      ];
    } else if (sceneId === 'spheres-gallery') {
      return [
        { id: 'ground', name: 'Colossal Ground Sphere', type: 'Sphere (r=1000)', mat: 'Gray Diffuse' },
        { id: 'hero-glass', name: 'Center Glass Orb', type: 'Sphere (r=1.0)', mat: 'Dielectric (IOR 1.5)' },
        { id: 'hero-diffuse', name: 'Matte Brown Orb', type: 'Sphere (r=1.0)', mat: 'Lambertian' },
        { id: 'hero-metal', name: 'Glossy Steel Orb', type: 'Sphere (r=1.0)', mat: 'Specular Metal' },
        { id: 'field', name: 'Shirley Micro-Spheres (Grid)', type: 'Procedural Spheres (50+)', mat: 'Mixed PBR Materials' }
      ];
    } else {
      return [
        { id: 'stage', name: 'Dark Studio Floor', type: 'Quad', mat: 'Glossy Black Metal' },
        { id: 'neon-cyan', name: 'Neon Cyan Panel', type: 'Quad Emitter', mat: 'DiffuseLight (Cyan 15.0)' },
        { id: 'neon-magenta', name: 'Neon Magenta Panel', type: 'Quad Emitter', mat: 'DiffuseLight (Magenta 20.0)' },
        { id: 'chrome-orb', name: 'Central Mirror Orb', type: 'Sphere (r=0.8)', mat: 'Pure Chrome' },
        { id: 'satellites', name: 'Gold & Glass Orbiters', type: 'Spheres (r=0.35)', mat: 'Dielectric & Gold' }
      ];
    }
  };

  const objects = getSceneObjects();

  return (
    <div className="p-3 text-xs font-mono space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between text-slate-400 pb-2 border-b border-white/5">
        <span className="font-semibold text-slate-200">SCENE HIERARCHY</span>
        <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-cyan-400">
          {objects.length} Entities
        </span>
      </div>

      {/* Geometry Group */}
      <div className="space-y-1">
        <div
          onClick={() => toggle('geometry')}
          className="flex items-center space-x-1.5 text-slate-300 font-semibold cursor-pointer hover:text-white"
        >
          {expanded.geometry ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          <span>Active Primitives</span>
        </div>

        {expanded.geometry && (
          <div className="pl-4 space-y-1">
            {objects.map((obj) => (
              <div
                key={obj.id}
                onClick={() => onSelectObject?.(obj.id)}
                className="group flex items-center justify-between p-1.5 rounded hover:bg-slate-800/60 cursor-pointer transition-colors border border-transparent hover:border-white/5"
              >
                <div className="flex items-center space-x-2 truncate">
                  {obj.type.includes('Mesh') || obj.type.includes('Quad') ? (
                    <Box className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                  ) : obj.type.includes('Emitter') ? (
                    <Sun className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  ) : (
                    <Circle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  )}
                  <div className="truncate">
                    <p className="text-slate-200 truncate">{obj.name}</p>
                    <p className="text-[10px] text-slate-500">{obj.mat}</p>
                  </div>
                </div>
                <Eye className="w-3.5 h-3.5 text-slate-600 group-hover:text-slate-300 transition-colors" />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Spatial Acceleration Status */}
      <div className="bg-slate-900/60 border border-white/5 rounded-lg p-2.5 space-y-1.5">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-400">Spatial Index:</span>
          <span className="text-cyan-400 font-semibold">Two-Tier SAH BVH</span>
        </div>
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-400">Traversal Method:</span>
          <span className="text-emerald-400">GPU Non-Recursive Stack</span>
        </div>
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-400">Triangle Intersector:</span>
          <span className="text-slate-300">Möller-Trumbore</span>
        </div>
      </div>
    </div>
  );
};
