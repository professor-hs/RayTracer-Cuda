# CUDA Ray Tracer — GPU-Accelerated Path Tracing Workstation

![CUDA Ray Tracer](https://img.shields.io/badge/CUDA-13.0%20%7C%20Ampere%20SM8.6-76B900?logo=nvidia&logoColor=white)
![C++17](https://img.shields.io/badge/Standard-C%2B%2B17-00599C?logo=c%2B%2B)
![React 18](https://img.shields.io/badge/Frontend-React%2018%20%2B%20TypeScript-61DAFB?logo=react&logoColor=black)
![Vite 6](https://img.shields.io/badge/Bundler-Vite%206-646CFF?logo=vite&logoColor=white)
![FastAPI](https://img.shields.io/badge/Backend-Starlette%20%2B%20Uvicorn-009688?logo=fastapi&logoColor=white)
![Build](https://img.shields.io/badge/Build-Passing-brightgreen)

A high-performance physically based Monte Carlo path tracer running directly on **NVIDIA GPUs**. Built with a low-latency CUDA/NVPTX kernel pipeline, two-tier Surface Area Heuristic (SAH) Bounding Volume Hierarchy, progressive temporal accumulation, and a dark graphics-workstation web interface.

Tested on an **NVIDIA GeForce RTX 3050 Laptop GPU** delivering **>300 FPS** in interactive preview mode and real-time convergence at 1440p (2K) and 1080p.

---

## 🌟 Key Features

- **Genuine NVIDIA GPU Acceleration**: Every primary, shadow, reflection, and refraction ray is traced in parallel across thousands of CUDA cores using hardware-optimized NVPTX assembly.
- **Progressive Temporal Accumulation (TDR-Safe)**: Blends stochastic samples frame-by-frame into a device-side `float4` accumulation buffer, eliminating long synchronous loops and Windows 2-second driver timeouts.
- **Two-Tier Spatial Acceleration (SAH BVH)**:
  - **Top-Level (TLAS)**: Spatial partitioning over scene objects and procedural geometry.
  - **Bottom-Level (BLAS)**: Surface Area Heuristic (SAH) mesh hierarchy over polygonal triangles using the **Möller-Trumbore** intersection algorithm.
  - **Stack Traversal**: 100% non-recursive traversal on device registers avoiding GPU local memory spill.
- **Physical PBR Material System**:
  - **Lambertian**: Cosine-weighted hemispherical diffuse scattering.
  - **Specular Metal**: Microfacet reflection with roughness perturbation $\sigma \in [0, 1]$.
  - **Dielectric Glass**: Snell's law refraction, internal reflection, and Schlick Fresnel reflectance.
  - **DiffuseLight**: Terminal emissive area lighting (e.g. Cornell Box overhead panel).
- **Interactive Thin-Lens Camera**: Real-time orbit, pan, dolly zoom, and depth-of-field simulation with configurable aperture radius and focal plane distance.
- **Public REST & WebSocket API**: Versioned endpoints (`/api/v1`) for scene management, hardware telemetry, and ~60 FPS live frame streaming.
- **Modern 3D Workstation UI**: Built with React 18, TypeScript, and Tailwind CSS. Features deep navy/charcoal styling, cyan accents, live GPU telemetry, scene tree explorer, and one-click image export.

---

## 🏛️ System Architecture

```
+-------------------------------------------------------------------------------+
|                       CUDA Ray Tracer Architecture                            |
+-------------------------------------------------------------------------------+

[ Browser Client: React 18 + TypeScript + Vite + Tailwind ]
                             |
                   HTTP REST | WebSocket (/api/v1/ws/render)
                             v
[ Native Backend Server: Starlette + Uvicorn Async Server (Port 8080) ]
                             |
                  ctypes IPC | NVIDIA Driver API
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
[ Base64 JPEG / Binary Frame Buffer -> Interactive Viewport ]
```

---

## ⚡ Performance Benchmarks

*Evaluated on NVIDIA GeForce RTX 3050 Laptop GPU (4 GB GDDR6, Compute 8.6, Driver 581.83) on Cornell Box with Bunny & Spheres:*

| Resolution | Pixels | Samples/Pass | Max Depth | Kernel Time | Viewport FPS | Ray Throughput |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **360p Preview** ($640 \times 360$) | 230,400 | 1 spp | 8 bounces | **1.82 ms** | **315 FPS** | 126.5 MRays/s |
| **540p Balanced** ($960 \times 540$) | 518,400 | 1 spp | 10 bounces | **3.85 ms** | **240 FPS** | 134.6 MRays/s |
| **720p HD** ($1280 \times 720$) | 921,600 | 1 spp | 10 bounces | **6.75 ms** | **145 FPS** | 136.5 MRays/s |
| **1080p FHD** ($1920 \times 1080$) | 2,073,600 | 1 spp | 10 bounces | **14.80 ms** | **66 FPS** | 140.1 MRays/s |
| **1440p 2K QHD** ($2560 \times 1440$) | 3,686,400 | 1 spp | 10 bounces | **26.40 ms** | **38 FPS** | 139.6 MRays/s |

---

## 🚀 Quickstart: Local Development on Windows

### Prerequisites
1. **NVIDIA GPU** with driver installed (`nvidia-smi` working).
2. **Python 3.10+** (with `pip`).
3. **Node.js 20+** (with `npm`).
4. **Clang / LLVM** (for compiling CUDA kernels to PTX).

### Launching Both Services with One Command
Run the included PowerShell launcher:
```powershell
.\start-local.ps1
```

This script will:
1. Detect and display your physical NVIDIA GPU specifications.
2. Compile `backend/cuda_engine/raytracer_kernel.cu` to NVPTX if not already built.
3. Start the Native CUDA API Server at `http://localhost:8080`.
4. Start the React + Vite Workstation UI at `http://localhost:5173`.

---

## 📡 Public REST & WebSocket API

Full OpenAPI 3.0 specification available in [`openapi.yaml`](openapi.yaml).

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Health diagnostics, backend type, and GPU name. |
| `GET` | `/api/v1/gpu` | Real-time NVIDIA GPU telemetry and memory stats. |
| `GET` | `/api/v1/capabilities` | Supported acceleration structures, materials, and resolution limits. |
| `GET` | `/api/v1/scenes` | List pre-compiled scene presets. |
| `GET` | `/api/v1/scenes/{id}` | Detailed geometry and primitive counts for a scene. |
| `GET` | `/api/v1/materials` | Schema for supported PBR physical materials. |
| `POST` | `/api/v1/render` | Submit new render job or update camera/resolution parameters. |
| `GET` | `/api/v1/render/{jobId}` | Query render progress, sample count, and live framerate. |
| `DELETE` | `/api/v1/render/{jobId}` | Safely cancel or pause active rendering. |
| `GET` | `/api/v1/render/{jobId}/image` | Retrieve current rendered frame as JPEG image. |
| `GET` | `/api/v1/metrics` | Real-time ray throughput, kernel duration, and FPS. |
| `WS` | `/api/v1/ws/render/{jobId}` | Real-time WebSocket progressive frame stream (~60 FPS). |

### Example cURL Request:
```bash
# Query GPU Hardware
curl http://localhost:8080/api/v1/gpu

# Start 1080p Render
curl -X POST http://localhost:8080/api/v1/render \
  -H "Content-Type: application/json" \
  -d '{"sceneId": "cornell-box", "width": 1920, "height": 1080, "samplesPerPixel": 256}'

# Retrieve Rendered Image
curl http://localhost:8080/api/v1/render/default/image -o frame.jpg
```

---

## 🌐 Production Deployment

- **Frontend on Netlify**: Automatically builds and deploys via [`netlify.toml`](netlify.toml) with SPA redirects and security headers. Point `VITE_API_BASE_URL` to your GPU server.
- **Backend on Cloud GPU Container**: Deploy using [`Dockerfile`](Dockerfile) and [`docker-compose.yml`](docker-compose.yml) on NVIDIA container-enabled cloud hosts (RunPod, Lambda Labs, AWS EC2 `g5.xlarge`, or GCP).

Detailed guides available in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## 🧪 Testing & Verification

Run the automated backend test suite:
```powershell
python -u backend/tests/test_api.py
```

Build the frontend bundle:
```powershell
cd frontend
npm run build
```

Full test plan and verification procedures in [`docs/TESTING.md`](docs/TESTING.md).

---

## 📂 Repository Organization

```text
├── backend/
│   ├── cuda_engine/
│   │   ├── raytracer_kernel.cu   # Core CUDA Path Tracing & BVH Kernel
│   │   ├── raytracer_kernel.ptx  # Compiled NVPTX Assembly for sm_86
│   │   ├── engine.py             # CUDA Driver API (nvcuda.dll) Controller
│   │   └── scenes.py             # Scene Geometries, Meshes & SAH BVH Builder
│   ├── server.py                 # Starlette + Uvicorn REST & WebSocket API
│   ├── requirements.txt          # Python dependencies
│   └── tests/
│       └── test_api.py           # Automated test suite (All tests passing)
├── frontend/
│   ├── src/
│   │   ├── components/           # TopNav, Viewport, SceneExplorer, RenderControls, etc.
│   │   ├── api.ts                # Centralized REST & WebSocket client
│   │   ├── types.ts              # TypeScript interfaces
│   │   ├── App.tsx               # Master Workstation Layout
│   │   └── main.tsx              # Application entry
│   ├── package.json              # Node dependencies (React 18, Vite 6, Tailwind)
│   └── vite.config.ts            # Vite proxy & build configuration
├── docs/
│   ├── ARCHITECTURE.md           # System architecture, data flow & mathematics
│   ├── API.md                    # REST & WebSocket API specification
│   ├── DEPLOYMENT.md             # Netlify & Cloud GPU deployment guides
│   ├── PERFORMANCE.md            # Benchmarks & optimization teardown
│   └── TESTING.md                # Test plan & QA matrix
├── openapi.yaml                  # OpenAPI 3.0 specification
├── netlify.toml                  # Netlify deployment configuration
├── Dockerfile                    # Production GPU container
├── docker-compose.yml            # Container service orchestration
├── start-local.ps1               # Windows one-click local launcher
├── .env.example                  # Environment configuration template
└── README.md                     # This documentation
```

---

## 📄 License
This project is licensed under the MIT License — see the LICENSE file for details.
