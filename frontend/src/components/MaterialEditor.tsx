import React, { useState } from 'react';
import { Palette, Sparkles, Sun, Droplet } from 'lucide-react';

export const MaterialEditor: React.FC = () => {
  const [selectedType, setSelectedType] = useState<number>(0);
  const [albedo, setAlbedo] = useState<string>('#00d2ff');
  const [roughness, setRoughness] = useState<number>(0.05);
  const [ior, setIor] = useState<number>(1.52);
  const [emission, setEmission] = useState<number>(12.0);

  const materials = [
    { id: 0, name: 'Lambertian Diffuse', desc: 'Cosine-weighted matte surface' },
    { id: 1, name: 'Specular Metal', desc: 'Microfacet reflection with roughness' },
    { id: 2, name: 'Dielectric Glass', desc: 'Snell refraction & Schlick Fresnel' },
    { id: 3, name: 'DiffuseLight', desc: 'Unattenuated area light emitter' }
  ];

  return (
    <div className="p-3 text-xs font-mono space-y-4">
      {/* Header */}
      <div className="flex items-center space-x-2 text-slate-400 pb-2 border-b border-white/5">
        <Palette className="w-4 h-4 text-[#7928ca]" />
        <span className="font-semibold text-slate-200">PHYSICAL MATERIAL INSPECTOR</span>
      </div>

      {/* Material Type Pills */}
      <div className="grid grid-cols-2 gap-1.5">
        {materials.map(m => (
          <button
            key={m.id}
            onClick={() => setSelectedType(m.id)}
            className={`p-2 rounded text-left border transition-all ${
              selectedType === m.id
                ? 'bg-purple-950/60 border-purple-500/50 text-purple-300 font-semibold shadow-sm'
                : 'bg-slate-900/60 border-white/5 text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <p className="text-[11px] truncate">{m.name}</p>
            <p className="text-[9px] text-slate-500 truncate">{m.desc}</p>
          </button>
        ))}
      </div>

      {/* Parameters based on type */}
      {selectedType !== 3 && (
        <div className="space-y-1.5">
          <label className="text-slate-400 text-[11px] flex justify-between">
            <span>Base Albedo Tint:</span>
            <span className="font-mono text-cyan-300">{albedo}</span>
          </label>
          <div className="flex items-center space-x-2">
            <input
              type="color"
              value={albedo}
              onChange={(e) => setAlbedo(e.target.value)}
              className="w-8 h-8 rounded border-0 bg-transparent cursor-pointer"
            />
            <input
              type="text"
              value={albedo}
              onChange={(e) => setAlbedo(e.target.value)}
              className="flex-1 bg-slate-900/80 border border-white/10 rounded px-2 py-1 text-[11px] text-slate-200"
            />
          </div>
        </div>
      )}

      {selectedType === 1 && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-[11px]">
            <span className="text-slate-400">Microfacet Roughness:</span>
            <span className="text-amber-400 font-semibold">{roughness.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={roughness}
            onChange={(e) => setRoughness(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-[9px] text-slate-500">
            <span>Mirror (0.0)</span>
            <span>Satin</span>
            <span>Rough (1.0)</span>
          </div>
        </div>
      )}

      {selectedType === 2 && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-[11px]">
            <span className="text-slate-400">Index of Refraction (IOR):</span>
            <span className="text-cyan-400 font-semibold">{ior.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="1.0"
            max="2.5"
            step="0.01"
            value={ior}
            onChange={(e) => setIor(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-[9px] text-slate-500">
            <span>Air (1.0)</span>
            <span>Water (1.33)</span>
            <span>Glass (1.52)</span>
            <span>Diamond (2.42)</span>
          </div>
        </div>
      )}

      {selectedType === 3 && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-[11px]">
            <span className="text-slate-400">Emission Intensity:</span>
            <span className="text-amber-300 font-semibold">{emission.toFixed(1)} Lux</span>
          </div>
          <input
            type="range"
            min="1.0"
            max="30.0"
            step="0.5"
            value={emission}
            onChange={(e) => setEmission(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
          />
        </div>
      )}

      {/* Physics Notation */}
      <div className="bg-slate-900/60 border border-white/5 rounded-lg p-2.5 text-[10px] text-slate-400 space-y-1">
        <p className="text-slate-300 font-semibold">BRDF Formulation:</p>
        <p>Evaluated using Monte Carlo hemispherical integration with Russian Roulette survival weighting.</p>
      </div>
    </div>
  );
};
