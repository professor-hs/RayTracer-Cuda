# =============================================================================
# CUDA RAY TRACER - HIGH-THROUGHPUT REST & WEBSOCKET API SERVER
# Exposes versioned public API (/api/v1), real-time WebSocket frame streaming,
# GPU hardware telemetry, and asynchronous rendering job management.
# =============================================================================

import io
import os
import sys
import time
import uuid
import json
import base64
import asyncio
from typing import Dict, Any

from PIL import Image
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.cuda_engine.engine import CudaEngine
from backend.cuda_engine.scenes import get_scene_presets

# -----------------------------------------------------------------------------
# Global State & Singletons
# -----------------------------------------------------------------------------
START_TIME = time.time()
engine = CudaEngine(width=960, height=540)

# Active Render Jobs Registry
render_jobs: Dict[str, Dict[str, Any]] = {}

active_job_id = "default-job"
render_jobs[active_job_id] = {
    "jobId": active_job_id,
    "status": "idle",
    "sceneId": "cornell-box",
    "targetSamples": 256,
    "currentSamples": 0,
    "width": 960,
    "height": 540,
    "maxBounces": 10,
    "progressive": True,
    "created_at": time.time(),
    "completed_at": None,
    "last_error": None
}

# -----------------------------------------------------------------------------
# REST API Handlers (/api/v1)
# -----------------------------------------------------------------------------
async def health_check(request):
    """GET /api/v1/health: Service uptime and health diagnostics."""
    status = engine.get_status()
    return JSONResponse({
        "status": "healthy",
        "service": "cuda-raytracer-api",
        "version": "1.0.0",
        "uptimeSeconds": round(time.time() - START_TIME, 2),
        "backend": status["backend"],
        "cudaAvailable": status["cudaAvailable"],
        "gpuName": status["gpuName"]
    })

async def get_gpu_info(request):
    """GET /api/v1/gpu: Live NVIDIA GPU hardware properties and memory stats."""
    status = engine.get_status()
    return JSONResponse({
        "cudaAvailable": status["cudaAvailable"],
        "gpuName": status["gpuName"],
        "computeCapability": status["computeCapability"],
        "totalMemoryMB": status["totalMemoryMB"],
        "freeMemoryMB": status["freeMemoryMB"],
        "multiprocessors": status["multiprocessors"],
        "driverVersion": status["driverVersion"],
        "backend": status["backend"],
        "hardwareAccelerated": status["cudaAvailable"]
    })

async def get_capabilities(request):
    """GET /api/v1/capabilities: Supported features, limits, and material types."""
    return JSONResponse({
        "renderer": "Monte Carlo Path Tracer",
        "accelerationStructure": "Two-Tier Surface Area Heuristic (SAH) BVH",
        "traversal": "Non-recursive GPU Stack",
        "intersectionAlgorithms": ["Möller-Trumbore Triangles", "Analytic Spheres", "Fast Slab AABB"],
        "progressiveAccumulation": True,
        "maxResolution": {"width": 3840, "height": 2160},
        "supportedResolutions": [
            {"label": "360p Preview", "width": 640, "height": 360},
            {"label": "540p Balanced", "width": 960, "height": 540},
            {"label": "720p HD", "width": 1280, "height": 720},
            {"label": "1080p FHD", "width": 1920, "height": 1080},
            {"label": "1440p QHD / 2K", "width": 2560, "height": 1440}
        ],
        "maxBouncesLimit": 20,
        "maxSamplesLimit": 5000,
        "supportedMaterials": ["Lambertian", "Metal", "Dielectric", "DiffuseLight"],
        "supportedSkyModes": ["Dark Studio", "Atmospheric Sky", "Closed Void"]
    })

async def list_scenes(request):
    """GET /api/v1/scenes: Available scene presets."""
    return JSONResponse({"scenes": get_scene_presets()})

async def get_scene_details(request):
    """GET /api/v1/scenes/{id}: Detailed primitives and geometry counts for a scene."""
    scene_id = request.path_params.get("id", "cornell-box")
    presets = {p["id"]: p for p in get_scene_presets()}
    if scene_id not in presets:
        return JSONResponse({"error": f"Scene '{scene_id}' not found."}, status_code=404)

    preset = presets[scene_id]
    status = engine.get_status()
    return JSONResponse({
        "id": preset["id"],
        "name": preset["name"],
        "description": preset["description"],
        "defaultCamera": preset["defaultCamera"],
        "skyMode": preset["skyMode"],
        "activeOnGpu": (engine.current_scene_id == scene_id),
        "primitives": status["primitives"]
    })

