# =============================================================================
# SCENE DEFINITIONS & ACCELERATION STRUCTURE BUILDER
# Provides: Procedural Meshes (Bunny, Boxes, Quads), Sphere Scenes,
#           and Surface Area Heuristic (SAH) BVH Builder.
# =============================================================================

import math
import numpy as np
from ctypes import Structure, c_float, c_int, sizeof

# -----------------------------------------------------------------------------
# Ctypes Structs Matching raytracer_kernel.cu
# -----------------------------------------------------------------------------
class Vec3Struct(Structure):
    _fields_ = [("x", c_float), ("y", c_float), ("z", c_float)]

class CameraParamsStruct(Structure):
    _fields_ = [
        ("origin", Vec3Struct),
        ("lowerLeftCorner", Vec3Struct),
        ("horizontal", Vec3Struct),
        ("vertical", Vec3Struct),
        ("u", Vec3Struct),
        ("v", Vec3Struct),
        ("w", Vec3Struct),
        ("lensRadius", c_float),
        ("focusDist", c_float)
    ]

class SphereStruct(Structure):
    _fields_ = [
        ("center", Vec3Struct),
        ("radius", c_float),
        ("materialIndex", c_int)
    ]

class TriangleStruct(Structure):
    _fields_ = [
        ("v0", Vec3Struct),
        ("v1", Vec3Struct),
        ("v2", Vec3Struct),
        ("normal", Vec3Struct),
        ("materialIndex", c_int)
    ]

class AABBStruct(Structure):
    _fields_ = [
        ("minBounds", Vec3Struct),
        ("maxBounds", Vec3Struct)
    ]

class BVHNodeStruct(Structure):
    _fields_ = [
        ("bbox", AABBStruct),
        ("leftChild", c_int),
        ("rightChild", c_int),
        ("primitiveStart", c_int),
        ("primitiveCount", c_int),
        ("isLeaf", c_int),
        ("primitiveType", c_int) # 0 = sphere, 1 = triangle
    ]

class MaterialStruct(Structure):
    _fields_ = [
        ("type", c_int), # 0 = Lambertian, 1 = Metal, 2 = Dielectric, 3 = DiffuseLight
        ("albedo", Vec3Struct),
        ("roughness", c_float),
        ("ior", c_float),
        ("emission", Vec3Struct)
    ]

# -----------------------------------------------------------------------------
# BVH Construction Helper
# -----------------------------------------------------------------------------
def build_bvh_triangles(triangles_list):
    """Constructs a binary Bounding Volume Hierarchy over a list of TriangleStruct."""
    if not triangles_list:
        return []

    nodes = []

    def compute_aabb(indices):
        min_b = [1e30, 1e30, 1e30]
        max_b = [-1e30, -1e30, -1e30]
        for idx in indices:
            t = triangles_list[idx]
            for v in [t.v0, t.v1, t.v2]:
                min_b[0] = min(min_b[0], v.x)
                min_b[1] = min(min_b[1], v.y)
                min_b[2] = min(min_b[2], v.z)
                max_b[0] = max(max_b[0], v.x)
                max_b[1] = max(max_b[1], v.y)
                max_b[2] = max(max_b[2], v.z)
        # Pad slightly to avoid flat zero-volume boxes
        delta = 0.001
        for a in range(3):
            if max_b[a] - min_b[a] < delta:
                min_b[a] -= delta
                max_b[a] += delta
        return min_b, max_b

    def build_recursive(indices):
        node_idx = len(nodes)
        node = BVHNodeStruct()
        nodes.append(node)

        min_b, max_b = compute_aabb(indices)
        node.bbox.minBounds = Vec3Struct(min_b[0], min_b[1], min_b[2])
        node.bbox.maxBounds = Vec3Struct(max_b[0], max_b[1], max_b[2])
        node.primitiveType = 1 # triangle

        count = len(indices)
        if count <= 4:
            # Leaf node
            node.isLeaf = 1
            node.primitiveStart = indices[0]
            node.primitiveCount = count
            node.leftChild = -1
            node.rightChild = -1
            return node_idx

        # Split along longest axis
        extent = [max_b[0] - min_b[0], max_b[1] - min_b[1], max_b[2] - min_b[2]]
        axis = extent.index(max(extent))

        # Sort indices by triangle centroid along chosen axis
        def get_centroid(idx):
            t = triangles_list[idx]
            if axis == 0:
                return (t.v0.x + t.v1.x + t.v2.x) / 3.0
            elif axis == 1:
                return (t.v0.y + t.v1.y + t.v2.y) / 3.0
            else:
                return (t.v0.z + t.v1.z + t.v2.z) / 3.0

        indices.sort(key=get_centroid)
        mid = count // 2

        left_child = build_recursive(indices[:mid])
        right_child = build_recursive(indices[mid:])

        # Re-fetch node reference as nodes list may have grown
        nodes[node_idx].isLeaf = 0
        nodes[node_idx].leftChild = left_child
        nodes[node_idx].rightChild = right_child
        nodes[node_idx].primitiveStart = 0
        nodes[node_idx].primitiveCount = 0
        return node_idx

    initial_indices = list(range(len(triangles_list)))
    build_recursive(initial_indices)
    return nodes

