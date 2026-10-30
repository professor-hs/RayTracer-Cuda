# =============================================================================
# AUTOMATED TEST SUITE: BACKEND REST API & CUDA ENGINE VERIFICATION
# =============================================================================

import os
import sys
import json

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import backend.server as srv
from starlette.requests import Request

def run_coro(coro):
    """Executes a coroutine directly to completion without Windows Proactor loop issues."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value

def test_health():
    res = run_coro(srv.health_check(None))
    assert res.status_code == 200
    data = json.loads(res.body)
    assert data["status"] == "healthy"
    assert data["service"] == "cuda-raytracer-api"
    if data["cudaAvailable"]:
        assert data["backend"] == "cuda_gpu"
        print(f"Health Check Passed: GPU={data['gpuName']} (CUDA GPU Active)")
    else:
        assert data["backend"] == "cpu_fallback"
        print("Health Check Passed: CPU Fallback Active (No physical CUDA GPU detected)")

def test_gpu_info():
    res = run_coro(srv.get_gpu_info(None))
    assert res.status_code == 200
    data = json.loads(res.body)
    if data["cudaAvailable"]:
        assert "GeForce" in data["gpuName"] or "RTX" in data["gpuName"] or "Tesla" in data["gpuName"] or "A10" in data["gpuName"]
        assert float(data["computeCapability"]) >= 5.0
        assert data["totalMemoryMB"] > 1000
        print(f"GPU Info Passed: {data['gpuName']} (Compute {data['computeCapability']})")
    else:
        assert data["backend"] == "cpu_fallback"
        print("GPU Info Passed: Validated CPU fallback state when hardware GPU is unavailable.")

def test_capabilities():
    res = run_coro(srv.get_capabilities(None))
    assert res.status_code == 200
    data = json.loads(res.body)
    assert data["progressiveAccumulation"] is True
    assert "Two-Tier" in data["accelerationStructure"]
    assert "Lambertian" in data["supportedMaterials"]
    print("Capabilities Passed.")

def test_scenes():
    res = run_coro(srv.list_scenes(None))
    assert res.status_code == 200
    data = json.loads(res.body)
    scenes = data["scenes"]
    assert len(scenes) >= 4
    scene_ids = [s["id"] for s in scenes]
    assert "cornell-box" in scene_ids
    assert "glass-metal-showroom" in scene_ids
    print(f"Scenes Passed: Found {len(scenes)} presets.")

def test_materials():
    res = run_coro(srv.list_materials(None))
    assert res.status_code == 200
    data = json.loads(res.body)
    assert len(data["materials"]) == 4
    print("Materials Passed.")

def test_render_and_image():
    class MockRequest:
        def __init__(self, json_data):
            self._json = json_data
            self.path_params = {"jobId": "default-job"}
        async def json(self):
            return self._json

    mock_req = MockRequest({
        "sceneId": "cornell-box",
        "width": 320,
        "height": 180,
        "samplesPerPixel": 4,
        "maxBounces": 4,
        "progressive": True
    })

    # 1. Create render job
    res = run_coro(srv.create_render_job(mock_req))
    assert res.status_code == 202
    job_info = json.loads(res.body)
    job_id = job_info["jobId"]
    assert job_info["status"] == "rendering"

    # 2. Status
    mock_req.path_params = {"jobId": job_id}
    res_status = run_coro(srv.get_job_status(mock_req))
    assert res_status.status_code == 200
    status_data = json.loads(res_status.body)
    assert status_data["currentSamples"] >= 1

    # 3. Image (JPEG)
    res_img = run_coro(srv.get_rendered_image(mock_req))
    assert res_img.status_code == 200
    assert len(res_img.body) > 1000
    assert res_img.headers["content-type"] == "image/jpeg"
    print(f"Render Job Passed: Generated {len(res_img.body)} bytes JPEG image.")

    # 4. Image (PNG)
    class MockPngRequest:
        def __init__(self, job_id):
            self.path_params = {"jobId": job_id}
            self.query_params = {"format": "png"}
    res_png = run_coro(srv.get_rendered_image(MockPngRequest(job_id)))
    assert res_png.status_code == 200
    assert res_png.headers["content-type"] == "image/png"
    print(f"PNG Export Passed: Generated {len(res_png.body)} bytes PNG image.")

    # 5. Cancellation
    res_cancel = run_coro(srv.cancel_job(mock_req))
    assert res_cancel.status_code == 200
    cancel_data = json.loads(res_cancel.body)
    assert cancel_data["status"] == "cancelled"
    print("Job Cancellation Passed.")

    # 6. Non-existent job 404
    mock_req.path_params = {"jobId": "invalid-job-999"}
    res_404 = run_coro(srv.get_job_status(mock_req))
    assert res_404.status_code == 404
    print("404 Error Handling Passed.")

def test_scene_details():
    class MockSceneReq:
        def __init__(self, scene_id):
            self.path_params = {"id": scene_id}
    res_valid = run_coro(srv.get_scene_details(MockSceneReq("cornell-box")))
    assert res_valid.status_code == 200
    data = json.loads(res_valid.body)
    assert data["id"] == "cornell-box"
    assert "primitives" in data

    res_invalid = run_coro(srv.get_scene_details(MockSceneReq("unknown-scene-xyz")))
    assert res_invalid.status_code == 404
    print("Scene Details & 404 Validation Passed.")

def test_metrics():
    res = run_coro(srv.get_metrics(None))
    assert res.status_code == 200
    data = json.loads(res.body)
    assert "fps" in data
    assert "kernelTimeMs" in data
    print(f"Metrics Passed: FPS={data['fps']}, KernelTime={data['kernelTimeMs']}ms")

if __name__ == "__main__":
    print("=== Running Backend Test Suite ===")
    test_health()
    test_gpu_info()
    test_capabilities()
    test_scenes()
    test_scene_details()
    test_materials()
    test_render_and_image()
    test_metrics()
    print("=== ALL BACKEND API & GPU TESTS PASSED 100%! ===")
