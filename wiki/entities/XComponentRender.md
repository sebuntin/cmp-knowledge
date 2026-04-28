---
type: entity
category: C++ 类
created: 2026-04-26
updated: 2026-04-26
sources:
  - raw/OHOS SkiaRenderer渲染管线设计.md
tags:
  - CMP
  - C++
  - SkiaRenderer
  - EGL
  - XComponent
related:
  - "[[SkiaRenderer渲染管线]]"
  - "[[ComposeSceneRender]]"
---

# XComponentRender

## 定义

C++ 层 EGL 渲染上下文管理类，与 OHOS 的 OH_NativeXComponent 交互，负责 EGL 表面创建、帧回调注册和绘制生命周期管理。

## 基本信息

| 属性 | 值 |
|------|-----|
| **语言** | C++ |
| **位置** | `ui-arkui/.../cpp/compose/xcomponent_render.h/.cpp` |

## 核心职责

1. **EGL 环境初始化**：创建 EGL Surface 和 Context
2. **绘制准备/完成**：eglMakeCurrent / eglSwapBuffers
3. **VSync 帧回调**：注册 OH_NativeXComponent 帧回调

## 关键成员

| 成员 | 类型 | 说明 |
|------|------|------|
| `component` | `OH_NativeXComponent*` | OHOS 原生 XComponent |
| `controller` | `ArkUIViewController*` | Kotlin 层控制器 |
| `eglWindow` | `EGLNativeWindowType` | 原生窗口 |
| `eglSurface` | `EGLSurface` | 每实例独立 |
| `eglContext` | `EGLContext` | 每实例独立 |
| `eglDisplay` | `EGLDisplay` | 进程共享（static） |
| `eglConfig` | `EGLConfig` | 进程共享（static） |

## 关键方法

| 方法 | EGL 调用 |
|------|---------|
| `EglInit(window)` | eglCreateWindowSurface + eglCreateContext |
| `EglPrepareDraw()` | eglMakeCurrent |
| `EglFinishDraw()` | eglSwapBuffers |
| `RegisterFrameCallback()` | OH_NativeXComponent_RegisterOnFrameCallback |

## 与其他实体的关系

- [[ComposeSceneRender]] — XComponentRender 提供 EGL 环境，ComposeSceneRender 在其上运行 Skia 渲染
- [[SkiaRenderer渲染管线]] — 是该管线的 C++ 基础层

## 来源

- [[src-OHOS SkiaRenderer渲染管线设计]] — 第 4.2 节
