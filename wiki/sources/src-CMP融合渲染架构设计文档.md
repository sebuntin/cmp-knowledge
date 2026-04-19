---
type: source
source_file: CMP融合渲染架构设计文档.md
ingested: 2026-04-19
tags:
  - CMP
  - 融合渲染
  - 架构设计
  - OHOS
---

# src-CMP融合渲染架构设计文档

## 摘要

本文档是 CMP（Compose Multiplatform）融合渲染架构的完整设计文档，详细阐述了在 OHOS（OpenHarmony OS）平台上如何将 Compose UI 的声明式绘制命令通过 SkPicture 录制 → OH_Drawing 命令转换 → ContentModifier 聚合 → RenderNode 挂载的完整数据流，最终由 OHOS RenderService 完成硬件加速渲染。

文档分为六大章：整体架构设计、SkPicture 脏区管理、OH_Drawing 命令转换、ContentModifier 挂载、融合渲染完整流程、性能分析与优化。

## 关键发现

1. **三阶段绑定模型**：编译时绑定（Compose 编译器）→ ArkTS 运行时绑定（NodeContainer + CanvasNodeController）→ Compose 运行时绑定（ComposeSceneMediator.setContent）
2. **帧回调机制**：基于 NodeContainer + RenderFrameCallback，而非 XComponent 的生命周期方法；由 willDraw 事件、触摸事件、尺寸变化触发
3. **脏区管理核心**：通过 `fDrawBounds` 在每次绘制操作时实时合并边界框，`getFinishDrawBounds()` 在完成录制时返回最终脏区，`setRealFrame()` 应用到 RenderNode
4. **双模式回放**：Picture 模式（直接在 Canvas 执行命令，聚合到父节点）和 Node 模式（创建独立 OHRenderNode，通过 ContentModifier 执行）
5. **节点复用机制**：通过 makeClone 克隆、fUnusedCloneNodes 回收、fCacheCloneNodes 缓存的三级复用策略
6. **扩展不缩小策略**：RenderNode 脏区只扩展不缩小，避免频繁重建

## 重要细节

### 数据流全景

```
Compose UI 绘制 (@Composable)
  → RenderNodeLayer (Kotlin) — Picture 录制/缓存
  → SkPictureRecorder (C++) — 创建 Canvas、录制命令、生成 Picture
  → SkCanvas (C++) — 转换为 OH_Drawing 命令、跟踪脏区
  → 脏区计算 (getFinishDrawBounds)
  → SkOHPicture + OHRenderNode — Picture/Node 模式决策
  → ContentModifier 挂载
  → OHOS RenderService — 硬件加速渲染
```

### 关键模块

| 模块 | 位置 | 职责 |
|------|------|------|
| Core (`src/core/`) | OHRender | SkCanvas、SkPictureRecorder、SkOHPicture 等 244 个文件 |
| OH (`src/oh/`) | OHRender | OHRenderNode、OHDrawingAPI — OHOS 平台桥接 |
| ArkUI 集成 | compose/ets | CanvasNodeController、RenderFrameCallback、Compose 主组件 |
| Effects | OHRender | 颜色滤镜、路径效果、图像滤镜 |
| Image | OHRender | SkImage、SkSurface、SkImage_OH |

### 命令映射关系

| SkCanvas 操作 | OH_Drawing 命令 |
|--------------|----------------|
| `drawRect` | `OH_Drawing_CanvasDrawRect` |
| `drawPath` | `OH_Drawing_CanvasDrawPath` |
| `drawText` | `OH_Drawing_CanvasDrawText` |
| `drawImage` | `OH_Drawing_CanvasDrawImage` |
| `save/restore` | `OH_Drawing_CanvasSave/Restore` |
| `translate` | `OH_Drawing_CanvasTranslate` |
| `concat` | `OH_Drawing_CanvasConcatMatrix` |

## 与已有知识的关联

- 本文档是融合渲染路径的核心参考，与 [[渲染模式隔离架构设计文档]] 中的架构描述互补
- [[SkPicture与脏区管理]] 和 [[OH_Drawing命令转换]] 深入展开本文档第二、三章内容
- [[ContentModifier挂载机制]] 深入展开第四章内容

## 原文引用

> 融合渲染方案通过以下方式解决挑战：统一数据流、脏区优化、命令聚合、性能提升

> 脏区是一个矩形区域（SkRect），表示需要重新绘制的区域。通过合并所有绘制操作的边界框计算得出。

> Picture模式：命令直接记录到当前录制的Canvas中，最终聚合到父节点的ContentModifier。Node模式：每个Picture对应一个独立的OHRenderNode，支持独立的脏区管理和变换。
