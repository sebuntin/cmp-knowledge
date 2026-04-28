---
type: source
created: 2026-04-26
updated: 2026-04-26
source_file: raw/OHOS SkiaRenderer渲染管线设计.md
ingested: 2026-04-26
tags:
  - SkiaRenderer
  - XComponent
  - EGL
  - OpenGL
  - 自渲染
  - 策略模式
  - ComposeSceneRender
related:
  - "[[融合渲染架构]]"
  - "[[Messenger通信机制]]"
  - "[[RenderNode生命周期]]"
---

# OHOS SkiaRenderer 渲染管线设计

## 摘要

本文档描述 OHOS 自渲染路径（SkiaRenderer）的完整渲染管线架构。OHOS 不使用 Skiko 的 SkiaLayer（空壳实现），而是将渲染职责拆散到四层中：ArkTS XComponent 容器、C++ EGL 上下文管理、Kotlin 策略模式隔离、Skia GPU 渲染管线。

## 关键发现

- **SkiaLayer 空壳**：OHOS 上 SkiaLayer 是空实现，渲染职责由 XComponentRender（C++）、ComposeSceneRender（Kotlin）等协作完成
- **6 个策略接口隔离**：SurfaceLifecycleHandler、FrameDispatcher、DrawPipeline、InputStrategy、ContentBindingStrategy、MediatorRenderDelegate
- **EGL 资源分层**：eglDisplay + eglConfig 进程共享（static），eglSurface + eglContext 每实例独立
- **ComposeSceneRender 三种绘制模式**：draw（常规）、drawWithCanvas（外部画布）、drawByPictureRecorder（录制模式）
- **尺寸通知迂回路径**：EGL surface resize → Messenger → ComposeSizeProxy → @State 更新

## 重要细节

### 帧渲染完整流程

```
VSync → OnFrameCallbackCB → controller.onFrame → frameDispatcher.onFrame
→ EglPrepareDraw(eglMakeCurrent) → drawPipeline.onDraw → mediator.onDraw
→ ComposeSceneRender.draw → ensureSurface → clear → onDraw → flush
→ EglFinishDraw(eglSwapBuffers) → 系统合成显示
```

### 与 FusionRenderer 关键差异

| 维度 | SkiaRenderer | FusionRenderer |
|------|-------------|----------------|
| Surface 来源 | XComponent + EGL | RenderNode |
| 帧循环 | XComponent VSync + 后台心跳 | postFrameCallback |
| 绘制后 | eglSwapBuffers | 系统自动合成 |
| 内容绑定 | mediator 创建时立即 | 延迟到 onSurfaceChanged |
| 后台心跳 | 需要 | 不需要 |
| 尺寸通知 | ComposeSizeProxy 迂回 | onAreaChange 直接 |

### SkiaRendererMediatorDelegate 特点

draw() 忽略传入的 canvas 参数，因为 ComposeSceneRender 自己管理 Surface 和 GPU 上下文。

## 与已有知识的关联

- 补充了 [[融合渲染架构]] 的自渲染路径细节，与 FusionRenderer 形成完整对比
- [[Messenger通信机制]] 在自渲染路径中承担尺寸通知的迂回通道
- 与 [[RenderNode生命周期]] 形成两种渲染路径的节点管理对比
