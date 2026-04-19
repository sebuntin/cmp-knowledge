---
type: source
source_file: raw/coil+skia自渲染解码原理.md
ingested: 2026-04-19
tags:
  - CMP
  - 图片解码
  - Coil
  - Skia
  - 自渲染
---

# Coil + Skia 自渲染下延迟解码分析

## 摘要

本文分析了 Coil 图片加载库在 Skia 自渲染路径下的延迟解码机制。`SkiaImage.makeFromEncoded(bytes)` 仅创建 `SkImage_Lazy` 并持有编码数据引用，不分配像素内存、不执行解码；真正的解码发生在首次 `canvas.drawImageRect()` 调用时，由 `SkBitmapDevice` 触发 `getROPixels` → `SkBitmapCache::Alloc`（分配像素内存）→ `SkCodec` 执行解码。后续绘制直接命中 `SkBitmapCache` 缓存，无需重复解码。该分析基于 `self_render_1.9.2_develop` 分支的 Skia 源码。

## 关键发现

- **延迟解码设计**：`makeFromEncoded` 只创建 `SkImage_Lazy` + `SkCodecImageGenerator`，编码数据以 `SkData` 引用形式持有，整个图片加载阶段零像素内存分配、零解码操作。
- **绘制时解码触发**：首次 `drawImageRect` 是解码的唯一触发点。调用链为 `SkBitmapDevice::drawImageRect` → `SkImage_Lazy::getROPixels` → `SkBitmapCache::Alloc`（`sk_malloc` 分配像素内存）→ `SkCodecImageGenerator::onGetPixels`（调用 SkCodec 真正解码）。
- **SkBitmapCache 缓存机制**：首次解码后将像素数据写入 `SkBitmapCache`，后续 `drawImageRect` 通过 `SkBitmapCache::Find` 命中缓存直接返回，无重复解码和内存分配。
- **内存分配策略**：`SkBitmapCache::Alloc` 优先使用平台注册的 `DiscardableFactory`（内存压力时可被系统回收，下次访问重新解码），鸿蒙上默认走 `sk_malloc_canfail` 普通堆内存路径。
- **编码数据生命周期**：`SkData`（原始编码字节）由 `SkCodecImageGenerator` 持有，只要 `SkImage_Lazy` 存活就不会释放。解码后像素内存和编码内存同时存在，直到 `SkImage` 被销毁或缓存被 purge。

## 重要细节

### 延迟创建链路（无解码、无内存分配）

1. **`DeferredFromEncodedData`**（`src/codec/SkImageGenerator_FromEncoded.cpp`）：入口函数，将编码数据包装为 `SkCodecImageGenerator`。
2. **`MakeFromEncoded`**：创建 `SkCodecImageGenerator`，仅持有 `SkData` 引用，不调用任何解码 API。
3. **`DeferredFromGenerator`**（`src/image/SkImage_Lazy.cpp:292`）：将 generator 包装进 `SharedGenerator`（带 mutex），创建 `SkImage_Lazy`。
4. **`SkImage_Lazy` 构造函数**（`src/image/SkImage_Lazy.cpp:103`）：仅保存 `fSharedGenerator` 引用，无内存分配。

### 实际解码链路（像素内存分配 + 解码）

1. **`SkBitmapDevice::drawImageRect`**（`src/core/SkBitmapDevice.cpp:414`）：首次 draw 触发解码链，调用 `getROPixels`。
2. **`SkImage_Lazy::getROPixels`**（`src/image/SkImage_Lazy.cpp:110`）：先查 `SkBitmapCache`，未命中则分配内存并解码。
3. **`SkBitmapCache::Alloc`**（`src/core/SkBitmapCache.cpp:188`）：计算 `width * height * bytesPerPixel`，通过 `sk_malloc_canfail` 或 `DiscardableMemory` 分配像素内存。
4. **`SkCodecImageGenerator::onGetPixels`**（`src/codec/SkCodecImageGenerator.cpp:89`）：调用 `fCodec->getPixels()` 执行真正的图像解码（JPEG/PNG/WebP 等格式）。
5. **`SkBitmapCache::Add`**：解码结果写入缓存，后续绘制命中缓存。

### 缓存与内存要点

- 首次 `drawImageRect` 走完整解码链，分配内存 + 解码。
- 后续 `drawImageRect` 命中 `SkBitmapCache`，直接复用已解码 bitmap。
- 鸿蒙默认使用 `sk_malloc_canfail` 而非 `DiscardableMemory`，意味着解码后像素内存常驻直到 `SkImage` 被释放。
- 解码后编码数据（`SkData`）与像素内存同时驻留内存，存在内存翻倍现象。

## 与已有知识的关联

- [[SkCanvas]] — `drawImageRect` 是 SkCanvas 的核心绘制方法之一，在自渲染路径中由 `SkBitmapDevice` 处理图片绘制，触发延迟解码链。
- [[OH_Drawing命令转换]] — 自渲染路径下 `drawImageRect` 解码后通过 CPU 光栅化直接绘制到 Canvas，不经过 OH_Drawing 命令转换；而融合渲染路径中图片数据会通过 SkPicture 录制转为 OH_Drawing 命令。
- [[融合渲染架构]] — 本文分析的是 SkiaRender（自渲染）路径下的图片解码流程，与融合渲染路径的图片处理机制存在差异。融合渲染路径中 Canvas 来源于 RenderNode 回调，图片解码可能涉及不同的缓存和绘制策略。

## 来源

- 源文件：`raw/coil+skia自渲染解码原理.md`
- 分析路径：`self_render_1.9.2_develop/third_party/skiko/skiko/skia-pack/skia`
- 涉及 Skia 源码文件：
  - `src/codec/SkImageGenerator_FromEncoded.cpp`
  - `src/image/SkImage_Lazy.cpp`
  - `src/core/SkBitmapDevice.cpp`
  - `src/core/SkBitmapCache.cpp`
  - `src/codec/SkCodecImageGenerator.cpp`