async def list_materials(request):
    """GET /api/v1/materials: Definitions of supported PBR materials."""
    return JSONResponse({
        "materials": [
            {
                "type": "Lambertian",
                "id": 0,
                "description": "Cosine-weighted diffuse surface scattering.",
                "parameters": ["albedo (RGB color)"]
            },
            {
                "type": "Metal",
                "id": 1,
                "description": "Specular metallic reflection with microfacet roughness.",
                "parameters": ["albedo (RGB tint)", "roughness (0.0 to 1.0)"]
            },
            {
                "type": "Dielectric",
                "id": 2,
                "description": "Glass / water refractive transmission with Schlick Fresnel reflectance.",
                "parameters": ["ior (Index of Refraction: 1.0 to 2.5)"]
            },
            {
                "type": "DiffuseLight",
                "id": 3,
                "description": "Emissive surface area light source.",
                "parameters": ["emission (RGB radiance intensity)"]
            }
        ]
    })

async def create_render_job(request):
    """POST /api/v1/render: Submits a new render request or updates active scene parameters."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    scene_id = data.get("sceneId", engine.current_scene_id)
    width = min(max(int(data.get("width", engine.width)), 160), 3840)
    height = min(max(int(data.get("height", engine.height)), 90), 2160)
    target_samples = min(max(int(data.get("samplesPerPixel", 128)), 1), 5000)
    max_bounces = min(max(int(data.get("maxBounces", 10)), 1), 20)
    progressive = bool(data.get("progressive", True))

    camera = data.get("camera", None)

    # Apply configuration to engine
    if scene_id != engine.current_scene_id:
        engine.load_scene(scene_id)

    engine.update_resolution(width, height)
    engine.max_bounces = max_bounces

    if camera and isinstance(camera, dict):
        engine.update_camera(
            position=camera.get("position"),
            target=camera.get("target"),
            fov=camera.get("fov"),
            aperture=camera.get("aperture"),
            focus_dist=camera.get("focusDist")
        )

    engine.reset_accumulation()

    job_id = str(uuid.uuid4())[:8]
    render_jobs[job_id] = {
        "jobId": job_id,
        "status": "rendering",
        "sceneId": scene_id,
        "width": width,
        "height": height,
        "targetSamples": target_samples,
        "currentSamples": 0,
        "maxBounces": max_bounces,
        "progressive": progressive,
        "created_at": time.time(),
        "completed_at": None,
        "last_error": None
    }

    # Render a prime initial frame immediately
    engine.render_frame(samples=1, max_bounces=max_bounces)
    render_jobs[job_id]["currentSamples"] = engine.total_samples_accumulated

    return JSONResponse({
        "jobId": job_id,
        "status": "rendering",
        "width": width,
        "height": height,
        "sceneId": scene_id,
        "targetSamples": target_samples
    }, status_code=202)

async def get_job_status(request):
    """GET /api/v1/render/{jobId}: Retrieves current job progress and metrics."""
    job_id = request.path_params.get("jobId")
    if job_id not in render_jobs:
        return JSONResponse({"error": f"Job '{job_id}' not found."}, status_code=404)

    job = render_jobs[job_id]
    job["currentSamples"] = engine.total_samples_accumulated
    progress = min(round((job["currentSamples"] / max(job["targetSamples"], 1)) * 100.0, 1), 100.0)

    if job["currentSamples"] >= job["targetSamples"] and job["status"] == "rendering":
        job["status"] = "completed"
        if not job["completed_at"]:
            job["completed_at"] = time.time()

    status = engine.get_status()
    return JSONResponse({
        "jobId": job["jobId"],
        "status": job["status"],
        "sceneId": job["sceneId"],
        "width": job["width"],
        "height": job["height"],
        "targetSamples": job["targetSamples"],
        "currentSamples": job["currentSamples"],
        "progressPercent": progress,
        "fps": status["fps"],
        "kernelTimeMs": status["kernelTimeMs"],
        "mraysPerSecond": status["mraysPerSecond"],
        "gpu": status["gpuName"],
        "backend": status["backend"]
    })

async def cancel_job(request):
    """DELETE /api/v1/render/{jobId}: Cancels / pauses active rendering."""
    job_id = request.path_params.get("jobId")
    if job_id not in render_jobs:
        return JSONResponse({"error": f"Job '{job_id}' not found."}, status_code=404)

    render_jobs[job_id]["status"] = "cancelled"
    return JSONResponse({"jobId": job_id, "status": "cancelled", "message": "Render job stopped safely."})

async def get_rendered_image(request):
    """GET /api/v1/render/{jobId}/image: Retrieves the current rendered image in JPEG format."""
    job_id = request.path_params.get("jobId")
    if job_id not in render_jobs:
        return JSONResponse({"error": f"Job '{job_id}' not found."}, status_code=404)

    # Encode current RGBA frame to JPEG
    img = Image.fromarray(engine.h_output_rgba, "RGBA").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)

    return Response(
        content=buf.getvalue(),
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Samples-Accumulated": str(engine.total_samples_accumulated)
        }
    )

async def get_metrics(request):
    """GET /api/v1/metrics: Real-time rendering performance metrics."""
    return JSONResponse(engine.get_status())

# -----------------------------------------------------------------------------
# WebSocket Handler for Live Frame & Progress Streaming
# -----------------------------------------------------------------------------
async def websocket_render_stream(websocket: WebSocket):
    """WS /api/v1/ws/render/{jobId}: Streams live progressive frames and telemetry."""
    await websocket.accept()
    job_id = websocket.path_params.get("jobId", "default")
    print(f"[WebSocket] Client connected to live render stream for job: {job_id}")

    try:
        while True:
            # Check for client messages (e.g. camera move, render config, pause/resume)
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                data = json.loads(msg)
                action = data.get("action")

                if action == "camera":
                    cam = data.get("camera", {})
                    engine.update_camera(
                        position=cam.get("position"),
                        target=cam.get("target"),
                        fov=cam.get("fov"),
                        aperture=cam.get("aperture"),
                        focus_dist=cam.get("focusDist")
                    )
                elif action == "scene":
                    scene_id = data.get("sceneId")
                    if scene_id:
                        engine.load_scene(scene_id)
                elif action == "reset":
                    engine.reset_accumulation()
                elif action == "config":
                    if "width" in data and "height" in data:
                        engine.update_resolution(data["width"], data["height"])
                    if "maxBounces" in data:
                        engine.max_bounces = data["maxBounces"]
                    if "samplesPerFrame" in data:
                        engine.samples_per_frame = data["samplesPerFrame"]
            except asyncio.TimeoutError:
                pass
            except json.JSONDecodeError:
                pass

            # Progressive Render Pass on NVIDIA GPU
            engine.render_frame()

            # Encode Frame to Base64 JPEG
            img = Image.fromarray(engine.h_output_rgba, "RGBA").convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            b64_frame = base64.b64encode(buf.getvalue()).decode("utf-8")

            # Telemetry Packet
            status = engine.get_status()
            payload = {
                "type": "frame",
                "jobId": job_id,
                "image": f"data:image/jpeg;base64,{b64_frame}",
                "samples": engine.total_samples_accumulated,
                "fps": status["fps"],
                "kernelTimeMs": status["kernelTimeMs"],
                "mraysPerSec": status["mraysPerSecond"],
                "gpuName": status["gpuName"],
                "backend": status["backend"],
                "freeMemoryMB": status["freeMemoryMB"]
            }

            await websocket.send_text(json.dumps(payload))
            # Yield control to prevent event-loop starvation
            await asyncio.sleep(0.016) # ~60 FPS cap

    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected from job: {job_id}")
    except Exception as e:
        print(f"[WebSocket] Stream error: {e}")

# -----------------------------------------------------------------------------
# Starlette Application Routing & Middleware
# -----------------------------------------------------------------------------
routes = [
    Route("/api/v1/health", health_check, methods=["GET"]),
    Route("/api/v1/gpu", get_gpu_info, methods=["GET"]),
    Route("/api/v1/capabilities", get_capabilities, methods=["GET"]),
    Route("/api/v1/scenes", list_scenes, methods=["GET"]),
    Route("/api/v1/scenes/{id}", get_scene_details, methods=["GET"]),
    Route("/api/v1/materials", list_materials, methods=["GET"]),
    Route("/api/v1/render", create_render_job, methods=["POST"]),
    Route("/api/v1/render/{jobId}", get_job_status, methods=["GET"]),
    Route("/api/v1/render/{jobId}", cancel_job, methods=["DELETE"]),
    Route("/api/v1/render/{jobId}/image", get_rendered_image, methods=["GET"]),
    Route("/api/v1/metrics", get_metrics, methods=["GET"]),
    WebSocketRoute("/api/v1/ws/render/{jobId}", websocket_render_stream)
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True
    )
]

app = Starlette(debug=False, routes=routes, middleware=middleware)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"==================================================")
    print(f" CUDA Ray Tracer Native API Server running on:")
    print(f" -> http://127.0.0.1:{port}/api/v1/health")
    print(f" -> WebSocket: ws://127.0.0.1:{port}/api/v1/ws/render/default")
    print(f"==================================================")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
