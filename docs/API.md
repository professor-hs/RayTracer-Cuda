# Public API Specification & Integration Guide

The CUDA Ray Tracer exposes a versioned REST and WebSocket API (`/api/v1`) allowing external clients, automation pipelines, and the web frontend to control the GPU rendering engine.

## Base URLs
- **Local Development**: `http://localhost:8080`
- **WebSocket Base**: `ws://localhost:8080/api/v1/ws/render/{jobId}`

---

## 1. REST Endpoints

### 1.1 Health Check
Returns system health, version, and active GPU status.
- **Method**: `GET`
- **Path**: `/api/v1/health`
- **Response**:
```json
{
  "status": "healthy",
  "service": "cuda-raytracer-api",
  "version": "1.0.0",
  "uptimeSeconds": 145.2,
  "backend": "cuda_gpu",
  "cudaAvailable": true,
  "gpuName": "NVIDIA GeForce RTX 3050 Laptop GPU"
}
```
- **Example**:
```bash
curl -X GET http://localhost:8080/api/v1/health
```

---

### 1.2 GPU Hardware Telemetry
Queries real hardware metrics directly from the NVIDIA CUDA Driver.
- **Method**: `GET`
- **Path**: `/api/v1/gpu`
- **Response**:
```json
{
  "cudaAvailable": true,
  "gpuName": "NVIDIA GeForce RTX 3050 Laptop GPU",
  "computeCapability": "8.6",
  "totalMemoryMB": 4095.5,
  "freeMemoryMB": 3812.0,
  "multiprocessors": 16,
  "driverVersion": "13.0",
  "backend": "cuda_gpu",
  "hardwareAccelerated": true
}
```

---

### 1.3 Capabilities
Returns engine acceleration structures and configurable boundaries.
- **Method**: `GET`
- **Path**: `/api/v1/capabilities`
- **Response**:
```json
{
  "renderer": "Monte Carlo Path Tracer",
  "accelerationStructure": "Two-Tier Surface Area Heuristic (SAH) BVH",
  "traversal": "Non-recursive GPU Stack",
  "progressiveAccumulation": true,
  "maxBouncesLimit": 20,
  "supportedMaterials": ["Lambertian", "Metal", "Dielectric", "DiffuseLight"]
}
```

---

### 1.4 List Scenes & Scene Details
- **Method**: `GET /api/v1/scenes`
- **Method**: `GET /api/v1/scenes/{id}`
- **Example**:
```bash
curl -X GET http://localhost:8080/api/v1/scenes/cornell-box
```

---

### 1.5 Create / Update Render Job
Initiates rendering with specific resolution, samples, bounces, or camera orientation.
- **Method**: `POST`
- **Path**: `/api/v1/render`
- **Request Body**:
```json
{
  "sceneId": "cornell-box",
  "width": 1280,
  "height": 720,
  "samplesPerPixel": 256,
  "maxBounces": 10,
  "progressive": true,
  "camera": {
    "position": [0.0, 1.0, 3.2],
    "target": [0.0, 1.0, 0.0],
    "fov": 45.0,
    "aperture": 0.00001,
    "focusDist": 3.2
  }
}
```
- **Response Status**: `202 Accepted`
```json
{
  "jobId": "a1b2c3d4",
  "status": "rendering",
  "width": 1280,
  "height": 720,
  "sceneId": "cornell-box",
  "targetSamples": 256
}
```

---

### 1.6 Job Status & Image Retrieval
- **Method**: `GET /api/v1/render/{jobId}`
- **Method**: `GET /api/v1/render/{jobId}/image` (returns binary `image/jpeg`)
- **Example**:
```bash
curl -X GET http://localhost:8080/api/v1/render/a1b2c3d4/image -o frame.jpg
```

---

### 1.7 Live Metrics
- **Method**: `GET /api/v1/metrics`
```json
{
  "fps": 298.5,
  "kernelTimeMs": 3.35,
  "mraysPerSecond": 45.2,
  "totalSamples": 182,
  "freeMemoryMB": 3812.0
}
```

---

## 2. WebSocket Protocol (`/api/v1/ws/render/{jobId}`)

Clients connect to the WebSocket endpoint to receive live streaming frames and push camera/scene updates with zero HTTP handshake overhead.

### 2.1 Inbound Messages (Client -> Server)
```json
// Update Camera
{ "action": "camera", "camera": { "position": [1.0, 2.0, 4.0], "target": [0.0, 0.5, 0.0] } }

// Switch Scene
{ "action": "scene", "sceneId": "glass-metal-showroom" }

// Reset Accumulation
{ "action": "reset" }

// Update Parameters
{ "action": "config", "width": 1280, "height": 720, "maxBounces": 12 }
```

### 2.2 Outbound Telemetry Stream (Server -> Client)
Sent after every progressive GPU pass:
```json
{
  "type": "frame",
  "jobId": "default",
  "image": "data:image/jpeg;base64,...",
  "samples": 84,
  "fps": 120.4,
  "kernelTimeMs": 8.3,
  "mraysPerSec": 32.1,
  "gpuName": "NVIDIA GeForce RTX 3050 Laptop GPU",
  "backend": "cuda_gpu"
}
```
