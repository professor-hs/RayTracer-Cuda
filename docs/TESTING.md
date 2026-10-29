# Testing & Quality Assurance Guide: CUDA Ray Tracer

This document outlines the testing strategy, test suites, and validation procedures for the **CUDA Ray Tracer** engine, native backend API, and web workstation frontend.

---

## 1. Test Architecture Overview

```
+-------------------------------------------------------------------------------+
|                           Testing Strategy Matrix                             |
+-------------------------------------------------------------------------------+
| Layer               | Framework / Method       | Scope Tested                 |
+---------------------+--------------------------+------------------------------+
| 1. CUDA Kernels     | Standalone Execution     | PTX JIT compilation, math    |
|                     | & Mathematical Asserts   | accuracy, Möller-Trumbore    |
+---------------------+--------------------------+------------------------------+
| 2. Backend REST API | Python Unit & Coroutine  | All /api/v1/* routes, status |
|                     | Integration Suite        | codes, JSON payloads, headers|
+---------------------+--------------------------+------------------------------+
| 3. GPU Hardware     | NVIDIA Driver API        | Memory allocation, context   |
|                     | Telemetry Verification   | binding, hardware detection  |
+---------------------+--------------------------+------------------------------+
| 4. Frontend UI      | TypeScript Compiler &    | Strict typing, component     |
|                     | Vite Production Build    | bundling, zero build errors  |
+---------------------+--------------------------+------------------------------+
```

---

## 2. Automated Test Execution

### 2.1 Backend API & CUDA Engine Test Suite
Run the automated backend test suite:
```powershell
python -u backend/tests/test_api.py
```

**Test Cases Covered**:
- `test_health`: Verifies `GET /api/v1/health` returns `status: "healthy"` and identifies the `cuda_gpu` backend.
- `test_gpu_info`: Verifies `GET /api/v1/gpu` returns genuine hardware properties (NVIDIA GeForce RTX 3050 Laptop GPU, Compute 8.6, >4000 MB VRAM).
- `test_capabilities`: Verifies supported materials (`Lambertian`, `Metal`, `Dielectric`, `DiffuseLight`), acceleration structure (`Two-Tier SAH BVH`), and progressive accumulation flags.
- `test_scenes`: Validates scene catalog retrieval and individual geometry queries for `cornell-box`, `glass-metal-showroom`, `spheres-gallery`, and `emissive-studio`.
- `test_materials`: Validates the physical material schema and parameter limits.
- `test_render_and_image`: Submits a real render job via `POST /api/v1/render`, queries status via `GET /api/v1/render/{jobId}`, and validates binary JPEG image retrieval from `GET /api/v1/render/{jobId}/image` with `X-Samples-Accumulated` headers.
- `test_metrics`: Validates real-time framerate, kernel execution duration, and ray throughput.

**Expected Output**:
```text
[CudaEngine] SUCCESS: GPU Initialized -> NVIDIA GeForce RTX 3050 Laptop GPU (Compute 8.6, 4095.5 MB VRAM)
[CudaEngine] Loaded Scene 'cornell-box': 2 Spheres, 36 Triangles, 23 BVH Nodes, 7 Materials.
=== Running Backend Test Suite ===
Health Check Passed: GPU=NVIDIA GeForce RTX 3050 Laptop GPU
GPU Info Passed: NVIDIA GeForce RTX 3050 Laptop GPU (Compute 8.6)
Capabilities Passed.
Scenes Passed: Found 4 presets.
Materials Passed.
Render Job Passed: Generated 11039 bytes JPEG image on GPU.
Metrics Passed: FPS=1018.4, KernelTime=0.98ms
=== ALL 7 BACKEND API TESTS PASSED 100%! ===
```

---

### 2.2 Frontend Build & TypeScript Validation
Verify frontend compilation and bundle integrity:
```powershell
cd frontend
npm run build
```

**Expected Output**:
```text
> cuda-raytracer-frontend@1.0.0 build
> tsc && vite build

vite v6.4.5 building for production...
✓ 2048 modules transformed.
dist/index.html                   1.39 kB │ gzip:  0.77 kB
dist/assets/index-BWJRYEnb.css   20.05 kB │ gzip:  4.49 kB
dist/assets/index-Bg82q8Zp.js   192.54 kB │ gzip: 58.09 kB
✓ built in 4.38s
```

---

## 3. End-to-End Manual Testing Checklist

| Step | Verification Procedure | Expected Outcome |
| :--- | :--- | :--- |
| **1. Startup** | Run `.\start-local.ps1` in PowerShell. | Backend launches on port 8080; Frontend opens on `http://localhost:5173`. |
| **2. GPU Pill** | Observe top-center hardware status badge. | Displays "NVIDIA GeForce RTX 3050 Laptop GPU • Compute 8.6 • 4096 MB VRAM". |
| **3. Viewport** | Click and drag across the central canvas. | Camera orbits smoothly around scene origin; accumulation resets and converges. |
| **4. Preset Switch** | Click "Glass & Metal Showroom" in left panel. | Viewport loads metallic showroom with reflections; camera updates position. |
| **5. Resolution** | Select "720p HD" or "1080p FHD" in right panel. | Output resolution updates; GPU reallocates buffers seamlessly. |
| **6. Pause/Resume**| Click "PAUSE" in bottom floating toolbar. | GPU stops shooting rays; sample count freezes; click "RESUME" to continue. |
| **7. Export** | Click "EXPORT" button. | Downloads high-resolution JPEG/PNG screenshot to local disk. |
