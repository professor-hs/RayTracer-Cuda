# System Architecture: CUDA-Accelerated Ray Tracer

## 1. Overview & Architectural Vision
The **CUDA-Accelerated Ray Tracer** is a high-performance physically based path tracer designed to deliver interactive, physically accurate global illumination on NVIDIA GPUs. It couples a low-latency GPU path tracing pipeline with a modern desktop-inspired web interface, providing real-time progressive accumulation, spatial acceleration, and rich material physics.

```
+-------------------------------------------------------------------------------+
|                       CUDA Ray Tracer Architecture                            |
+-------------------------------------------------------------------------------+

[ Browser Client: React 18 + TypeScript + Vite + Tailwind ]
                             |
                   HTTP REST | WebSocket
                             v
[ Native Backend Server: Starlette + Uvicorn Async Server ]
                             |
                  ctypes IPC | Driver API
                             v
[ CUDA Engine Controller: CudaEngine (nvcuda.dll) ]
                             |
             Module JIT Load | PTX Kernel Execution
                             v
[ NVIDIA GeForce RTX 3050 Laptop GPU: Ampere SM 8.6 ]
   - 2D Tile Execution (16 x 16 Warps)
   - Temporal Progressive Accumulation (float4 VRAM Buffer)
   - Two-Tier Surface Area Heuristic (SAH) BVH Traversal
   - Möller-Trumbore Ray-Triangle & Analytic Sphere Intersections
   - Microfacet PBR Materials (Lambertian, Metal, Dielectric, DiffuseLight)
   - Russian Roulette Energy Termination
                             |
             Host-Device DtoH | Zero-Flip Output Mapping
                             v
[ Base64 JPEG / Binary Frame Buffer -> Display Canvas ]
```

---

## 2. Core Subsystems

### 2.1 GPU Kernel Pipeline (`raytracer_kernel.cu`)
The GPU execution logic is written in high-performance CUDA/C++ and compiled into NVIDIA PTX (`.ptx`) assembly targeting Ampere architecture (`sm_86`).

- **Ray Generation**: Implements a thin-lens camera model with configurable aperture radius, focal plane distance, and field of view. Sub-pixel anti-aliasing is achieved by stochastically jittering ray targets across pixel apertures using per-pixel PCG32 random number generators.
- **Ray-Scene Intersection**:
  - **Triangles**: Evaluated using the Möller-Trumbore intersection algorithm, solving for barycentric coordinates $(u, v)$ and ray parameter $t$ via determinant calculations without auxiliary plane storage.
  - **Spheres**: Evaluated analytically using the quadratic discriminant formulation with early negative discriminant rejection.
- **Spatial Acceleration (BVH)**:
  - Traversal is strictly non-recursive to eliminate GPU register spilling and call stack limits.
  - An integer array stack (`int stack[64]`) maintains unvisited child nodes.
  - Nodes test Ray-AABB intersection using coordinate slab logic ($t_{\min}, t_{\max}$) before evaluating contained primitives.
- **Physical Materials**:
  - **Lambertian**: Cosine-weighted hemispherical scattering via unit sphere surface rejection.
  - **Metal**: Law of reflection perturbed by microfacet roughness $\sigma \in [0, 1]$.
  - **Dielectric**: Snell's law refraction, internal reflection detection, and Fresnel reflectance estimated via Schlick's approximation.
  - **DiffuseLight**: Terminal emissive area lighting returning unattenuated radiance.
- **Russian Roulette Termination**:
  - Paths undergo unbiased probabilistic termination starting at bounce 3.
  - Survival probability: $P = \min(\max(R, G, B), 0.95)$.
  - Throughput is scaled by $1/P$ for surviving rays, maintaining strict energy conservation without biasing the estimator.

---

### 2.2 Progressive Temporal Accumulation & TDR Prevention
To ensure sub-10ms kernel execution times that never trigger the Windows 2-second Timeout Detection and Recovery (TDR) limit:
1. The kernel maintains a device-side `float4* accumBuffer` where each element stores accumulated $(R, G, B)$ radiance and accumulated sample count $W$.
2. In each frame pass, 1 or 2 new stochastic samples per pixel are computed.
3. The running sample average is calculated in-kernel:
   $$\bar{C} = \frac{\sum_{i=1}^N C_i}{N}$$
4. Gamma 2.0 tone mapping ($\sqrt{\bar{C}}$) and $[0, 255]$ clamping are applied directly in device registers.
5. Pixels are written in correct display orientation $(y = \text{height} - 1 - y_{\text{raw}})$, completely removing CPU image flipping overhead.

---

### 2.3 Backend API & Hardware Bridge (`engine.py` & `server.py`)
- Interfaces directly with `C:\Windows\System32\nvcuda.dll` via Python `ctypes`.
- Automatically attaches the CUDA context (`cuCtxSetCurrent`) across asynchronous worker threads.
- Streams live progressive frames over WebSockets at ~60 FPS while concurrently servicing REST endpoints for scene selection, material updates, and hardware telemetry.

---

### 2.4 Modern Frontend Workstation UI (`frontend/`)
- Built using React 18, TypeScript, Vite, and Tailwind CSS.
- Adheres to a dark workstation aesthetic with charcoal surfaces, electric blue/cyan accents, and translucent panels.
- Features real-time orbit/dolly camera interaction via mouse drag and scroll wheel, interactive resolution switching, material inspection, and performance telemetry gauges.
