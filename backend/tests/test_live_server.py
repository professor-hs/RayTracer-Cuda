# =============================================================================
# END-TO-END LIVE SERVER & GPU RAY TRACING INTEGRATION TEST
# Starts backend server process, sends real HTTP/WebSocket requests, verifies GPU frame output
# =============================================================================

import os
import sys
import time
import json
import urllib.request
import urllib.error
import subprocess
import asyncio
from io import BytesIO
from PIL import Image

PORT = 8085
BASE_URL = f"http://127.0.0.1:{PORT}"

def run_e2e_tests():
    env = os.environ.copy()
    env["PORT"] = str(PORT)
    env["HOST"] = "127.0.0.1"
    env["PYTHONUNBUFFERED"] = "1"

    print(f"[E2E] Spawning backend server process on port {PORT}...")
    proc = subprocess.Popen(
        [sys.executable, "-u", os.path.join(os.path.dirname(__file__), "../server.py")],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    try:
        print("[E2E] Waiting for live server on port 8085...")
        started = False
        for _ in range(40):
            if proc.poll() is not None:
                out, _ = proc.communicate()
                raise RuntimeError(f"Server process terminated prematurely:\n{out}")
            try:
                with urllib.request.urlopen(f"{BASE_URL}/api/v1/health", timeout=1) as resp:
                    if resp.status == 200:
                        started = True
                        break
            except Exception:
                time.sleep(0.25)

        if not started:
            raise RuntimeError("Server failed to respond on health check.")

        print("[E2E] Server is online. Running tests...\n")

        # 1. Health
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/health") as resp:
            assert resp.status == 200
            health = json.loads(resp.read().decode())
            print(f"[PASS] Health Check: {health['status']} | Backend: {health['backend']} | GPU: {health['gpuName']}")
            assert health["status"] == "healthy"
            assert health["cudaAvailable"] is True

        # 2. GPU Telemetry
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/gpu") as resp:
            assert resp.status == 200
            gpu = json.loads(resp.read().decode())
            print(f"[PASS] GPU Info: {gpu['gpuName']} | Compute {gpu['computeCapability']} | VRAM {gpu['totalMemoryMB']} MB")
            assert gpu["cudaAvailable"] is True
            assert "RTX" in gpu["gpuName"] or "GeForce" in gpu["gpuName"]

        # 3. Capabilities
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/capabilities") as resp:
            assert resp.status == 200
            caps = json.loads(resp.read().decode())
            print(f"[PASS] Capabilities: {caps['renderer']} with {caps['accelerationStructure']}")
            assert len(caps["supportedMaterials"]) == 4

        # 4. Scenes
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/scenes") as resp:
            assert resp.status == 200
            scenes = json.loads(resp.read().decode())["scenes"]
            print(f"[PASS] Scene Presets: Found {len(scenes)} scenes")
            assert len(scenes) >= 4

        # 5. Scene details
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/scenes/cornell-box") as resp:
            assert resp.status == 200
            scene_detail = json.loads(resp.read().decode())
            print(f"[PASS] Scene Detail: {scene_detail['name']} with {scene_detail['primitives']['triangles']} triangles")

        # 6. Render Job Submission
        payload = json.dumps({
            "sceneId": "cornell-box",
            "width": 480,
            "height": 270,
            "samplesPerPixel": 16,
            "maxBounces": 6,
            "progressive": True
        }).encode("utf-8")
        req = urllib.request.Request(f"{BASE_URL}/api/v1/render", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 202
            job_data = json.loads(resp.read().decode())
            job_id = job_data["jobId"]
            print(f"[PASS] Render Job Created: ID {job_id} ({job_data['status']})")

        # 7. Poll Job Status until completed
        completed = False
        for _ in range(50):
            with urllib.request.urlopen(f"{BASE_URL}/api/v1/render/{job_id}") as resp:
                status_data = json.loads(resp.read().decode())
                if status_data["status"] == "completed":
                    completed = True
                    print(f"[PASS] Job Converged: Samples={status_data['currentSamples']}/{status_data['targetSamples']} | Progress={status_data['progressPercent']}% | FPS={status_data['fps']}")
                    break
            time.sleep(0.1)
        assert completed, "Render job did not reach completion status."

        # 8. Retrieve PNG Output
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/render/{job_id}/image?format=png") as resp:
            assert resp.status == 200
            assert resp.headers["Content-Type"] == "image/png"
            img_bytes = resp.read()
            img = Image.open(BytesIO(img_bytes))
            assert img.size == (480, 270), f"Unexpected image size: {img.size}"
            assert img.format == "PNG"
            # Verify image contains rendered pixel values
            extrema = img.getextrema()
            assert any(e[1] > 0 for e in extrema), "Image should contain rendered pixel radiance"
            print(f"[PASS] PNG Image Verified: Size={img.size}, Channels={img.mode}, Bytes={len(img_bytes)}")

        # 9. Retrieve JPEG Output
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/render/{job_id}/image?format=jpeg") as resp:
            assert resp.status == 200
            assert resp.headers["Content-Type"] == "image/jpeg"
            jpeg_bytes = resp.read()
            jpeg_img = Image.open(BytesIO(jpeg_bytes))
            assert jpeg_img.size == (480, 270)
            assert jpeg_img.format == "JPEG"
            print(f"[PASS] JPEG Image Verified: Size={jpeg_img.size}, Bytes={len(jpeg_bytes)}")

        # 10. Metrics
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/metrics") as resp:
            assert resp.status == 200
            metrics = json.loads(resp.read().decode())
            print(f"[PASS] Performance Metrics: KernelTime={metrics['kernelTimeMs']}ms | Throughput={metrics['mraysPerSecond']} MRays/s | FPS={metrics['fps']}")

        # 11. WebSocket Frame Streaming Test
        async def test_ws():
            import websockets
            uri = f"ws://127.0.0.1:{PORT}/api/v1/ws/render/default"
            async with websockets.connect(uri) as ws:
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(msg)
                assert data["type"] == "frame"
                assert data["image"].startswith("data:image/jpeg;base64,")
                assert data["samples"] >= 1
                print(f"[PASS] WebSocket Frame Stream: Received live frame at {data['fps']:.1f} FPS, GPU={data['gpuName']}")

        asyncio.run(test_ws())

        print("\n=======================================================")
        print(" ALL END-TO-END LIVE SERVER & GPU TESTS PASSED 100%!")
        print("=======================================================")

    finally:
        print("[E2E] Terminating backend server process...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    run_e2e_tests()
