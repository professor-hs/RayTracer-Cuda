# =============================================================================
# PRODUCTION NVIDIA GPU CONTAINER DOCKERFILE
# Base: NVIDIA CUDA 12.4.1 Devel Ubuntu 22.04 with NVPTX & Driver Runtime
# =============================================================================

FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies & Python 3
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    clang \
    llvm \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip3 install --no-cache-dir -r /app/backend/requirements.txt

# Copy source code
COPY backend /app/backend
COPY openapi.yaml /app/openapi.yaml

# Compile kernel to PTX inside container
RUN clang++ -x c++ --target=nvptx64-nvidia-cuda -march=sm_86 -O3 -S \
    -o /app/backend/cuda_engine/raytracer_kernel.ptx \
    /app/backend/cuda_engine/raytracer_kernel.cu

EXPOSE 8080

CMD ["python3", "-u", "backend/server.py"]
