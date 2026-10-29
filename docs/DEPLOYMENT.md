# Production Deployment Guide: CUDA Ray Tracer

This guide provides end-to-end instructions for deploying the **CUDA Ray Tracer** application across frontend hosting platforms and GPU cloud infrastructure.

```
+------------------------------------+          +------------------------------------+
|          Netlify Frontend          |          |          Cloud GPU Server          |
|  - Static React + Vite Bundle      |  HTTPS   |  - NVIDIA Container Toolkit        |
|  - CDN Edge Delivery (Global)      | -------> |  - Native CUDA Engine (PTX JIT)    |
|  - SPA Routing & Security Headers  |  WSS     |  - Uvicorn + Starlette Backend     |
+------------------------------------+          +------------------------------------+
```

---

## Part 1: Netlify Frontend Deployment

Netlify hosts the static React + TypeScript web application, routing API requests to your deployed GPU backend.

### 1.1 Netlify CLI Deployment
1. Ensure the production build succeeds locally:
   ```bash
   cd frontend
   npm run build
   ```
2. Deploy to Netlify:
   ```bash
   netlify deploy --prod --dir=dist
   ```

### 1.2 Netlify Git Continuous Deployment
1. Push your repository to GitHub.
2. In the Netlify Dashboard, click **Add new site > Import an existing project**.
3. Select your GitHub repository.
4. Set Build Settings (pre-configured via `netlify.toml`):
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `dist`
5. Configure Environment Variables in **Site Settings > Environment Variables**:
   - `VITE_API_BASE_URL`: URL of your deployed GPU server (e.g., `https://gpu.your-domain.com`).
6. Click **Deploy Site**.

---

## Part 2: Backend & GPU Worker Deployment Architecture

The deployment architecture separates the public API access layer from the compute-intensive CUDA execution environment:

```
User's Browser (Desktop / Mobile)
      |
      v  HTTPS / WSS
Netlify-hosted Frontend (CDN Edge)
      |
      |  HTTPS REST / WSS
      +-------------------------------------------+
      |                                           |
      v                                           v
Render Web Service (API Gateway)         Public NVIDIA GPU Worker
(Handles public requests, CORS, auth)    (RunPod / Lambda Labs / Cloud GPU / On-Prem)
      |                                           |
      +---- Forward Render Requests ------------->+
                                                  |
                                                  v
                                      NVIDIA Driver (libcuda.so / nvcuda.dll)
                                                  |
                                                  v
                                      PTX JIT / Ampere+ GPU Hardware
```

### 2.1 Render Deployment (render.yaml)

Render is supported via the included `render.yaml` blueprint.

#### Important Technical Compatibility Note:
- Standard Render Web Services run in CPU container environments without physical NVIDIA GPU passthrough.
- If deployed directly on standard Render, the application starts normally and serves the complete REST API; however, the CUDA engine will detect that no physical NVIDIA GPU device is accessible and report `backend: "cpu_fallback"`, `cudaAvailable: false`.
- **For genuine CUDA GPU ray tracing**:
  1. Deploy the rendering worker container on an NVIDIA GPU host (e.g. RunPod, Lambda Labs, AWS `g5.xlarge`, or your GPU workstation).
  2. In your Render Dashboard, set the environment variable:
     ```env
     GPU_WORKER_URL=https://<your-gpu-worker-domain>
     ```
  3. Render acts as the secure, high-uptime public API Gateway routing jobs to the GPU worker.

#### Deploying on Render:
1. Connect your GitHub repository to Render (https://dashboard.render.com).
2. Click **New > Blueprint** and select this repository (it will automatically read `render.yaml`).
3. Or create a **New Web Service**:
   - **Environment**: Python 3
   - **Build Command**: `pip install --no-cache-dir -r backend/requirements.txt`
   - **Start Command**: `python -u backend/server.py`
   - **Health Check Path**: `/api/v1/health`
4. The service will be available at `https://cuda-raytracer-backend.onrender.com`.

---

## Part 3: Native GPU Worker Deployment

The GPU worker requires an NVIDIA GPU with driver support (CUDA 11.8 - 13.0+) and the NVIDIA Container Toolkit.

### 3.1 Recommended Cloud GPU Providers
| Provider | Recommended GPU | Approx. Cost | Notes |
| :--- | :--- | :--- | :--- |
| **RunPod.io** | RTX 3070 / RTX 4000 / A4000 | ~$0.20 - $0.35 / hr | Instant template container, one-click deploy |
| **Lambda Labs** | RTX 6000 / A10 | ~$0.50 - $0.75 / hr | High reliability, persistent instances |
| **AWS EC2** | `g5.xlarge` (NVIDIA A10G 24GB) | ~$1.00 / hr | Enterprise VPC & IAM integration |
| **GCP Compute Engine** | `n1-standard-4` + NVIDIA T4 / L4 | ~$0.60 / hr | Managed Google Cloud environment |

---

### 3.2 Docker GPU Deployment (RunPod / Cloud VM)

1. **Verify NVIDIA Drivers & Container Toolkit**:
   ```bash
   nvidia-smi
   docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
   ```

2. **Build and Launch Container**:
   ```bash
   docker build -t cuda-raytracer:latest .
   docker run -d \
     --name cuda-raytracer \
     --gpus all \
     -p 8080:8080 \
     --restart unless-stopped \
     cuda-raytracer:latest
   ```

3. **Verify Container Health**:
   ```bash
   curl http://localhost:8080/api/v1/health
   ```

---

### 2.3 Reverse Proxy & SSL Setup (Caddy / Nginx)

To enable secure HTTPS and WSS (WebSocket Secure) connections from the Netlify frontend to your GPU server:

#### Caddy (Automatic HTTPS)
Create `/etc/caddy/Caddyfile`:
```caddy
gpu.your-domain.com {
    reverse_proxy localhost:8080
}
```
Reload Caddy:
```bash
sudo systemctl reload caddy
```

#### Nginx
```nginx
server {
    server_name gpu.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400s;
    }
}
```

---

## Part 3: Verification Checklist
- [x] Health check returns `status: "healthy"` and `cudaAvailable: true`.
- [x] GPU device name matches host NVIDIA hardware (e.g. RTX 3050 / RTX 4000).
- [x] WebSocket establishes connection and streams base64 JPEG frames at >30 FPS.
- [x] Netlify frontend loads and connects without CORS or Mixed Content errors.
