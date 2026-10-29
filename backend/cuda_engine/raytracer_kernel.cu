// =============================================================================
// CUDA RAY TRACER - HIGH-PERFORMANCE PATH TRACING KERNEL
// Target: NVIDIA Ampere (sm_86) / CUDA Compute Capability 5.0+
// Supports: Progressive Accumulation, BVH Traversal, Multi-Material PBR,
//           Möller-Trumbore Triangles, Spheres, Russian Roulette, DoF Camera.
// =============================================================================

#define PI 3.14159265358979323846f
#define TWO_PI 6.28318530717958647692f
#define EPSILON 1e-5f
#define INFINITY_FLT 1e30f

// -----------------------------------------------------------------------------
// Native High-Speed Hardware Math Primitives
// -----------------------------------------------------------------------------
inline float ptx_sqrt(float x) {
    float res;
    asm("sqrt.approx.f32 %0, %1;" : "=f"(res) : "f"(x));
    return res;
}
inline float ptx_fabs(float x) {
    float res;
    asm("abs.f32 %0, %1;" : "=f"(res) : "f"(x));
    return res;
}
inline float ptx_sin(float x) {
    float res;
    asm("sin.approx.f32 %0, %1;" : "=f"(res) : "f"(x));
    return res;
}
inline float ptx_cos(float x) {
    float res;
    asm("cos.approx.f32 %0, %1;" : "=f"(res) : "f"(x));
    return res;
}
inline float ptx_fmin(float a, float b) {
    float res;
    asm("min.f32 %0, %1, %2;" : "=f"(res) : "f"(a), "f"(b));
    return res;
}
inline float ptx_fmax(float a, float b) {
    float res;
    asm("max.f32 %0, %1, %2;" : "=f"(res) : "f"(a), "f"(b));
    return res;
}
inline float pow5(float x) {
    float x2 = x * x;
    return x2 * x2 * x;
}

struct float4 {
    float x, y, z, w;
};

inline float4 make_float4(float x, float y, float z, float w) {
    float4 res;
    res.x = x; res.y = y; res.z = z; res.w = w;
    return res;
}

// -----------------------------------------------------------------------------
// Vector Math
// -----------------------------------------------------------------------------
struct Vec3 {
    float x, y, z;

    inline Vec3() : x(0.0f), y(0.0f), z(0.0f) {}
    inline Vec3(float val) : x(val), y(val), z(val) {}
    inline Vec3(float x_, float y_, float z_) : x(x_), y(y_), z(z_) {}

    inline Vec3 operator-() const { return Vec3(-x, -y, -z); }
    inline Vec3 operator+(const Vec3& b) const { return Vec3(x + b.x, y + b.y, z + b.z); }
    inline Vec3 operator-(const Vec3& b) const { return Vec3(x - b.x, y - b.y, z - b.z); }
    inline Vec3 operator*(const Vec3& b) const { return Vec3(x * b.x, y * b.y, z * b.z); }
    inline Vec3 operator*(float s) const { return Vec3(x * s, y * s, z * s); }
    inline Vec3 operator/(float s) const { float inv = 1.0f / s; return Vec3(x * inv, y * inv, z * inv); }

    inline Vec3& operator+=(const Vec3& b) { x += b.x; y += b.y; z += b.z; return *this; }
    inline Vec3& operator*=(const Vec3& b) { x *= b.x; y *= b.y; z *= b.z; return *this; }
    inline Vec3& operator*=(float s) { x *= s; y *= s; z *= s; return *this; }

    inline float lengthSquared() const { return x * x + y * y + z * z; }
    inline float length() const { return ptx_sqrt(lengthSquared()); }
};

