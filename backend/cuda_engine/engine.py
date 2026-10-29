# =============================================================================
# CUDA DRIVER API ENGINE CONTROLLER & RENDER PIPELINE
# Connects to native nvcuda.dll, loads PTX, allocates GPU buffers, and
# dispatches progressive path-tracing kernels to the NVIDIA RTX GPU.
# =============================================================================

import os
import sys
import time
import math
import ctypes
import numpy as np
from PIL import Image

from .scenes import (
    Vec3Struct, CameraParamsStruct, SphereStruct, TriangleStruct,
    AABBStruct, BVHNodeStruct, MaterialStruct,
    build_scene, get_scene_presets
)

# -----------------------------------------------------------------------------
# CUDA Driver API Constants & Types
# -----------------------------------------------------------------------------
CUDA_SUCCESS = 0

CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MAJOR = 75
CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MINOR = 76
CU_DEVICE_ATTRIBUTE_MULTIPROCESSOR_COUNT = 16
CU_DEVICE_ATTRIBUTE_WARP_SIZE = 10
CU_DEVICE_ATTRIBUTE_CLOCK_RATE = 13

class CudaEngine:
    """Manages the lifetime of CUDA Driver API resources and renders scenes on NVIDIA GPU."""

    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.is_cuda_available = False
        self.gpu_name = "N/A"
        self.compute_capability = "0.0"
        self.total_memory_mb = 0.0
        self.free_memory_mb = 0.0
        self.multiprocessors = 0
        self.driver_version = "N/A"

        self.cuda = None
        self.device = None
        self.context = None
        self.module = None
        self.kernel = None

        # GPU Device Pointers
        self.d_accum_buffer = ctypes.c_uint64(0)
        self.d_output_rgba = ctypes.c_uint64(0)
        self.d_camera_params = ctypes.c_uint64(0)
        self.d_spheres = ctypes.c_uint64(0)
        self.d_triangles = ctypes.c_uint64(0)
        self.d_bvh_nodes = ctypes.c_uint64(0)
        self.d_materials = ctypes.c_uint64(0)

        # Host Buffers
        self.h_output_rgba = np.zeros((height, width, 4), dtype=np.uint8)

        # Scene & Render State
        self.current_scene_id = "cornell-box"
        self.frame_index = 0
        self.total_samples_accumulated = 0
        self.max_bounces = 10
        self.samples_per_frame = 1
        self.sky_mode = 0

        # Camera Configuration
        self.cam_position = [0.0, 1.0, 3.2]
        self.cam_target = [0.0, 1.0, 0.0]
        self.cam_up = [0.0, 1.0, 0.0]
        self.cam_fov = 45.0
        self.cam_aperture = 0.00001
        self.cam_focus_dist = 3.2

        # Geometry Counts
        self.num_spheres = 0
        self.num_triangles = 0
        self.num_bvh_nodes = 0
        self.num_materials = 0

        # Metrics
        self.last_kernel_time_ms = 0.0
        self.last_fps = 0.0

        # Initialize Hardware
        self._init_cuda()

    def _init_cuda(self):
        """Initializes CUDA Driver API, creates context on device 0, loads PTX."""
        try:
            if sys.platform == "win32":
                cuda_dll_paths = ["nvcuda.dll", "C:\\Windows\\System32\\nvcuda.dll"]
                for dll_path in cuda_dll_paths:
                    try:
                        self.cuda = ctypes.WinDLL(dll_path)
                        break
                    except Exception:
                        continue
            else:
                cuda_so_paths = [
                    "libcuda.so.1",
                    "libcuda.so",
                    "/usr/lib/x86_64-linux-gnu/libcuda.so.1",
                    "/usr/local/cuda/lib64/stubs/libcuda.so",
                    "/usr/lib/wsl/lib/libcuda.so.1"
                ]
                for so_path in cuda_so_paths:
                    try:
                        self.cuda = ctypes.CDLL(so_path)
                        break
                    except Exception:
                        continue

            if not self.cuda:
                print("[CudaEngine] WARNING: CUDA driver library (nvcuda.dll / libcuda.so) could not be loaded. Running CPU fallback.")
                return

            if self.cuda.cuInit(0) != CUDA_SUCCESS:
                print("[CudaEngine] cuInit failed.")
                return

            device_count = ctypes.c_int()
            self.cuda.cuDeviceGetCount(ctypes.byref(device_count))
            if device_count.value <= 0:
                print("[CudaEngine] No CUDA devices found.")
                return

            # Device 0
            self.device = ctypes.c_int()
            self.cuda.cuDeviceGet(ctypes.byref(self.device), 0)

            # Query Properties
            dev_name = (ctypes.c_char * 256)()
            self.cuda.cuDeviceGetName(dev_name, 256, self.device)
            self.gpu_name = dev_name.value.decode("utf-8")

            total_mem = ctypes.c_size_t()
            self.cuda.cuDeviceTotalMem_v2(ctypes.byref(total_mem), self.device)
            self.total_memory_mb = total_mem.value / (1024.0 * 1024.0)

            major = ctypes.c_int()
            minor = ctypes.c_int()
            self.cuda.cuDeviceGetAttribute(ctypes.byref(major), CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MAJOR, self.device)
            self.cuda.cuDeviceGetAttribute(ctypes.byref(minor), CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MINOR, self.device)
            self.compute_capability = f"{major.value}.{minor.value}"

            sm_count = ctypes.c_int()
            self.cuda.cuDeviceGetAttribute(ctypes.byref(sm_count), CU_DEVICE_ATTRIBUTE_MULTIPROCESSOR_COUNT, self.device)
            self.multiprocessors = sm_count.value

            drv_ver = ctypes.c_int()
            self.cuda.cuDriverGetVersion(ctypes.byref(drv_ver))
            self.driver_version = f"{drv_ver.value // 1000}.{(drv_ver.value % 100) // 10}"

            # Create CUDA Context
            self.context = ctypes.c_void_p()
            res = self.cuda.cuCtxCreate_v2(ctypes.byref(self.context), 0, self.device)
            if res != CUDA_SUCCESS:
                print(f"[CudaEngine] cuCtxCreate failed with error code: {res}")
                return

            # Load Compiled PTX
            ptx_path = os.path.join(os.path.dirname(__file__), "raytracer_kernel.ptx")
            if not os.path.exists(ptx_path):
                print(f"[CudaEngine] PTX file not found at: {ptx_path}")
                return

            with open(ptx_path, "rb") as f:
                ptx_data = f.read()

            self.module = ctypes.c_void_p()
            res = self.cuda.cuModuleLoadData(ctypes.byref(self.module), ptx_data)
            if res != CUDA_SUCCESS:
                print(f"[CudaEngine] cuModuleLoadData failed with error code: {res}")
                return

            self.kernel = ctypes.c_void_p()
            res = self.cuda.cuModuleGetFunction(ctypes.byref(self.kernel), self.module, b"renderKernel")
            if res != CUDA_SUCCESS:
                print(f"[CudaEngine] cuModuleGetFunction renderKernel failed: {res}")
                return

            self.is_cuda_available = True
            print(f"[CudaEngine] SUCCESS: GPU Initialized -> {self.gpu_name} (Compute {self.compute_capability}, {self.total_memory_mb:.1f} MB VRAM)")

            # Allocate Screen Buffers & Load Initial Scene
            self._ensure_context()
            self._allocate_screen_buffers()
            self.load_scene(self.current_scene_id)

        except Exception as e:
            print(f"[CudaEngine] Exception during CUDA initialization: {e}")
            self.is_cuda_available = False

    def _ensure_context(self):
        """Ensures the CUDA context is attached to the calling thread."""
        if self.is_cuda_available and self.context:
            self.cuda.cuCtxSetCurrent(self.context)

    def _allocate_screen_buffers(self):
        """Allocates GPU accumulation (float4) and output (RGBA8) image buffers."""
        if not self.is_cuda_available:
            return
        self._ensure_context()

        # Free previous if already allocated
        if self.d_accum_buffer.value != 0:
            self.cuda.cuMemFree_v2(self.d_accum_buffer)
            self.d_accum_buffer = ctypes.c_uint64(0)
        if self.d_output_rgba.value != 0:
            self.cuda.cuMemFree_v2(self.d_output_rgba)
            self.d_output_rgba = ctypes.c_uint64(0)

        # float4 per pixel = 16 bytes per pixel
        accum_bytes = self.width * self.height * 16
        # uint8 RGBA = 4 bytes per pixel
        output_bytes = self.width * self.height * 4

        res1 = self.cuda.cuMemAlloc_v2(ctypes.byref(self.d_accum_buffer), accum_bytes)
        if res1 != CUDA_SUCCESS:
            print(f"[CudaEngine] Failed to allocate accumulation buffer: code {res1}")
            self.d_accum_buffer = ctypes.c_uint64(0)
            return

        res2 = self.cuda.cuMemAlloc_v2(ctypes.byref(self.d_output_rgba), output_bytes)
        if res2 != CUDA_SUCCESS:
            print(f"[CudaEngine] Failed to allocate output RGBA buffer: code {res2}")
            self.d_output_rgba = ctypes.c_uint64(0)
            return

        self.h_output_rgba = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Single camera struct
        if self.d_camera_params.value == 0:
            self.cuda.cuMemAlloc_v2(ctypes.byref(self.d_camera_params), ctypes.sizeof(CameraParamsStruct))

    def cleanup(self):
        """Releases all allocated GPU buffers and destroys CUDA context."""
        if not self.is_cuda_available or not self.cuda:
            return
        try:
            self._ensure_context()
            for ptr_name in ['d_accum_buffer', 'd_output_rgba', 'd_camera_params', 'd_spheres', 'd_triangles', 'd_bvh_nodes', 'd_materials']:
                ptr = getattr(self, ptr_name, None)
                if ptr and ptr.value != 0:
                    self.cuda.cuMemFree_v2(ptr)
                    setattr(self, ptr_name, ctypes.c_uint64(0))

            if self.module and self.module.value != 0:
                self.cuda.cuModuleUnload(self.module)
                self.module = None

            if self.context and self.context.value != 0:
                self.cuda.cuCtxDestroy_v2(self.context)
                self.context = None

            self.is_cuda_available = False
            print("[CudaEngine] Cleaned up CUDA resources successfully.")
        except Exception as e:
            print(f"[CudaEngine] Error during cleanup: {e}")

    def __del__(self):
        self.cleanup()

    def update_resolution(self, width, height):
        """Updates rendering canvas dimensions and reallocates GPU memory."""
        if width == self.width and height == self.height:
            return
        self.width = width
        self.height = height
        self._allocate_screen_buffers()
        self.reset_accumulation()

    def update_camera(self, position=None, target=None, fov=None, aperture=None, focus_dist=None):
        """Updates camera position, orientation, and lens optics."""
        changed = False
        if position is not None and position != self.cam_position:
            self.cam_position = list(position)
            changed = True
        if target is not None and target != self.cam_target:
            self.cam_target = list(target)
            changed = True
        if fov is not None and fov != self.cam_fov:
            self.cam_fov = float(fov)
            changed = True
        if aperture is not None and aperture != self.cam_aperture:
            self.cam_aperture = float(aperture)
            changed = True
        if focus_dist is not None and focus_dist != self.cam_focus_dist:
            self.cam_focus_dist = float(focus_dist)
            changed = True

        if changed:
            self.reset_accumulation()

    def _sync_camera_to_device(self):
        """Computes camera coordinate frame vectors and uploads struct to device."""
        self._ensure_context()
        aspect_ratio = float(self.width) / float(self.height)
        theta = math.radians(self.cam_fov)
        h = math.tan(theta / 2.0)
        viewport_height = 2.0 * h
        viewport_width = aspect_ratio * viewport_height

        # Orthonormal basis
        lookfrom = np.array(self.cam_position, dtype=np.float32)
        lookat = np.array(self.cam_target, dtype=np.float32)
        vup = np.array(self.cam_up, dtype=np.float32)

        w = lookfrom - lookat
        w_len = np.linalg.norm(w)
        w = w / (w_len if w_len > 0 else 1.0)

        u = np.cross(vup, w)
        u_len = np.linalg.norm(u)
        u = u / (u_len if u_len > 0 else 1.0)

        v = np.cross(w, u)

        focus = self.cam_focus_dist
        horizontal = focus * viewport_width * u
        vertical = focus * viewport_height * v
        lower_left = lookfrom - horizontal / 2.0 - vertical / 2.0 - focus * w

        cam = CameraParamsStruct()
        cam.origin = Vec3Struct(lookfrom[0], lookfrom[1], lookfrom[2])
        cam.lowerLeftCorner = Vec3Struct(lower_left[0], lower_left[1], lower_left[2])
        cam.horizontal = Vec3Struct(horizontal[0], horizontal[1], horizontal[2])
        cam.vertical = Vec3Struct(vertical[0], vertical[1], vertical[2])
        cam.u = Vec3Struct(u[0], u[1], u[2])
        cam.v = Vec3Struct(v[0], v[1], v[2])
        cam.w = Vec3Struct(w[0], w[1], w[2])
        cam.lensRadius = float(self.cam_aperture / 2.0)
        cam.focusDist = float(focus)

        if self.is_cuda_available and self.d_camera_params.value != 0:
            self.cuda.cuMemcpyHtoD_v2(self.d_camera_params, ctypes.byref(cam), ctypes.sizeof(CameraParamsStruct))

    def load_scene(self, scene_id):
        """Loads a scene preset, builds BVH, and uploads geometry & materials to GPU."""
        self._ensure_context()
        self.current_scene_id = scene_id
        spheres, triangles, bvh_nodes, materials = build_scene(scene_id)

        # Set default camera from presets
        for preset in get_scene_presets():
            if preset["id"] == scene_id:
                cam = preset["defaultCamera"]
                self.cam_position = list(cam["position"])
                self.cam_target = list(cam["target"])
                self.cam_fov = float(cam["fov"])
                self.cam_aperture = float(cam["aperture"])
                self.cam_focus_dist = float(cam["focusDist"])
                self.sky_mode = int(preset["skyMode"])
                break

        self.num_spheres = len(spheres)
        self.num_triangles = len(triangles)
        self.num_bvh_nodes = len(bvh_nodes)
        self.num_materials = len(materials)

        if self.is_cuda_available:
            # Free old buffers
            for ptr in [self.d_spheres, self.d_triangles, self.d_bvh_nodes, self.d_materials]:
                if ptr.value != 0:
                    self.cuda.cuMemFree_v2(ptr)

            # Upload Spheres
            if spheres:
                s_arr = (SphereStruct * len(spheres))(*spheres)
                self.cuda.cuMemAlloc_v2(ctypes.byref(self.d_spheres), ctypes.sizeof(s_arr))
                self.cuda.cuMemcpyHtoD_v2(self.d_spheres, ctypes.byref(s_arr), ctypes.sizeof(s_arr))

            # Upload Triangles
            if triangles:
                t_arr = (TriangleStruct * len(triangles))(*triangles)
                self.cuda.cuMemAlloc_v2(ctypes.byref(self.d_triangles), ctypes.sizeof(t_arr))
                self.cuda.cuMemcpyHtoD_v2(self.d_triangles, ctypes.byref(t_arr), ctypes.sizeof(t_arr))

            # Upload BVH Nodes
            if bvh_nodes:
                b_arr = (BVHNodeStruct * len(bvh_nodes))(*bvh_nodes)
                self.cuda.cuMemAlloc_v2(ctypes.byref(self.d_bvh_nodes), ctypes.sizeof(b_arr))
                self.cuda.cuMemcpyHtoD_v2(self.d_bvh_nodes, ctypes.byref(b_arr), ctypes.sizeof(b_arr))

            # Upload Materials
            if materials:
                m_arr = (MaterialStruct * len(materials))(*materials)
                self.cuda.cuMemAlloc_v2(ctypes.byref(self.d_materials), ctypes.sizeof(m_arr))
                self.cuda.cuMemcpyHtoD_v2(self.d_materials, ctypes.byref(m_arr), ctypes.sizeof(m_arr))

        self.reset_accumulation()
        print(f"[CudaEngine] Loaded Scene '{scene_id}': {self.num_spheres} Spheres, {self.num_triangles} Triangles, {self.num_bvh_nodes} BVH Nodes, {self.num_materials} Materials.")

    def reset_accumulation(self):
        """Resets the progressive frame index and accumulation buffer."""
        self.frame_index = 0
        self.total_samples_accumulated = 0

    def render_frame(self, samples=None, max_bounces=None):
        """Dispatches an asynchronous CUDA path tracing kernel pass on the NVIDIA GPU."""
        self._ensure_context()
        if samples is not None:
            self.samples_per_frame = samples
        if max_bounces is not None:
            self.max_bounces = max_bounces

        start_time = time.perf_counter()

        if self.is_cuda_available and self.kernel is not None:
            # Sync Camera
            self._sync_camera_to_device()

            # Grid & Block Dimension Layout (2D tiles of 16x16 threads = 256 threads/block)
            block_dim_x = 16
            block_dim_y = 16
            grid_dim_x = (self.width + block_dim_x - 1) // block_dim_x
            grid_dim_y = (self.height + block_dim_y - 1) // block_dim_y

            # Kernel Arguments List Matching renderKernel signature
            p_width = ctypes.c_int(self.width)
            p_height = ctypes.c_int(self.height)
            p_samples = ctypes.c_int(self.samples_per_frame)
            p_bounces = ctypes.c_int(self.max_bounces)
            p_frame_idx = ctypes.c_int(self.frame_index)
            p_sky_mode = ctypes.c_int(self.sky_mode)
            p_num_spheres = ctypes.c_int(self.num_spheres)
            p_num_triangles = ctypes.c_int(self.num_triangles)
            p_num_bvh = ctypes.c_int(self.num_bvh_nodes)
            p_num_mats = ctypes.c_int(self.num_materials)

            kernel_args = [
                ctypes.byref(self.d_accum_buffer),
                ctypes.byref(self.d_output_rgba),
                ctypes.byref(p_width),
                ctypes.byref(p_height),
                ctypes.byref(p_samples),
                ctypes.byref(p_bounces),
                ctypes.byref(p_frame_idx),
                ctypes.byref(p_sky_mode),
                ctypes.byref(self.d_camera_params),
                ctypes.byref(self.d_spheres),
                ctypes.byref(p_num_spheres),
                ctypes.byref(self.d_triangles),
                ctypes.byref(p_num_triangles),
                ctypes.byref(self.d_bvh_nodes),
                ctypes.byref(p_num_bvh),
                ctypes.byref(self.d_materials),
                ctypes.byref(p_num_mats)
            ]
            args_array = (ctypes.c_void_p * len(kernel_args))(*[ctypes.cast(p, ctypes.c_void_p) for p in kernel_args])

            # Launch CUDA Kernel on GPU
            res = self.cuda.cuLaunchKernel(
                self.kernel,
                grid_dim_x, grid_dim_y, 1,
                block_dim_x, block_dim_y, 1,
                0, None, args_array, None
            )

            if res != CUDA_SUCCESS:
                print(f"[CudaEngine] cuLaunchKernel failed with error: {res}")
            else:
                # Synchronize GPU
                self.cuda.cuCtxSynchronize()

                # Transfer Frame Output (DtoH)
                self.cuda.cuMemcpyDtoH_v2(
                    ctypes.c_void_p(self.h_output_rgba.ctypes.data),
                    self.d_output_rgba,
                    self.width * self.height * 4
                )

            # Query remaining VRAM
            free_mem = ctypes.c_size_t()
            total_mem = ctypes.c_size_t()
            self.cuda.cuMemGetInfo_v2(ctypes.byref(free_mem), ctypes.byref(total_mem))
            self.free_memory_mb = free_mem.value / (1024.0 * 1024.0)

        else:
            # CPU Fallback Pattern
            self._render_cpu_fallback()

        elapsed = (time.perf_counter() - start_time) * 1000.0 # ms
        self.last_kernel_time_ms = elapsed
        self.last_fps = 1000.0 / elapsed if elapsed > 0 else 0.0

        self.frame_index += 1
        self.total_samples_accumulated += self.samples_per_frame

        return self.h_output_rgba

    def _render_cpu_fallback(self):
        """Clean procedural CPU fallback when CUDA is not present."""
        # Simple procedural gradient pattern
        x = np.linspace(0, 1, self.width)
        y = np.linspace(0, 1, self.height)
        xx, yy = np.meshgrid(x, y)
        self.h_output_rgba[:, :, 0] = (xx * 180 + 30).astype(np.uint8)
        self.h_output_rgba[:, :, 1] = (yy * 160 + 40).astype(np.uint8)
        self.h_output_rgba[:, :, 2] = 200
        self.h_output_rgba[:, :, 3] = 255

    def get_status(self):
        """Returns hardware, performance, and current render progress metrics."""
        mrays_per_sec = (self.width * self.height * self.samples_per_frame) / (self.last_kernel_time_ms * 1000.0) if self.last_kernel_time_ms > 0 else 0.0
        return {
            "cudaAvailable": self.is_cuda_available,
            "gpuName": self.gpu_name,
            "computeCapability": self.compute_capability,
            "totalMemoryMB": round(self.total_memory_mb, 1),
            "freeMemoryMB": round(self.free_memory_mb, 1),
            "multiprocessors": self.multiprocessors,
            "driverVersion": self.driver_version,
            "backend": "cuda_gpu" if self.is_cuda_available else "cpu_fallback",
            "sceneId": self.current_scene_id,
            "width": self.width,
            "height": self.height,
            "frameIndex": self.frame_index,
            "totalSamples": self.total_samples_accumulated,
            "samplesPerFrame": self.samples_per_frame,
            "maxBounces": self.max_bounces,
            "kernelTimeMs": round(self.last_kernel_time_ms, 2),
            "fps": round(self.last_fps, 1),
            "mraysPerSecond": round(mrays_per_sec, 2),
            "primitives": {
                "spheres": self.num_spheres,
                "triangles": self.num_triangles,
                "bvhNodes": self.num_bvh_nodes,
                "materials": self.num_materials
            }
        }