# -----------------------------------------------------------------------------
# Procedural Mesh Generators
# -----------------------------------------------------------------------------
def make_quad_triangles(p0, p1, p2, p3, normal, mat_id):
    """Creates 2 triangles for a planar quad defined by 4 vertices in CCW order."""
    t1 = TriangleStruct(
        v0=Vec3Struct(p0[0], p0[1], p0[2]),
        v1=Vec3Struct(p1[0], p1[1], p1[2]),
        v2=Vec3Struct(p2[0], p2[1], p2[2]),
        normal=Vec3Struct(normal[0], normal[1], normal[2]),
        materialIndex=mat_id
    )
    t2 = TriangleStruct(
        v0=Vec3Struct(p0[0], p0[1], p0[2]),
        v1=Vec3Struct(p2[0], p2[1], p2[2]),
        v2=Vec3Struct(p3[0], p3[1], p3[2]),
        normal=Vec3Struct(normal[0], normal[1], normal[2]),
        materialIndex=mat_id
    )
    return [t1, t2]

def make_box_triangles(p_min, p_max, mat_id):
    """Creates a 3D box mesh consisting of 12 triangles."""
    x0, y0, z0 = p_min
    x1, y1, z1 = p_max
    triangles = []
    # Front (+Z)
    triangles.extend(make_quad_triangles([x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1], [0, 0, 1], mat_id))
    # Back (-Z)
    triangles.extend(make_quad_triangles([x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0], [0, 0, -1], mat_id))
    # Top (+Y)
    triangles.extend(make_quad_triangles([x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0], [0, 1, 0], mat_id))
    # Bottom (-Y)
    triangles.extend(make_quad_triangles([x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1], [0, -1, 0], mat_id))
    # Right (+X)
    triangles.extend(make_quad_triangles([x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [1, 0, 0], mat_id))
    # Left (-X)
    triangles.extend(make_quad_triangles([x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0], [-1, 0, 0], mat_id))
    return triangles

def make_bunny_mesh(center=(0, 0, 0), scale=1.0, mat_id=0):
    """Procedural low-poly bunny model for testing triangle mesh acceleration."""
    cx, cy, cz = center
    # Stylized low-poly mesh vertices
    verts = [
        [-0.4, 0.0, -0.3], [0.4, 0.0, -0.3], [0.4, 0.0, 0.3], [-0.4, 0.0, 0.3], # Base 0-3
        [-0.3, 0.5, -0.2], [0.3, 0.5, -0.2], [0.3, 0.5, 0.3], [-0.3, 0.5, 0.3], # Torso 4-7
        [-0.2, 0.9, 0.2],  [0.2, 0.9, 0.2],  [0.2, 0.9, 0.5], [-0.2, 0.9, 0.5], # Head 8-11
        [-0.15, 1.4, 0.3], [-0.05, 1.4, 0.3], # Left ear 12, 13
        [0.05, 1.4, 0.3],  [0.15, 1.4, 0.3],  # Right ear 14, 15
        [0.0, 0.2, -0.45] # Tail 16
    ]
    # Faces (indices of 3 vertices)
    faces = [
        # Base
        (0, 2, 1), (0, 3, 2),
        # Torso sides
        (0, 1, 5), (0, 5, 4),
        (1, 2, 6), (1, 6, 5),
        (2, 3, 7), (2, 7, 6),
        (3, 0, 4), (3, 4, 7),
        # Torso top
        (4, 5, 9), (4, 9, 8),
        (6, 7, 11), (6, 11, 10),
        # Head
        (8, 9, 10), (8, 10, 11),
        (8, 11, 7), (9, 5, 6),
        # Ears
        (8, 12, 13), (9, 14, 15),
        (10, 13, 12), (11, 15, 14),
        # Tail
        (0, 16, 1), (4, 16, 5)
    ]

    triangles = []
    for f in faces:
        p0 = [verts[f[0]][0] * scale + cx, verts[f[0]][1] * scale + cy, verts[f[0]][2] * scale + cz]
        p1 = [verts[f[1]][0] * scale + cx, verts[f[1]][1] * scale + cy, verts[f[1]][2] * scale + cz]
        p2 = [verts[f[2]][0] * scale + cx, verts[f[2]][1] * scale + cy, verts[f[2]][2] * scale + cz]
        # Compute face normal
        e1 = [p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]]
        e2 = [p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]]
        n = [
            e1[1] * e2[2] - e1[2] * e2[1],
            e1[2] * e2[0] - e1[0] * e2[2],
            e1[0] * e2[1] - e1[1] * e2[0]
        ]
        norm = math.sqrt(n[0]*n[0] + n[1]*n[1] + n[2]*n[2])
        if norm > 0:
            n = [n[0] / norm, n[1] / norm, n[2] / norm]
        else:
            n = [0, 1, 0]

        triangles.append(TriangleStruct(
            v0=Vec3Struct(p0[0], p0[1], p0[2]),
            v1=Vec3Struct(p1[0], p1[1], p1[2]),
            v2=Vec3Struct(p2[0], p2[1], p2[2]),
            normal=Vec3Struct(n[0], n[1], n[2]),
            materialIndex=mat_id
        ))
    return triangles