inline Vec3 operator*(float s, const Vec3& v) { return Vec3(s * v.x, s * v.y, s * v.z); }
inline float dot(const Vec3& a, const Vec3& b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline Vec3 cross(const Vec3& a, const Vec3& b) {
    return Vec3(
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x
    );
}
inline Vec3 unitVector(const Vec3& v) {
    float len = v.length();
    return len > 0.0f ? v / len : Vec3(0.0f, 0.0f, 0.0f);
}
inline Vec3 reflect(const Vec3& v, const Vec3& n) {
    return v - 2.0f * dot(v, n) * n;
}
inline Vec3 refract(const Vec3& uv, const Vec3& n, float etai_over_etat) {
    float cos_theta = ptx_fmin(dot(-uv, n), 1.0f);
    Vec3 r_out_perp = etai_over_etat * (uv + cos_theta * n);
    float k = ptx_fmax(0.0f, 1.0f - r_out_perp.lengthSquared());
    Vec3 r_out_parallel = -ptx_sqrt(k) * n;
    return r_out_perp + r_out_parallel;
}
inline Vec3 minVec(const Vec3& a, const Vec3& b) {
    return Vec3(ptx_fmin(a.x, b.x), ptx_fmin(a.y, b.y), ptx_fmin(a.z, b.z));
}
inline Vec3 maxVec(const Vec3& a, const Vec3& b) {
    return Vec3(ptx_fmax(a.x, b.x), ptx_fmax(a.y, b.y), ptx_fmax(a.z, b.z));
}

// -----------------------------------------------------------------------------
// Ultra-Fast PCG32 GPU Random Number Generator
// -----------------------------------------------------------------------------
struct RNG {
    unsigned long long state;
    unsigned long long inc;

    inline void init(unsigned long long initstate, unsigned long long initseq) {
        state = 0U;
        inc = (initseq << 1u) | 1u;
        nextUint();
        state += initstate;
        nextUint();
    }

    inline unsigned int nextUint() {
        unsigned long long oldstate = state;
        state = oldstate * 6364136223846793005ULL + inc;
        unsigned int xorshifted = (unsigned int)(((oldstate >> 18u) ^ oldstate) >> 27u);
        unsigned int rot = (unsigned int)(oldstate >> 59u);
        return (xorshifted >> rot) | (xorshifted << ((~rot + 1u) & 31));
    }

    inline float nextFloat() {
        return (nextUint() >> 8) * (1.0f / 16777216.0f);
    }

    inline float nextFloat(float minVal, float maxVal) {
        return minVal + (maxVal - minVal) * nextFloat();
    }

    inline Vec3 randomUnitVector() {
        float z = nextFloat(-1.0f, 1.0f);
        float a = nextFloat(0.0f, TWO_PI);
        float r = ptx_sqrt(ptx_fmax(0.0f, 1.0f - z * z));
        return Vec3(r * ptx_cos(a), r * ptx_sin(a), z);
    }

    inline Vec3 randomInUnitDisk() {
        float r = ptx_sqrt(nextFloat());
        float theta = nextFloat(0.0f, TWO_PI);
        return Vec3(r * ptx_cos(theta), r * ptx_sin(theta), 0.0f);
    }
};

// -----------------------------------------------------------------------------
// Ray & Hit Structures
// -----------------------------------------------------------------------------
struct Ray {
    Vec3 origin;
    Vec3 direction;

    inline Ray() {}
    inline Ray(const Vec3& o, const Vec3& d) : origin(o), direction(d) {}
    inline Vec3 at(float t) const { return origin + direction * t; }
};

struct HitRecord {
    Vec3 p;
    Vec3 normal;
    float t;
    int materialIndex;
    bool frontFace;

    inline void setFaceNormal(const Ray& r, const Vec3& outwardNormal) {
        frontFace = dot(r.direction, outwardNormal) < 0.0f;
        normal = frontFace ? outwardNormal : -outwardNormal;
    }
};

// -----------------------------------------------------------------------------
// Camera Model
// -----------------------------------------------------------------------------
struct CameraParams {
    Vec3 origin;
    Vec3 lowerLeftCorner;
    Vec3 horizontal;
    Vec3 vertical;
    Vec3 u, v, w;
    float lensRadius;
    float focusDist;
};

inline Ray getCameraRay(const CameraParams& cam, float s, float t, RNG& rng) {
    Vec3 rd = cam.lensRadius * rng.randomInUnitDisk();
    Vec3 offset = cam.u * rd.x + cam.v * rd.y;
    return Ray(
        cam.origin + offset,
        cam.lowerLeftCorner + s * cam.horizontal + t * cam.vertical - cam.origin - offset
    );
}

// -----------------------------------------------------------------------------
// Primitives & BVH Structures
// -----------------------------------------------------------------------------
struct Sphere {
    Vec3 center;
    float radius;
    int materialIndex;

    inline bool hit(const Ray& r, float tMin, float tMax, HitRecord& rec) const {
        Vec3 oc = r.origin - center;
        float a = dot(r.direction, r.direction);
        float half_b = dot(oc, r.direction);
        float c = oc.lengthSquared() - radius * radius;
        float discriminant = half_b * half_b - a * c;

        if (discriminant < 0.0f) return false;
        float sqrtd = ptx_sqrt(discriminant);

        float root = (-half_b - sqrtd) / a;
        if (root < tMin || root > tMax) {
            root = (-half_b + sqrtd) / a;
            if (root < tMin || root > tMax) return false;
        }

        rec.t = root;
        rec.p = r.at(rec.t);
        Vec3 outwardNormal = (rec.p - center) / radius;
        rec.setFaceNormal(r, outwardNormal);
        rec.materialIndex = materialIndex;
        return true;
    }
};

struct Triangle {
    Vec3 v0, v1, v2;
    Vec3 normal;
    int materialIndex;

    inline bool hit(const Ray& r, float tMin, float tMax, HitRecord& rec) const {
        // Möller-Trumbore Algorithm
        Vec3 edge1 = v1 - v0;
        Vec3 edge2 = v2 - v0;
        Vec3 h = cross(r.direction, edge2);
        float a = dot(edge1, h);

        if (ptx_fabs(a) < 1e-7f) return false;
        float f = 1.0f / a;
        Vec3 s = r.origin - v0;
        float u = f * dot(s, h);
        if (u < 0.0f || u > 1.0f) return false;

        Vec3 q = cross(s, edge1);
        float v = f * dot(r.direction, q);
        if (v < 0.0f || u + v > 1.0f) return false;

        float t = f * dot(edge2, q);
        if (t < tMin || t > tMax) return false;

        rec.t = t;
        rec.p = r.at(t);
        rec.setFaceNormal(r, normal);
        rec.materialIndex = materialIndex;
        return true;
    }
};

struct AABB {
    Vec3 minBounds;
    Vec3 maxBounds;

    inline bool hit(const Ray& r, float tMin, float tMax) const {
        for (int a = 0; a < 3; a++) {
            float origin = a == 0 ? r.origin.x : (a == 1 ? r.origin.y : r.origin.z);
            float dir = a == 0 ? r.direction.x : (a == 1 ? r.direction.y : r.direction.z);
            float minVal = a == 0 ? minBounds.x : (a == 1 ? minBounds.y : minBounds.z);
            float maxVal = a == 0 ? maxBounds.x : (a == 1 ? maxBounds.y : maxBounds.z);

            float invD = 1.0f / dir;
            float t0 = (minVal - origin) * invD;
            float t1 = (maxVal - origin) * invD;
            if (invD < 0.0f) {
                float tmp = t0; t0 = t1; t1 = tmp;
            }
            tMin = t0 > tMin ? t0 : tMin;
            tMax = t1 < tMax ? t1 : tMax;
            if (tMax <= tMin) return false;
        }
        return true;
    }
};

struct BVHNode {
    AABB bbox;
    int leftChild;
    int rightChild;
    int primitiveStart;
    int primitiveCount;
    int isLeaf; // 1 = leaf, 0 = interior
    int primitiveType; // 0 = sphere, 1 = triangle
};

// -----------------------------------------------------------------------------
// Materials
// -----------------------------------------------------------------------------
enum MaterialType {
    MAT_LAMBERTIAN = 0,
    MAT_METAL = 1,
    MAT_DIELECTRIC = 2,
    MAT_DIFFUSE_LIGHT = 3
};

struct Material {
    int type;
    Vec3 albedo;
    float roughness;
    float ior;
    Vec3 emission;
};

inline float reflectance(float cosine, float refIdx) {
    // Schlick's approximation with fast pow5
    float r0 = (1.0f - refIdx) / (1.0f + refIdx);
    r0 = r0 * r0;
    return r0 + (1.0f - r0) * pow5(1.0f - cosine);
}

inline bool scatter(
    const Material& mat,
    const Ray& rIn,
    const HitRecord& rec,
    Vec3& attenuation,
    Ray& scattered,
    RNG& rng
) {
    if (mat.type == MAT_LAMBERTIAN) {
        Vec3 scatterDirection = rec.normal + rng.randomUnitVector();
        if (scatterDirection.lengthSquared() < 1e-8f) {
            scatterDirection = rec.normal;
        }
        scattered = Ray(rec.p, unitVector(scatterDirection));
        attenuation = mat.albedo;
        return true;
    }
    else if (mat.type == MAT_METAL) {
        Vec3 reflected = reflect(unitVector(rIn.direction), rec.normal);
        scattered = Ray(rec.p, unitVector(reflected + mat.roughness * rng.randomUnitVector()));
        attenuation = mat.albedo;
        return dot(scattered.direction, rec.normal) > 0.0f;
    }
    else if (mat.type == MAT_DIELECTRIC) {
        attenuation = Vec3(1.0f, 1.0f, 1.0f);
        float refractionRatio = rec.frontFace ? (1.0f / mat.ior) : mat.ior;

        Vec3 unitDir = unitVector(rIn.direction);
        float cosTheta = ptx_fmin(dot(-unitDir, rec.normal), 1.0f);
        float sinTheta = ptx_sqrt(ptx_fmax(0.0f, 1.0f - cosTheta * cosTheta));

        bool cannotRefract = refractionRatio * sinTheta > 1.0f;
        Vec3 direction;

        if (cannotRefract || reflectance(cosTheta, refractionRatio) > rng.nextFloat()) {
            direction = reflect(unitDir, rec.normal);
        } else {
            direction = refract(unitDir, rec.normal, refractionRatio);
        }

        scattered = Ray(rec.p, unitVector(direction));
        return true;
    }
    return false; // MAT_DIFFUSE_LIGHT does not scatter
}

// -----------------------------------------------------------------------------
// Scene Ray-Intersection via Non-Recursive Stack BVH
// -----------------------------------------------------------------------------
inline bool intersectScene(
    const Ray& ray,
    const Sphere* spheres,
    int numSpheres,
    const Triangle* triangles,
    int numTriangles,
    const BVHNode* bvhNodes,
    int numBvhNodes,
    HitRecord& closestRec
) {
    bool hitAnything = false;
    float closestSoFar = INFINITY_FLT;

    if (numBvhNodes > 0) {
        // Stack-based iterative traversal
        int stack[64];
        int stackPtr = 0;
        stack[stackPtr++] = 0; // Root node index

        while (stackPtr > 0) {
            int nodeIdx = stack[--stackPtr];
            const BVHNode& node = bvhNodes[nodeIdx];

            if (node.bbox.hit(ray, 0.001f, closestSoFar)) {
                if (node.isLeaf) {
                    if (node.primitiveType == 0) { // Spheres
                        for (int i = 0; i < node.primitiveCount; i++) {
                            int sIdx = node.primitiveStart + i;
                            if (sIdx < numSpheres) {
                                HitRecord tempRec;
                                if (spheres[sIdx].hit(ray, 0.001f, closestSoFar, tempRec)) {
                                    hitAnything = true;
                                    closestSoFar = tempRec.t;
                                    closestRec = tempRec;
                                }
                            }
                        }
                    } else if (node.primitiveType == 1) { // Triangles
                        for (int i = 0; i < node.primitiveCount; i++) {
                            int tIdx = node.primitiveStart + i;
                            if (tIdx < numTriangles) {
                                HitRecord tempRec;
                                if (triangles[tIdx].hit(ray, 0.001f, closestSoFar, tempRec)) {
                                    hitAnything = true;
                                    closestSoFar = tempRec.t;
                                    closestRec = tempRec;
                                }
                            }
                        }
                    }
                } else {
                    if (node.rightChild >= 0) stack[stackPtr++] = node.rightChild;
                    if (node.leftChild >= 0) stack[stackPtr++] = node.leftChild;
                }
            }
        }
    } else {
        // Fallback linear scan if no BVH is supplied
        for (int i = 0; i < numSpheres; i++) {
            HitRecord tempRec;
            if (spheres[i].hit(ray, 0.001f, closestSoFar, tempRec)) {
                hitAnything = true;
                closestSoFar = tempRec.t;
                closestRec = tempRec;
            }
        }
        for (int i = 0; i < numTriangles; i++) {
            HitRecord tempRec;
            if (triangles[i].hit(ray, 0.001f, closestSoFar, tempRec)) {
                hitAnything = true;
                closestSoFar = tempRec.t;
                closestRec = tempRec;
            }
        }
    }

    return hitAnything;
}

// -----------------------------------------------------------------------------
// Path Tracing Radiance Evaluation
// -----------------------------------------------------------------------------
inline Vec3 evaluateRayColor(
    Ray currentRay,
    const Sphere* spheres,
    int numSpheres,
    const Triangle* triangles,
    int numTriangles,
    const BVHNode* bvhNodes,
    int numBvhNodes,
    const Material* materials,
    int numMaterials,
    int maxBounces,
    int skyMode,
    RNG& rng
) {
    Vec3 accumulatedColor(1.0f, 1.0f, 1.0f);
    Vec3 totalRadiance(0.0f, 0.0f, 0.0f);

    for (int bounce = 0; bounce < maxBounces; bounce++) {
        // Russian Roulette path termination after 3 bounces
        if (bounce >= 3) {
            float maxComponent = ptx_fmax(accumulatedColor.x, ptx_fmax(accumulatedColor.y, accumulatedColor.z));
            float survivalProb = ptx_fmin(maxComponent, 0.95f);
            if (rng.nextFloat() > survivalProb) {
                break;
            }
            accumulatedColor = accumulatedColor / survivalProb;
        }

        HitRecord rec;
        if (intersectScene(currentRay, spheres, numSpheres, triangles, numTriangles, bvhNodes, numBvhNodes, rec)) {
            if (rec.materialIndex >= 0 && rec.materialIndex < numMaterials) {
                const Material& mat = materials[rec.materialIndex];

                // If emissive, add light contribution
                if (mat.type == MAT_DIFFUSE_LIGHT) {
                    totalRadiance += accumulatedColor * mat.emission;
                    break;
                }

                Ray scattered;
                Vec3 attenuation;
                if (scatter(mat, currentRay, rec, attenuation, scattered, rng)) {
                    accumulatedColor *= attenuation;
                    currentRay = scattered;
                } else {
                    break;
                }
            } else {
                break;
            }
        } else {
            // Miss: Sky dome color gradient or dark background
            if (skyMode == 1) {
                Vec3 unitDir = unitVector(currentRay.direction);
                float t = 0.5f * (unitDir.y + 1.0f);
                Vec3 sky = (1.0f - t) * Vec3(1.0f, 1.0f, 1.0f) + t * Vec3(0.5f, 0.7f, 1.0f);
                totalRadiance += accumulatedColor * sky;
            } else if (skyMode == 2) {
                // Dark studio gradient
                Vec3 unitDir = unitVector(currentRay.direction);
                float t = 0.5f * (unitDir.y + 1.0f);
                Vec3 sky = (1.0f - t) * Vec3(0.05f, 0.05f, 0.08f) + t * Vec3(0.15f, 0.18f, 0.25f);
                totalRadiance += accumulatedColor * sky;
            } else {
                // Black background (void / closed studio)
                totalRadiance += accumulatedColor * Vec3(0.01f, 0.01f, 0.01f);
            }
            break;
        }
    }

    return totalRadiance;
}

// -----------------------------------------------------------------------------
// Primary Path Tracing & Temporal Accumulation Kernel
// -----------------------------------------------------------------------------
extern "C" {
__attribute__((nvptx_kernel))
void renderKernel(
    float4* accumBuffer,
    unsigned char* outputRgba,
    int width,
    int height,
    int samplesPerFrame,
    int maxBounces,
    int frameIndex,
    int skyMode,
    const CameraParams* cameraParams,
    const Sphere* spheres,
    int numSpheres,
    const Triangle* triangles,
    int numTriangles,
    const BVHNode* bvhNodes,
    int numBvhNodes,
    const Material* materials,
    int numMaterials
) {
    int tidX;
    asm("mov.u32 %0, %%tid.x;" : "=r"(tidX));
    int tidY;
    asm("mov.u32 %0, %%tid.y;" : "=r"(tidY));
    int blkX;
    asm("mov.u32 %0, %%ctaid.x;" : "=r"(blkX));
    int blkY;
    asm("mov.u32 %0, %%ctaid.y;" : "=r"(blkY));
    int bdimX;
    asm("mov.u32 %0, %%ntid.x;" : "=r"(bdimX));
    int bdimY;
    asm("mov.u32 %0, %%ntid.y;" : "=r"(bdimY));

    int x = blkX * bdimX + tidX;
    int y = blkY * bdimY + tidY;

    if (x >= width || y >= height) return;

    int pixelIndex = y * width + x;

    // Per-pixel PRNG initialized with seed + frameIndex offset
    RNG rng;
    unsigned long long seed = (unsigned long long)pixelIndex * 1999999973ULL + (unsigned long long)frameIndex * 1000000007ULL;
    rng.init(seed, (unsigned long long)pixelIndex);

    Vec3 frameRadiance(0.0f, 0.0f, 0.0f);

    for (int s = 0; s < samplesPerFrame; s++) {
        // Subpixel anti-aliasing jitter
        float u = (float(x) + rng.nextFloat()) / float(width);
        // Correct coordinate mapping: y = 0 is top row, height-1 is bottom
        float v = (float(height - 1 - y) + rng.nextFloat()) / float(height);

        Ray r = getCameraRay(*cameraParams, u, v, rng);
        frameRadiance += evaluateRayColor(
            r,
            spheres, numSpheres,
            triangles, numTriangles,
            bvhNodes, numBvhNodes,
            materials, numMaterials,
            maxBounces, skyMode,
            rng
        );
    }

    // Temporal Accumulation Buffer Update
    float4 prevAccum = accumBuffer[pixelIndex];
    if (frameIndex == 0) {
        prevAccum = make_float4(0.0f, 0.0f, 0.0f, 0.0f);
    }

    float4 newAccum = make_float4(
        prevAccum.x + frameRadiance.x,
        prevAccum.y + frameRadiance.y,
        prevAccum.z + frameRadiance.z,
        prevAccum.w + float(samplesPerFrame)
    );
    accumBuffer[pixelIndex] = newAccum;

    // Running Average
    float totalSamples = newAccum.w > 0.0f ? newAccum.w : 1.0f;
    float r = newAccum.x / totalSamples;
    float g = newAccum.y / totalSamples;
    float b = newAccum.z / totalSamples;

    // Gamma 2.0 correction: sqrt(C)
    r = ptx_sqrt(ptx_fmax(0.0f, r));
    g = ptx_sqrt(ptx_fmax(0.0f, g));
    b = ptx_sqrt(ptx_fmax(0.0f, b));

    // Clamp to [0, 255]
    int outIdx = pixelIndex * 4;
    outputRgba[outIdx + 0] = (unsigned char)(ptx_fmin(ptx_fmax(r * 255.99f, 0.0f), 255.0f));
    outputRgba[outIdx + 1] = (unsigned char)(ptx_fmin(ptx_fmax(g * 255.99f, 0.0f), 255.0f));
    outputRgba[outIdx + 2] = (unsigned char)(ptx_fmin(ptx_fmax(b * 255.99f, 0.0f), 255.0f));
    outputRgba[outIdx + 3] = 255;
}
}
