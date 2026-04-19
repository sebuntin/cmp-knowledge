# Coil 图片解码与零拷贝优化方案

## 目录

1. [背景](#1-背景)
2. [问题分析](#2-问题分析)
3. [零拷贝优化方案](#3-零拷贝优化方案)
4. [实施方案](#4-实施方案)
5. [预期收益](#5-预期收益)
6. [风险评估](#6-风险评估)

---

## 1. 背景

### 1.1 技术栈

CMP（Compose Multiplatform）融合渲染架构中，图片加载和渲染涉及以下核心技术：

- **Kotlin**: Compose Multiplatform UI 框架
- **Coil**: Kotlin 图片加载库
- **Skia**: 跨平台 2D 图形库
- **OH_Drawing**: OHOS（OpenHarmony OS）原生绘图 API
- **OH_PixelmapNative**: OHOS 像素图数据结构（DMA 内存格式）
- **DMA 内存**: 可直接被 GPU 访问的内存

### 1.2 优化目标

实现图片解码到绘制的**零拷贝（Zero-Copy）**优化：
- 消除不必要的 DMA → CPU 内存拷贝
- 让 GPU 直接访问 DMA 内存
- 降低内存占用和提升渲染性能
- **支持采样场景（isSampled）**：图片缩放无需额外内存拷贝

---

## 2. 问题分析

### 2.1 两次关键内存操作点

#### 拷贝点 1：DMA 内存分配（必要）

```kotlin
// Coil: SkiaImageDecoder.kt
val bytes = source.source().use { it.readByteArray() }
val image = Image.makeFromEncoded(bytes)  // ✅ DMA 内存分配
```

```cpp
// C++: SkImage_OH.cpp:174-213
void SkImage_OH::buildPixelmap(...) {
    // ✅ 分配 DMA 内存并解码图片
    err_code = OHDrawingAPI::OH_ImageSourceNative_CreatePixelmapUsingAllocator(
        fImageSource, opts,
        IMAGE_ALLOCATOR_TYPE_DMA,  // DMA 内存类型
        &pixelmap
    );

    fDecodePixelmap.store(pixelmap);
    fDecodePixelmapIsDMA.store(true);  // 标记为 DMA 内存
}
```

**说明**：这是一次**必要的内存分配**，图片直接解码到 DMA 内存中，GPU 可直接访问。

#### 拷贝点 2：Image → Bitmap 转换（性能瓶颈）

```kotlin
// Coil: utils.nonAndroid.kt:24-63
internal fun Bitmap.Companion.makeFromImage(
    image: SkiaImage,
    options: Options,
): Bitmap {
    val srcWidth = image.width
    val srcHeight = image.height

    // ❗ 关键：计算目标尺寸（采样场景：目标尺寸可能小于原始尺寸）
    val (dstWidth, dstHeight) = DecodeUtils.computeDstSize(
        srcWidth = srcWidth,
        srcHeight = srcHeight,
        targetSize = options.size,
        scale = options.scale,
        maxSize = options.maxBitmapSize,
    )

    val bitmap = Bitmap()
    bitmap.allocN32Pixels(outWidth, outHeight)  // ❌ 分配新的 CPU 内存

    Canvas(bitmap).use { canvas ->               // ❌ 关键：使用 Canvas 绘制
        canvas.drawImageRect(                     // ❌ 触发底层拷贝
            image = image,                       // Image 包含 DMA PixelMap
            src = Rect.makeWH(srcWidth.toFloat(), srcHeight.toFloat()),  // 原始尺寸
            dst = Rect.makeWH(outWidth.toFloat(), outHeight.toFloat()),  // 目标尺寸（采样）
        )
    }
    return bitmap
}
```

```kotlin
// Skia: Canvas.kt:459-479
fun drawImageRect(
    image: Image, src: Rect, dst: Rect,
    samplingMode: SamplingMode, paint: Paint?, strict: Boolean
): Canvas {
    Stats.onNativeCall()
    try {
        _nDrawImageRect(  // ❌ JNI 调用到底层 C++
            _ptr,
            getPtr(image),  // Image (包含 DMA PixelMap)
            src.left, src.top, src.right, src.bottom,
            dst.left, dst.top, dst.right, dst.bottom,
            ...
        )
    }
}
```

```cpp
// C++: SkCanvas.cpp:2875-2877
void SkCanvas::onDrawImageRect2(...) {
    // ❌ 内存拷贝发生点：从 DMA PixelMap 拷贝到 CPU Canvas 内存
    OHDrawingAPI::OH_Drawing_CanvasDrawPixelMapRectConstraint(
        fDrawingCanvas,                          // 目标：CPU 内存（Canvas 绑定的 bitmap）
        as_IB((SkImage *)image)->getOHPixelmap(), // 源：DMA 内存
        (OH_Drawing_Rect *)&src,
        (OH_Drawing_Rect *)&dst,
        oh_options,
        (OH_Drawing_SrcRectConstraint)constraint
    );
}
```

### 2.2 内存流向图

```
┌─────────────────────────────────────────────────────────────────────┐
│  第一次：DMA 内存分配                                               │
├─────────────────────────────────────────────────────────────────────┤
│  Image.makeFromEncoded(bytes)                                       │
│      → buildPixelmap()                                              │
│      → OH_ImageSourceNative_CreatePixelmapUsingAllocator(DMA)       │
│      ✅ 图片解码到 DMA 内存（GPU 可直接访问）                        │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  第二次：DMA → CPU 内存拷贝（问题所在）                            │
├─────────────────────────────────────────────────────────────────────┤
│  Bitmap.Companion.makeFromImage(image, options)                     │
│      → 计算目标尺寸（可能采样）                                      │
│      → bitmap.allocN32Pixels(dstW, dstH)  ❌ 分配新的 CPU 内存       │
│      → Canvas(bitmap).use { canvas ->                                 │
│          canvas.drawImageRect(image, src=原始, dst=目标) ❌ 拷贝+缩放│
│      }                                                                  │
│          → _nDrawImageRect(...)             ❌ JNI 调用               │
│              → SkCanvas::onDrawImageRect2(...)                       │
│                  → OH_Drawing_CanvasDrawPixelMapRectConstraint(...)  │
│                      ❌ 从 DMA PixelMap 拷贝到 CPU Canvas 内存      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 采样场景分析

**什么是采样（Sampling）？**

采样是指图片加载时根据显示需求缩小图片尺寸，例如：
- 原始图片：4K (3840×2160)
- 显示尺寸：1080p (1920×1080)
- 采样率：50%
- `isSampled = true`

**当前采样方案的问题**：

| 场景 | 传统方案 | 问题 |
|------|---------|------|
| **原始尺寸** | 分配 33MB CPU 内存，拷贝 33MB DMA→CPU | DMA 内存未被 GPU 直接利用 |
| **采样尺寸** | 分配 8MB CPU 内存（1080p），拷贝 33MB→8MB DMA→CPU | ❌ 拷贝了 33MB 但只保留 8MB，浪费 25MB 传输 |
| **GPU 访问** | 必须通过 CPU 内存中转 | 增加延迟和带宽消耗 |

**关键发现**：即使在采样场景下，DMA → CPU 的拷贝也是不必要的，因为 GPU 可以直接从 DMA 内存读取并缩放！

### 2.4 性能问题量化

**4K RGBA 图片（3840 × 2160 × 4 bytes = 33MB）**：

| 操作 | 原始尺寸场景 | 采样场景（1080p） | 说明 |
|------|-------------|------------------|------|
| DMA 内存分配和解码 | 33MB, ~50ms | 33MB, ~50ms | ✅ 必需，保留原始 DMA 内存 |
| **Image → Bitmap 拷贝** | **33MB, ~10-15ms** | **33MB→8MB, ~10-15ms** | ❌ **DMA → CPU 拷贝** |
| 总内存占用 | 66MB (DMA+CPU) | 41MB (DMA 33MB + CPU 8MB) | ❌ 仍需额外 CPU 内存 |
| 拷贝效率 | 100% | 24% (8/33) | ❌ 采样时传输浪费更大 |

**核心问题**：
- DMA 内存设计为 GPU 可直接访问，但拷贝到 CPU 内存后：
  - GPU 必须通过 CPU 中转访问
  - 采样场景下：拷贝 33MB 但只保留 8MB，传输效率极低
  - PCIe 带宽消耗增加（DMA → CPU → GPU）
  - 需要维护 DMA 与 CPU 内存一致性

---

## 3. 零拷贝优化方案

### 3.1 核心目标

**消除第二次拷贝**：让 GPU 直接访问 DMA 内存并按需缩放，避免 DMA → CPU 拷贝。

### 3.2 方案设计：SkiaImageWrapper（支持采样）

#### 设计思路

创建一个新的 `coil3.Image` 实现，直接包装 SkImage，支持采样场景，完全避免 Bitmap 转换和 Canvas 绘制触发的拷贝。

#### 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│  Image.makeFromEncoded(bytes)                                      │
│  → SkImage_OH                                                      │
│  → fPixelRef: SkPixelRef                                            │
│     → fPixelmap: OH_PixelmapNative (DMA 内存)                      │
│  → fDrawingPixelmap: OH_Drawing_PixelMap*                         │
│  ✅ 图片已解码到 DMA 内存，可直接 GPU 访问                          │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  【新增】SkiaImageWrapper(coil3.Image)                              │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  - 直接持有 SkImage 引用                                        │ │
│  │  - 存储目标尺寸（支持采样）                                      │ │
│  │  - 实现 coil3.Image 接口                                        │ │
│  │  - draw() 根据是否采样选择绘制策略                              │ │
│  │  - 无 Bitmap 转换                                               │ │
│  │  - 无 Canvas(bitmap).use { ... } 调用                           │ │
│  │  - 无 DMA → CPU 拷贝                                             │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  绘制时                                                           │
│  → SkCanvas.drawImageRect(skiaImage, src=原始, dst=目标)           │
│  → GPU 直接从 DMA 内存读取并缩放                                   │
│  ✅ 零拷贝：GPU 直接从 DMA 内存读取并缩放                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 代码实现

#### Step 1: 创建 SkiaImageWrapper（支持采样）

```kotlin
// coil-core/src/commonMain/kotlin/coil3/decode/SkiaImageWrapper.kt
package coil3

import androidx.compose.ui.graphics.Canvas
import coil3.decode.DecodeUtils
import coil3.request.Options
import org.jetbrains.skia.Image as SkiaImage
import org.jetbrains.skia.Rect as SkiaRect

/**
 * 零拷贝的 Image 实现，直接包装 SkImage，支持采样场景
 */
class SkiaImageWrapper(
    private val skiaImage: SkiaImage,
    private val targetWidth: Int = skiaImage.width,   // 目标宽度（默认原始尺寸）
    private val targetHeight: Int = skiaImage.height  // 目标高度（默认原始尺寸）
) : Image {

    // 返回目标尺寸（可能是采样后的尺寸）
    override val width: Int
        get() = targetWidth

    override val height: Int
        get() = targetHeight

    // 返回目标尺寸的内存大小（注意：实际 DMA 内存仍是原始大小）
    override val size: Long
        get() = targetWidth.toLong() * targetHeight.toLong() * 4

    // 判断是否采样
    val isSampled: Boolean
        get() = targetWidth != skiaImage.width || targetHeight != skiaImage.height

    // SkImage 是不可变的，可以共享
    override val shareable: Boolean
        get() = true

    // 零拷贝绘制：根据是否采样选择绘制策略
    override fun draw(canvas: Canvas) {
        val nativeCanvas = canvas.nativeCanvas

        if (isSampled) {
            // 采样场景：绘制时缩放
            // ✅ GPU 直接从 DMA 内存读取并缩放，无需 CPU 中转
            nativeCanvas.drawImageRect(
                skiaImage,
                SkiaRect.makeWH(skiaImage.width.toFloat(), skiaImage.height.toFloat()),  // src: 原始尺寸
                SkiaRect.makeWH(targetWidth.toFloat(), targetHeight.toFloat()),           // dst: 目标尺寸
                org.jetbrains.skia.FilterMode.LINEAR,  // 线性过滤保证缩放质量
                null,
                true
            )
        } else {
            // 非采样场景：直接绘制
            nativeCanvas.drawImageRect(
                skiaImage,
                SkiaRect.makeWH(skiaImage.width.toFloat(), skiaImage.height.toFloat()),
                SkiaRect.makeWH(skiaImage.width.toFloat(), skiaImage.height.toFloat()),
                org.jetbrains.skia.FilterMode.LINEAR,
                null,
                true
            )
        }
    }

    /**
     * 获取底层的 SkImage
     */
    fun getSkiaImage(): SkiaImage = skiaImage
}
```

#### Step 2: 修改 SkiaImageDecoder（支持采样）

```kotlin
// coil-core/src/nonAndroidMain/kotlin/coil3/decode/SkiaImageDecoder.kt
override suspend fun decode(): DecodeResult {
    val bytes = source.source().use { it.readByteArray() }

    // 零拷贝解码：直接创建 SkImage（DMA 内存已分配）
    val skiaImage = org.jetbrains.skia.Image.makeFromEncoded(bytes)

    // 计算目标尺寸（支持采样）
    val (dstWidth, dstHeight) = DecodeUtils.computeDstSize(
        srcWidth = skiaImage.width,
        srcHeight = skiaImage.height,
        targetSize = options.size,
        scale = options.scale,
        maxSize = options.maxBitmapSize,
    )

    // 零拷贝包装：使用 SkiaImageWrapper 而非 Bitmap
    val image = SkiaImageWrapper(
        skiaImage = skiaImage,
        targetWidth = dstWidth,
        targetHeight = dstHeight
    )

    // 判断是否采样
    val isSampled = dstWidth != skiaImage.width || dstHeight != skiaImage.height

    return DecodeResult(image, isSampled)
}
```

### 3.4 采样场景下的零拷贝优势

| 场景 | 传统方案 | 零拷贝方案 | 优势 |
|------|---------|-----------|------|
| **原始尺寸** | 分配 33MB CPU 内存<br>拷贝 33MB DMA→CPU | 无需分配<br>无需拷贝 | 内存 -33MB<br>拷贝 -10-15ms |
| **采样 1080p** | 分配 8MB CPU 内存<br>拷贝 33MB DMA→CPU（浪费 25MB） | 无需分配<br>无需拷贝 | 内存 -8MB<br>拷贝 -10-15ms<br>传输 -25MB |
| **GPU 访问** | CPU 内存 → GPU | DMA 内存 → GPU（直接） | 延迟降低<br>带宽减少 |

**关键优势**：
- GPU 硬件缩放效率远高于 CPU 软件缩放
- 无需传输不必要的数据（采样时尤其明显）
- DMA 内存可被多个目标共享（不同采样率）

---

## 4. 实施方案

### 4.1 实施步骤

**Phase 1: 核心功能开发（6 天）**

| 步骤 | 任务 | 文件 | 预估工作量 |
|------|------|------|-----------|
| 1 | 创建 `SkiaImageWrapper` 类（支持采样） | `coil-core/.../SkiaImageWrapper.kt` | 2 天 |
| 2 | 修改 `SkiaImageDecoder`（计算目标尺寸） | `coil-core/.../SkiaImageDecoder.kt` | 1 天 |
| 3 | 添加单元测试（原始尺寸 + 采样场景） | `coil-core/.../SkiaImageWrapperTest.kt` | 2 天 |
| 4 | 性能基准测试（对比不同采样率） | `coil-core/.../ImageDecoderBenchmark.kt` | 1 天 |

**Phase 2: 集成测试（7 天）**

| 步骤 | 任务 | 预估工作量 |
|------|------|-----------|
| 1 | 集成到 CMP 示例应用 | 2 天 |
| 2 | 兼容性测试（不同图片格式） | 2 天 |
| 3 | 采样场景测试（不同采样率） | 2 天 |
| 4 | 内存泄漏检测 | 1 天 |

**Phase 3: 生产验证（6 天）**

| 步骤 | 任务 | 预估工作量 |
|------|------|-----------|
| 1 | 灰度发布（可选开关） | 2 天 |
| 2 | 监控内存和性能指标 | 持续 |
| 3 | 收集用户反馈 | 持续 |
| 4 | 全量发布 | 1 天 |

**总工作量: 约 19 工作日**

### 4.2 可选开关配置

```kotlin
// coil-core/src/nonAndroidMain/kotlin/coil3/decode/SkiaImageDecoder.kt
class SkiaImageDecoder(
    private val source: ImageSource,
    private val options: Options
) : Decoder {

    private val enableZeroCopy by lazy {
        // 可配置开关，支持热更新
        System.getProperty("coil.zeroCopy.enabled")?.toBoolean() ?: true
    }

    override suspend fun decode(): DecodeResult {
        val bytes = source.source().use { it.readByteArray() }
        val skiaImage = org.jetbrains.skia.Image.makeFromEncoded(bytes)

        // 计算目标尺寸（支持采样）
        val (dstWidth, dstHeight) = DecodeUtils.computeDstSize(
            srcWidth = skiaImage.width,
            srcHeight = skiaImage.height,
            targetSize = options.size,
            scale = options.scale,
            maxSize = options.maxBitmapSize,
        )

        val isSampled = dstWidth != skiaImage.width || dstHeight != skiaImage.height

        return if (enableZeroCopy) {
            // 零拷贝路径
            val image = SkiaImageWrapper(skiaImage, dstWidth, dstHeight)
            DecodeResult(image, isSampled)
        } else {
            // 传统路径（保留用于回滚）
            val bitmap = Bitmap.Companion.makeFromImage(skiaImage, options)
            DecodeResult(bitmap.asImage(), isSampled)
        }
    }
}
```

---

## 5. 预期收益

### 5.1 性能提升对比

#### 原始尺寸场景

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| DMA 内存分配和解码 | 33MB (4K RGBA) | 33MB (4K RGBA) | 持平 |
| **Image → Bitmap 拷贝** | **33MB** | **0MB** | **100%** |
| 拷贝时间 | **~10-15ms** | **0ms** | **100%** |
| 总内存占用 | 66MB (DMA+CPU) | 33MB (仅DMA) | **50%** |

#### 采样场景（1080p）

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| DMA 内存分配和解码 | 33MB (4K RGBA) | 33MB (4K RGBA) | 持平 |
| **Image → Bitmap 拷贝** | **33MB→8MB** | **0MB** | **100%** |
| **数据传输量** | **33MB** | **0MB** | **100%** |
| 拷贝时间 | **~10-15ms** | **0ms** | **100%** |
| 总内存占用 | 41MB (DMA 33MB + CPU 8MB) | 33MB (仅DMA) | **20%** |

### 5.2 GPU 访问优化

| 项目 | 优化前 | 优化后 |
|------|--------|--------|
| GPU 访问方式 | CPU 中转（DMA → CPU → GPU） | 直接访问 DMA 内存 |
| 缩放方式 | CPU 软件缩放 | GPU 硬件缩放 |
| PCIe 带宽消耗 | 高 | 低（采样场景尤其明显） |
| 内存一致性开销 | 需要维护 | 无需维护 |

### 5.3 代码简化

| 项目 | 优化前 | 优化后 |
|------|--------|--------|
| 解码流程 | Image → Bitmap → Image | Image（直接使用） |
| 对象管理 | 多层包装 | 单层包装 |
| 采样处理 | 预先缩放到 CPU 内存 | 绘制时 GPU 缩放 |

---

## 6. 风险评估

### 6.1 技术风险

| 风险项 | 风险等级 | 缓解措施 |
|--------|----------|----------|
| Canvas API 兼容性 | 中 | 充分测试不同使用场景 |
| 图片格式兼容性 | 中 | 测试 PNG/JPEG/GIF/WebP |
| 采样质量差异 | 中 | 对比 CPU 缩放和 GPU 缩放质量 |
| 性能回退 | 低 | 性能基准测试 |

### 6.2 实施风险

| 风险项 | 风险等级 | 缓解措施 |
|--------|----------|----------|
| 开发周期延长 | 中 | 分阶段实施 |
| 测试覆盖不足 | 高 | 完善单元测试（含采样场景） |
| 线上问题 | 中 | 灰度发布 + 监控 |

### 6.3 回滚方案

```kotlin
// 可配置开关，支持热更新
private val enableZeroCopy by lazy {
    System.getProperty("coil.zeroCopy.enabled")?.toBoolean() ?: true
}

override suspend fun decode(): DecodeResult {
    return if (enableZeroCopy) {
        // 零拷贝路径：支持采样
        DecodeResult(SkiaImageWrapper(skiaImage, dstWidth, dstHeight), isSampled)
    } else {
        // 传统路径：保留 Bitmap 转换（支持回滚）
        DecodeResult(bitmap.asImage(), isSampled)
    }
}
```

---

## 7. 附录

### 7.1 关键文件清单

| 文件路径 | 说明 |
|---------|------|
| `third_party/coil/coil-core/src/nonAndroidMain/kotlin/coil3/util/utils.nonAndroid.kt` | **关键文件**：包含 `Bitmap.Companion.makeFromImage` 实现，调用 `Canvas(bitmap).use { canvas.drawImageRect(...) }` |
| `third_party/coil/coil-core/src/nonAndroidMain/kotlin/coil3/decode/SkiaImageDecoder.kt` | Coil 解码器（需修改） |
| `third_party/skiko/skiko/src/commonMain/kotlin/org/jetbrains/skia/Canvas.kt` | Skia Canvas 实现，`drawImageRect` 调用 `_nDrawImageRect` |
| `third_party/OHRender/OHRender/src/core/SkCanvas.cpp` | **关键文件**：`onDrawImageRect2` 调用 `OH_Drawing_CanvasDrawPixelMapRectConstraint` 进行 DMA → CPU 拷贝 |
| `third_party/OHRender/OHRender/src/image/SkImage_OH.cpp` | OHOS Image 实现，DMA 内存分配 |
| `compose/ui/ui-graphics/src/commonMain/kotlin/androidx/compose/ui/graphics/painter/BitmapPainter.kt` | 绘制入口 |

### 7.2 拷贝路径总结

```
完整拷贝路径（第二次拷贝）：

1. Bitmap.Companion.makeFromImage(image, options)
   └── utils.nonAndroid.kt:24-63
   └── 计算目标尺寸（可能采样）

2. bitmap.allocN32Pixels(outWidth, outHeight)
   └── 分配新的 CPU 内存（可能是缩放后的尺寸）

3. Canvas(bitmap).use { canvas ->
       canvas.drawImageRect(
           image,
           src=Rect(原始尺寸),
           dst=Rect(目标尺寸)  // 采样时不同
       )
   }
   └── utils.nonAndroid.kt:55-61

4. _nDrawImageRect(...)
   └── Canvas.kt:469-479 (JNI 调用)

5. SkCanvas::onDrawImageRect2(...)
   └── SkCanvas.cpp:2803-2881

6. OH_Drawing_CanvasDrawPixelMapRectConstraint(
       fDrawingCanvas,              // 目标：CPU 内存
       as_IB(image)->getOHPixelmap(), // 源：DMA 内存
       src, dst,  // src≠dst 时进行缩放
       ...
   )
   └── SkCanvas.cpp:2875-2877
   └── ❌ 内存拷贝 + 缩放：DMA → CPU
```

### 7.3 零拷贝路径总结

```
零拷贝路径（支持采样）：

1. SkiaImageDecoder.decode()
   └── Image.makeFromEncoded(bytes)  // DMA 内存已分配

2. 计算目标尺寸（支持采样）
   └── DecodeUtils.computeDstSize(...)

3. SkiaImageWrapper(skiaImage, targetWidth, targetHeight)
   └── 持有 SkImage 引用（无内存分配）
   └── 存储目标尺寸（用于采样）

4. Image.draw(canvas)
   └── 如果 isSampled:
       SkCanvas.drawImageRect(
           skiaImage,
           src=Rect(原始尺寸),
           dst=Rect(目标尺寸)
       )
       └── ✅ GPU 直接从 DMA 内存读取并缩放
   └── 否则:
       SkCanvas.drawImageRect(
           skiaImage,
           src=Rect(原始尺寸),
           dst=Rect(原始尺寸)
       )
       └── ✅ GPU 直接从 DMA 内存读取
```

---

**文档版本**: v5.0 (修正：支持采样场景 isSampled)
**创建日期**: 2025-02-03
**作者**: CMP 架构团队
**审核状态**: 待审核