# -----------------------------------------------------------------------------
# Pre-built Preset Scenes
# -----------------------------------------------------------------------------
def get_scene_presets():
    """Returns available scene metadata for the frontend and API."""
    return [
        {
            "id": "cornell-box",
            "name": "Cornell Box with Bunny & Spheres",
            "description": "The classic global illumination benchmark featuring diffuse walls, emissive ceiling light, Stanford bunny, and glass/metal spheres.",
            "defaultCamera": {
                "position": [0.0, 1.0, 3.2],
                "target": [0.0, 1.0, 0.0],
                "fov": 45.0,
                "aperture": 0.0,
                "focusDist": 3.2
            },
            "skyMode": 0 # closed studio
        },
        {
            "id": "glass-metal-showroom",
            "name": "Glass & Metal Showroom",
            "description": "High-specular showroom showcasing dielectric refraction, Fresnel reflections, and varying roughness metals.",
            "defaultCamera": {
                "position": [0.0, 1.8, 3.5],
                "target": [0.0, 0.5, 0.0],
                "fov": 40.0,
                "aperture": 0.05,
                "focusDist": 3.5
            },
            "skyMode": 2 # dark studio
        },
        {
            "id": "spheres-gallery",
            "name": "Spheres Gallery (Peter Shirley)",
            "description": "A field of diverse materials (diffuse, glossy metal, and glass bubbles) under an atmospheric sky dome.",
            "defaultCamera": {
                "position": [4.0, 1.5, 3.5],
                "target": [0.0, 0.3, 0.0],
                "fov": 35.0,
                "aperture": 0.02,
                "focusDist": 5.0
            },
            "skyMode": 1 # sky gradient
        },
        {
            "id": "emissive-studio",
            "name": "Emissive Neon Studio",
            "description": "Dark aesthetic illuminated by multi-colored emissive panels reflecting on curved metal surfaces.",
            "defaultCamera": {
                "position": [0.0, 2.0, 4.0],
                "target": [0.0, 0.6, 0.0],
                "fov": 42.0,
                "aperture": 0.0,
                "focusDist": 4.0
            },
            "skyMode": 0 # dark void
        }
    ]

