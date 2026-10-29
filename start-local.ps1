# =============================================================================
# CUDA Ray Tracer — Local Windows Development Launcher
# Starts the Native CUDA GPU API Server and the Vite React Frontend
# =============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  CUDA RAY TRACER — GPU PATH TRACING WORKSTATION LAUNCHER" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check NVIDIA Driver & GPU
Write-Host "[1/4] Detecting NVIDIA GPU..." -ForegroundColor Yellow
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
} else {
    Write-Host "WARNING: nvidia-smi not found in PATH. Ensure NVIDIA Drivers are installed." -ForegroundColor Red
}

# 2. Check Compiled PTX
Write-Host "`n[2/4] Checking CUDA PTX Binary..." -ForegroundColor Yellow
$ptxPath = "backend/cuda_engine/raytracer_kernel.ptx"
if (-not (Test-Path $ptxPath)) {
    Write-Host "Compiling CUDA Kernel to NVPTX..." -ForegroundColor Yellow
    clang++ -x c++ --target=nvptx64-nvidia-cuda -march=sm_86 -O3 -S -o $ptxPath backend/cuda_engine/raytracer_kernel.cu
    if (Test-Path $ptxPath) {
        Write-Host "NVPTX compiled successfully!" -ForegroundColor Green
    } else {
        Write-Host "Compilation failed. Ensure clang++ is installed." -ForegroundColor Red
    }
} else {
    Write-Host "Found compiled PTX: $ptxPath" -ForegroundColor Green
}

# 3. Launch Backend
Write-Host "`n[3/4] Starting Native CUDA Backend Server (Port 8080)..." -ForegroundColor Yellow
$backendJob = Start-Process -FilePath "python" -ArgumentList "-u", "backend/server.py" -PassThru

# 4. Launch Frontend
Write-Host "`n[4/4] Starting React + TypeScript Frontend (Port 5173)..." -ForegroundColor Yellow
Push-Location frontend
$frontendJob = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -PassThru
Pop-Location

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  SERVICES RUNNING!" -ForegroundColor Green
Write-Host "  -> Frontend Workstation UI : http://localhost:5173" -ForegroundColor Cyan
Write-Host "  -> Backend API Health Check: http://localhost:8080/api/v1/health" -ForegroundColor Cyan
Write-Host "  -> WebSocket Live Stream   : ws://localhost:8080/api/v1/ws/render/default" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Press Ctrl+C or close this window to stop both servers." -ForegroundColor Gray

# Monitor & keep active until interrupted
try {
    while ($true) {
        Start-Sleep -Seconds 2
        if ($backendJob.HasExited) {
            Write-Host "Backend process exited." -ForegroundColor Red
            break
        }
        if ($frontendJob.HasExited) {
            Write-Host "Frontend process exited." -ForegroundColor Red
            break
        }
    }
} finally {
    Write-Host "`nStopping servers..." -ForegroundColor Yellow
    Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue
    Write-Host "Shutdown complete." -ForegroundColor Green
}
