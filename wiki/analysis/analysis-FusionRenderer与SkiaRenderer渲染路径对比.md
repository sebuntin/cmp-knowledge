---
type: analysis
created: 2026-04-27
updated: 2026-04-27
tags:
  - FusionRenderer
  - SkiaRenderer
  - 渲染路径
  - 策略模式
  - 对比分析
related:
  - "[[融合渲染架构]]"
  - "[[SkiaRenderer渲染管线]]"
  - "[[帧时钟协作机制]]"
  - "[[三明治混排结构]]"
  - "[[RenderNode生命周期]]"
sources:
  - raw/OHOS SkiaRenderer渲染管线设计.md
  - raw/融合渲染整体方案总结.md
  - raw/渲染模式隔离架构设计文档.md
---

# FusionRenderer 与 SkiaRenderer 渲染路径对比

## 研究问题

CMP 为什么需要两条独立的渲染路径？它们在架构、帧循环、Surface 管理上有哪些根本差异？

## 结论

两条路径源于 OHOS 平台提供的两种不同的渲染接入方式。FusionRenderer 利用系统 RenderService 的硬件加速管线，SkiaRenderer 通过 XComponent 获得独立 GPU 上下文自渲染。共享同一套帧时钟调度系统，但 Surface 来源、帧驱动、绘制后处理完全不同。

## 对比矩阵

### 架构层

| 维度 | FusionRenderer | SkiaRenderer |
|------|---------------|-------------|
| 渲染后端 | OHOS RenderService (RenderNode) | XComponent + EGL + OpenGL ES |
| Canvas 来源 | RenderNode draw 回调提供 | Skia Surface (makeFromBackendRenderTarget) |
| GPU 上下文 | 系统管理 | ComposeSceneRender 自管理 DirectContext |
| C++ 层核心 | OHRenderNode (RenderNode 树) | XComponentRender (EGL 上下文) |
| Kotlin 渲染核心 | RenderNodeLayer (Picture 录制/缓存) | ComposeSceneRender (GPU 管线) |

### 帧循环

| 维度 | FusionRenderer | SkiaRenderer |
|------|---------------|-------------|
| 帧驱动 | postFrameCallback + willDraw 事件 | XComponent VSync 回调 (OnFrameCallbackCB) |
| 帧入口 | ChoreographerManager.onVsync | BasicArkUIViewController.onFrame |
| 绘制后 | 无需 flush (系统自动合成) | EglFinishDraw (eglSwapBuffers) |
| 后台心跳 | 不需要 | 需要 (XComponent VSync 维持) |
| 空闲帧脉冲 | sendFrameWithoutDraw / runBackgroundEffectsTick | 同左 (共用 BaseComposeScene) |

### Surface 与尺寸

| 维度 | FusionRenderer | SkiaRenderer |
|------|---------------|-------------|
| Surface 创建 | ContentModifier 挂载到 RenderNode | eglCreateWindowSurface |
| 尺寸感知 | onAreaChange 直接传递 | ComposeSizeProxy 迂回 (Messenger 通道) |
| Surface 销毁 | RenderNode 随组件树销毁 | onSurfaceDestroyed 显式清理 EGL 资源 |
| Content 绑定 | 延迟到首次 onSurfaceChanged | mediator 创建时立即 setContent |

### 策略接口差异

| 策略 | FusionRenderer 特点 | SkiaRenderer 特点 |
|------|-------------------|------------------|
| SurfaceLifecycleHandler | 延迟创建 mediator | 立即创建 mediator |
| FrameDispatcher | shouldRunBackgroundHeartbeat=false | shouldRunBackgroundHeartbeat=true |
| FrameDispatcher | requiresPostDrawFlush=false | requiresPostDrawFlush=true |
| DrawPipeline | 使用 RenderNode 回调的 Canvas | 忽略传入 Canvas，自管理 GPU |
| ContentBindingStrategy | onFirstSurfaceChanged 时 setContent | onMediatorCreated 时立即 setContent |
| InputStrategy | 直接分发 | 检查 isEglReady() 后分发 |

## 共性：帧时钟系统

两条路径共用同一套帧时钟调度系统（BaseComposeScene 的 render() 六阶段），这是通过策略模式实现的：

- 策略接口负责帧循环的"外壳"（何时触发、绘制前后处理）
- BaseComposeScene.render() 负责帧循环的"内核"（flush → sendFrame → measure → layout → draw）
- 两种路径的 Compose 内容感知不到渲染后端的差异

## 设计权衡

| 选择 FusionRenderer | 选择 SkiaRenderer |
|--------------------|--------------------|
| 利用系统硬件加速管线 | 完全控制 GPU 渲染 |
| 无需 EGL/GL 依赖 | 需要 EGL + OpenGL ES |
| 无后台心跳开销 | 需要维持 VSync 心跳 |
| 尺寸通知直接路径 | 尺寸通知迂回路径 |
| 渲染命令通过 OH_Drawing API | 渲染命令通过 Skia GPU |
| Picture/Node 双模式 | 单一 GPU 渲染模式 |

## 来源

- [[src-OHOS SkiaRenderer渲染管线设计]] — 自渲染路径架构
- [[src-融合渲染整体方案总结]] — 融合渲染路径架构
- [[src-渲染模式隔离架构设计文档]] — 策略模式隔离设计
- [[src-CMP帧时钟协作机制]] — 共用帧时钟系统
