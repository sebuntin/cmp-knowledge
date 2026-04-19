---
type: source
source_file: raw/Coil图片解码与零拷贝优化方案.md
ingested: 2026-04-19
tags:
  - CMP
  - 图片解码
  - Coil
  - 零拷贝
  - OHOS
  - 性能优化
  - DMA
  - SkImage
---

# Coil 图片解码与零拷贝优化方案

## 摘要

本文档分析了 CMP 融合渲染架构中 Coil 图片解码流程的性能瓶颈：图片解码到 DMA 内存后，`Bitmap.Companion.makeFromImage` 会通过 `Canvas.drawImageRect` 触发一次 DMA 到 CPU 内存的冗余拷贝（4K 图片约 33MB，耗时 10-15ms）。方案提出新增 `SkiaImageWrapper` 直接包装 SkImage，支持采样（isSampled）场景，让 GPU 直接从 DMA 内存读取并按需缩放，实现零拷贝解码。优化后 4K 图片内存占用从 66MB 降至 33MB，消除 10-15ms 拷贝延迟，采样场景传输浪费降至零。

## 关键发现

1. **两次内存操作中第二次是冗余的**：`Image.makeFromEncoded` 已将图片解码到 DMA 内存（GPU 可直接访问），但 `Bitmap.makeFromImage` 再将其拷贝到 CPU 内存，完全多余。
2. **拷贝瓶颈发生在 `SkCanvas::onDrawImageRect2`**：该函数调用 `OH_Drawing_CanvasDrawPixelMapRectConstraint`，从 DMA PixelMap 拷贝到 Canvas 绑定的 CPU Bitmap 内存。
3. **采样场景浪费更严重**：4K 图片采样到 1080p 时，需传输 33MB DMA 数据但只保留 8MB，传输效率仅 24%。
4. **GPU 硬件缩放可替代 CPU 软件缩放**：`drawImageRect` 在 src/dst 尺寸不同时，GPU 可直接从 DMA 内存读取并缩放，无需 CPU 中转。
5. **零拷贝方案通过 `SkiaImageWrapper` 实现**：直接持有 SkImage 引用，存储目标尺寸，`draw()` 方法根据是否采样选择绘制策略，无 Bitmap 转换、无 Canvas 分配、无内存拷贝。
6. **方案支持运行时开关**：通过 `coil.zeroCopy.enabled` 系统属性控制，可随时回滚到传统 Bitmap 路径。

## 重要细节

### 内存数据流（当前方案）

```
Image.makeFromEncoded(bytes)
  → SkImage_OH::buildPixelmap()
  → OH_ImageSourceNative_CreatePixelmapUsingAllocator(DMA)  ✅ DMA 内存分配
  → fDecodePixelmapIsDMA = true
      ↓ 冗余拷贝 ↓
Bitmap.makeFromImage(image, options)
  → bitmap.allocN32Pixels(dstW, dstH)  ❌ 分配 CPU 内存
  → Canvas(bitmap).drawImageRect(...)  ❌ JNI → C++
  → SkCanvas::onDrawImageRect2(...)
  → OH_Drawing_CanvasDrawPixelMapRectConstraint(
       fDrawingCanvas,           // 目标：CPU 内存
       getOHPixelmap(),          // 源：DMA 内存
       src, dst, ...
    )                            ❌ DMA → CPU 拷贝
```

### 关键代码路径

| 文件 | 函数/类 | 作用 |
|------|---------|------|
| `utils.nonAndroid.kt:24-63` | `Bitmap.Companion.makeFromImage` | 拷贝入口：分配 CPU Bitmap + Canvas 绘制 |
| `Canvas.kt:459-479` | `_nDrawImageRect` | JNI 调用桥接 |
| `SkCanvas.cpp:2803-2881` | `onDrawImageRect2` | C++ 层调用 OH_Drawing API 执行拷贝 |
| `SkImage_OH.cpp:174-213` | `buildPixelmap` | DMA 内存分配，使用 `IMAGE_ALLOCATOR_TYPE_DMA` |

### SkiaImageWrapper 核心设计

```kotlin
class SkiaImageWrapper(
    private val skiaImage: SkiaImage,
    private val targetWidth: Int,   // 支持采样目标尺寸
    private val targetHeight: Int
) : Image {
    val isSampled: Boolean
        get() = targetWidth != skiaImage.width || targetHeight != skiaImage.height

    override fun draw(canvas: Canvas) {
        // 采样场景：GPU 直接从 DMA 读取并缩放
        // 非采样场景：GPU 直接从 DMA 读取原始尺寸
        nativeCanvas.drawImageRect(skiaImage, src, dst, FilterMode.LINEAR, null, true)
    }
}
```

### 性能收益量化（4K RGBA 图片）

| 指标 | 原始尺寸场景 | 采样 1080p 场景 |
|------|------------|----------------|
| 拷贝消除 | 33MB → 0MB | 33MB→8MB → 0MB |
| 时间节省 | ~10-15ms | ~10-15ms |
| 内存节省 | 66MB → 33MB (-50%) | 41MB → 33MB (-20%) |

### 实施计划

- **Phase 1**（6 天）：创建 `SkiaImageWrapper`、修改 `SkiaImageDecoder`、单元测试、性能基准测试
- **Phase 2**（7 天）：CMP 示例应用集成、格式兼容性测试、采样场景测试、内存泄漏检测
- **Phase 3**（6 天）：灰度发布（可选开关 `coil.zeroCopy.enabled`）、监控、全量发布

## 与已有知识的关联

- [[融合渲染架构]] -- 零拷贝优化建立在 CMP 融合渲染架构的 DMA 内存分配机制之上，优化的是 SkImage_OH 到最终渲染的中间路径
- [[SkCanvas]] -- 拷贝瓶颈定位在 `SkCanvas::onDrawImageRect2` 中对 `OH_Drawing_CanvasDrawPixelMapRectConstraint` 的调用；零拷贝方案直接利用 `drawImageRect` 让 GPU 从 DMA 读取
- [[OH_Drawing命令转换]] -- 拷贝发生的底层机制是 OH_Drawing API 将 DMA PixelMap 数据转换为 Canvas 目标内存内容
- [[SkPicture与脏区管理]] -- 零拷贝路径中 `drawImageRect` 的绘制命令仍会通过 Picture 录制进入渲染管线

## 来源

- 源文档：`raw/Coil图片解码与零拷贝优化方案.md`（v5.0，2025-02-03，CMP 架构团队）
- 关键文件：
  - `third_party/coil/coil-core/src/nonAndroidMain/kotlin/coil3/util/utils.nonAndroid.kt` -- 拷贝入口
  - `third_party/OHRender/OHRender/src/core/SkCanvas.cpp` -- C++ 层拷贝实现
  - `third_party/OHRender/OHRender/src/image/SkImage_OH.cpp` -- DMA 内存分配
  - `third_party/coil/coil-core/src/nonAndroidMain/kotlin/coil3/decode/SkiaImageDecoder.kt` -- 解码器（需修改）