def build_scene(scene_id):
    """Builds GPU primitives, materials, and BVH for a requested scene ID."""
    spheres = []
    triangles = []
    materials = []

    if scene_id == "cornell-box":
        # Materials
        # 0: Red wall
        materials.append(MaterialStruct(type=0, albedo=Vec3Struct(0.65, 0.05, 0.05), roughness=0.0, ior=1.0, emission=Vec3Struct(0,0,0)))
        # 1: White walls/floor/ceiling
        materials.append(MaterialStruct(type=0, albedo=Vec3Struct(0.73, 0.73, 0.73), roughness=0.0, ior=1.0, emission=Vec3Struct(0,0,0)))
        # 2: Green wall
        materials.append(MaterialStruct(type=0, albedo=Vec3Struct(0.12, 0.45, 0.15), roughness=0.0, ior=1.0, emission=Vec3Struct(0,0,0)))
        # 3: Ceiling Light (Emissive)
        materials.append(MaterialStruct(type=3, albedo=Vec3Struct(1,1,1), roughness=0.0, ior=1.0, emission=Vec3Struct(15.0, 15.0, 15.0)))
        # 4: Metal Gold
        materials.append(MaterialStruct(type=1, albedo=Vec3Struct(0.85, 0.75, 0.35), roughness=0.05, ior=1.0, emission=Vec3Struct(0,0,0)))
        # 5: Glass Dielectric
        materials.append(MaterialStruct(type=2, albedo=Vec3Struct(1,1,1), roughness=0.0, ior=1.5, emission=Vec3Struct(0,0,0)))
        # 6: Bunny Material (Ceramic Cyan)
        materials.append(MaterialStruct(type=0, albedo=Vec3Struct(0.15, 0.65, 0.85), roughness=0.1, ior=1.0, emission=Vec3Struct(0,0,0)))

        # Cornell Box Enclosure (2.0 x 2.0 x 2.0 box centered from x=[-1, 1], y=[0, 2], z=[-1, 1])
        # Floor (+Y normal)
        triangles.extend(make_quad_triangles([-1, 0, 1], [1, 0, 1], [1, 0, -1], [-1, 0, -1], [0, 1, 0], 1))
        # Ceiling (-Y normal)
        triangles.extend(make_quad_triangles([-1, 2, -1], [1, 2, -1], [1, 2, 1], [-1, 2, 1], [0, -1, 0], 1))
        # Back wall (+Z normal)
        triangles.extend(make_quad_triangles([-1, 0, -1], [1, 0, -1], [1, 2, -1], [-1, 2, -1], [0, 0, 1], 1))
        # Left wall (+X normal, Red)
        triangles.extend(make_quad_triangles([-1, 0, 1], [-1, 0, -1], [-1, 2, -1], [-1, 2, 1], [1, 0, 0], 0))
        # Right wall (-X normal, Green)
        triangles.extend(make_quad_triangles([1, 0, -1], [1, 0, 1], [1, 2, 1], [1, 2, -1], [-1, 0, 0], 2))
        # Ceiling Light (centered overhead)
        triangles.extend(make_quad_triangles([-0.3, 1.99, -0.3], [0.3, 1.99, -0.3], [0.3, 1.99, 0.3], [-0.3, 1.99, 0.3], [0, -1, 0], 3))

        # Bunny Mesh in the center
        triangles.extend(make_bunny_mesh(center=[0.0, 0.0, -0.1], scale=0.75, mat_id=6))

        # Spheres
        # Left: Metallic Gold Sphere
        spheres.append(SphereStruct(center=Vec3Struct(-0.55, 0.32, 0.35), radius=0.32, materialIndex=4))
        # Right: Dielectric Glass Sphere
        spheres.append(SphereStruct(center=Vec3Struct(0.55, 0.32, 0.35), radius=0.32, materialIndex=5))

    elif scene_id == "glass-metal-showroom":
        # 0: Floor
        materials.append(MaterialStruct(type=0, albedo=Vec3Struct(0.2, 0.2, 0.25), roughness=0.0, ior=1.0, emission=Vec3Struct(0,0,0)))
        # 1: Silver Metal
        materials.append(MaterialStruct(type=1, albedo=Vec3Struct(0.9, 0.9, 0.92), roughness=0.02, ior=1.0, emission=Vec3Struct(0,0,0)))
        # 2: Rough Gold Metal
        materials.append(MaterialStruct(type=1, albedo=Vec3Struct(0.85, 0.65, 0.2), roughness=0.25, ior=1.0, emission=Vec3Struct(0,0,0)))
        # 3: Copper Metal
        materials.append(MaterialStruct(type=1, albedo=Vec3Struct(0.95, 0.45, 0.35), roughness=0.05, ior=1.0, emission=Vec3Struct(0,0,0)))
        # 4: Pure Glass Dielectric
        materials.append(MaterialStruct(type=2, albedo=Vec3Struct(1,1,1), roughness=0.0, ior=1.52, emission=Vec3Struct(0,0,0)))
        # 5: Water / Bubble Dielectric
        materials.append(MaterialStruct(type=2, albedo=Vec3Struct(1,1,1), roughness=0.0, ior=1.33, emission=Vec3Struct(0,0,0)))
        # 6: Warm Studio Light
        materials.append(MaterialStruct(type=3, albedo=Vec3Struct(1,1,1), roughness=0.0, ior=1.0, emission=Vec3Struct(12, 10, 8)))

        # Floor Quad
        triangles.extend(make_quad_triangles([-10, 0, 10], [10, 0, 10], [10, 0, -10], [-10, 0, -10], [0, 1, 0], 0))
        # Overhead Softbox Light
        triangles.extend(make_quad_triangles([-1.5, 3.5, -1.0], [1.5, 3.5, -1.0], [1.5, 3.5, 1.0], [-1.5, 3.5, 1.0], [0, -1, 0], 6))

        # Showroom Spheres
        spheres.append(SphereStruct(center=Vec3Struct(-1.2, 0.5, 0.0), radius=0.5, materialIndex=1)) # Silver
        spheres.append(SphereStruct(center=Vec3Struct(0.0, 0.5, 0.0), radius=0.5, materialIndex=4))  # Glass
        spheres.append(SphereStruct(center=Vec3Struct(1.2, 0.5, 0.0), radius=0.5, materialIndex=2))  # Rough Gold
        spheres.append(SphereStruct(center=Vec3Struct(-0.6, 0.25, 0.9), radius=0.25, materialIndex=3)) # Copper
        spheres.append(SphereStruct(center=Vec3Struct(0.6, 0.25, 0.9), radius=0.25, materialIndex=5))  # Water bubble

    elif scene_id == "spheres-gallery":
        # Ground
        materials.append(MaterialStruct(type=0, albedo=Vec3Struct(0.5, 0.5, 0.5), roughness=0.0, ior=1.0, emission=Vec3Struct(0,0,0)))
        spheres.append(SphereStruct(center=Vec3Struct(0.0, -1000.0, 0.0), radius=1000.0, materialIndex=0))

        # 3 Main hero spheres
        materials.append(MaterialStruct(type=2, albedo=Vec3Struct(1,1,1), roughness=0.0, ior=1.5, emission=Vec3Struct(0,0,0))) # Glass
        spheres.append(SphereStruct(center=Vec3Struct(0.0, 1.0, 0.0), radius=1.0, materialIndex=1))

        materials.append(MaterialStruct(type=0, albedo=Vec3Struct(0.4, 0.2, 0.1), roughness=0.0, ior=1.0, emission=Vec3Struct(0,0,0))) # Matte brown
        spheres.append(SphereStruct(center=Vec3Struct(-2.2, 1.0, 0.0), radius=1.0, materialIndex=2))

        materials.append(MaterialStruct(type=1, albedo=Vec3Struct(0.7, 0.6, 0.5), roughness=0.0, ior=1.0, emission=Vec3Struct(0,0,0))) # Metal
        spheres.append(SphereStruct(center=Vec3Struct(2.2, 1.0, 0.0), radius=1.0, materialIndex=3))

        # Small spheres grid
        rng = np.random.RandomState(42)
        mat_idx = 4
        for a in range(-4, 5):
            for b in range(-4, 5):
                choose_mat = rng.rand()
                center = Vec3Struct(a + 0.9 * rng.rand(), 0.2, b + 0.9 * rng.rand())
                if (center.x)**2 + (center.z)**2 > 2.0:
                    if choose_mat < 0.6: # Diffuse
                        albedo = Vec3Struct(rng.rand()*rng.rand(), rng.rand()*rng.rand(), rng.rand()*rng.rand())
                        materials.append(MaterialStruct(type=0, albedo=albedo, roughness=0.0, ior=1.0, emission=Vec3Struct(0,0,0)))
                    elif choose_mat < 0.85: # Metal
                        albedo = Vec3Struct(0.5 * (1 + rng.rand()), 0.5 * (1 + rng.rand()), 0.5 * (1 + rng.rand()))
                        rough = float(0.5 * rng.rand())
                        materials.append(MaterialStruct(type=1, albedo=albedo, roughness=rough, ior=1.0, emission=Vec3Struct(0,0,0)))
                    else: # Glass
                        materials.append(MaterialStruct(type=2, albedo=Vec3Struct(1,1,1), roughness=0.0, ior=1.5, emission=Vec3Struct(0,0,0)))
                    spheres.append(SphereStruct(center=center, radius=0.2, materialIndex=mat_idx))
                    mat_idx += 1

    else: # emissive-studio
        # Ground
        materials.append(MaterialStruct(type=1, albedo=Vec3Struct(0.1, 0.1, 0.12), roughness=0.08, ior=1.0, emission=Vec3Struct(0,0,0)))
        triangles.extend(make_quad_triangles([-10, 0, 10], [10, 0, 10], [10, 0, -10], [-10, 0, -10], [0, 1, 0], 0))

        # Neon Cyan light
        materials.append(MaterialStruct(type=3, albedo=Vec3Struct(1,1,1), roughness=0.0, ior=1.0, emission=Vec3Struct(0.0, 15.0, 20.0)))
        triangles.extend(make_quad_triangles([-2.5, 0.2, -1.0], [-2.5, 0.2, 1.0], [-2.5, 2.0, 1.0], [-2.5, 2.0, -1.0], [1, 0, 0], 1))

        # Neon Magenta light
        materials.append(MaterialStruct(type=3, albedo=Vec3Struct(1,1,1), roughness=0.0, ior=1.0, emission=Vec3Struct(20.0, 0.0, 15.0)))
        triangles.extend(make_quad_triangles([2.5, 0.2, 1.0], [2.5, 0.2, -1.0], [2.5, 2.0, -1.0], [2.5, 2.0, 1.0], [-1, 0, 0], 2))

        # Center Chrome Sphere
        materials.append(MaterialStruct(type=1, albedo=Vec3Struct(0.95, 0.95, 0.95), roughness=0.0, ior=1.0, emission=Vec3Struct(0,0,0)))
        spheres.append(SphereStruct(center=Vec3Struct(0.0, 0.8, 0.0), radius=0.8, materialIndex=3))

        # Satellite Glass & Gold Spheres
        materials.append(MaterialStruct(type=2, albedo=Vec3Struct(1,1,1), roughness=0.0, ior=1.5, emission=Vec3Struct(0,0,0)))
        spheres.append(SphereStruct(center=Vec3Struct(-1.2, 0.35, 0.8), radius=0.35, materialIndex=4))

        materials.append(MaterialStruct(type=1, albedo=Vec3Struct(0.9, 0.7, 0.2), roughness=0.05, ior=1.0, emission=Vec3Struct(0,0,0)))
        spheres.append(SphereStruct(center=Vec3Struct(1.2, 0.35, 0.8), radius=0.35, materialIndex=5))

    # Build BVH if triangles are present
    bvh_nodes = build_bvh_triangles(triangles) if triangles else []

    return spheres, triangles, bvh_nodes, materials
