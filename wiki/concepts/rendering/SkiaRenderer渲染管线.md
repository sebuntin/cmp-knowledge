---
type: concept
created: 2026-04-26
updated: 2026-04-26
sources:
  - raw/OHOS SkiaRenderer渲染管线设计.md
tags:
  - SkiaRenderer
  - 自渲染
  - EGL
  - XComponent
  - 策略模式
related:
  - "[[融合渲染架构]]"
  - "[[帧时钟协作机制]]"
  - "[[三明治混排结构]]"
---

# SkiaRenderer 渲染管线

## 定义

CMP 自渲染路径的完整渲染管线，通过 XComponent + EGL + OpenGL ES 管理 GPU 渲染表面，使用 6 个策略接口与 FusionRenderer 隔离。

## 详解

### 架构四层

| 层 | 核心类 | 职责 |
|---|--------|------|
| ArkTS | SkiaRenderCompose.ets | XComponent 容器、触摸事件 |
| C++ | XComponentRender | EGL 上下文管理、VSync 回调 |
| Kotlin 策略 | 6 个 StrategyImpl | 与 FusionRenderer 隔离 |
| Kotlin 渲染 | ComposeSceneRender | Skia GPU 管线 |

### ComposeSceneRender 三种绘制模式

| 方法 | 场景 |
|------|------|
| draw(timestamp) | 常规渲染：ensureSurface → clear → onDraw → flush |
| drawWithCanvas(canvas, timestamp) | 外部提供画布 |
| drawByPictureRecorder(timestamp) | 录制模式 |

### 与 FusionRenderer 核心差异

- Surface 来自 XComponent + EGL（非 RenderNode）
- 需要 eglSwapBuffers 完成绘制
- 需要后台心跳维持 XComponent VSync
- 尺寸通知通过 Messenger 迂回（非 onAreaChange 直接传递）

## 关键要点

- SkiaLayer 在 OHOS 上是空壳实现，职责分散到四层
- eglDisplay + eglConfig 进程共享，eglSurface + eglContext 每实例独立
- MediatorRenderDelegate.draw() 忽略传入 canvas，因为自己管理 GPU 上下文

## 与其他概念的关系

- [[融合渲染架构]] — Fusion Renderer 路径的对比方案
- [[帧时钟协作机制]] — 帧循环调度共用同一套帧时钟系统
- [[三明治混排结构]] — 自渲染路径的 UI 混排方案

## 来源

- [[src-OHOS SkiaRenderer渲染管线设计]] — 完整文档
