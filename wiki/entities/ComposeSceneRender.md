---
type: entity
category: Kotlin 类
created: 2026-04-26
updated: 2026-04-26
sources:
  - raw/OHOS SkiaRenderer渲染管线设计.md
tags:
  - CMP
  - Kotlin
  - SkiaRenderer
  - 渲染
  - GPU
related:
  - "[[SkiaRenderer渲染管线]]"
  - "[[XComponentRender]]"
---

# ComposeSceneRender

## 定义

OHOS 自渲染路径中管理 Skia GPU 渲染管线的核心类，负责 DirectContext、BackendRenderTarget 和 Surface 的创建与绘制。

## 基本信息

| 属性 | 值 |
|------|-----|
| **语言** | Kotlin |
| **位置** | `ui/src/ohosArm64Main/.../scene/ComposeSceneRender.ohos.kt` |

## 核心职责

1. **GPU 上下文管理**：通过 `DirectContext.makeGL()` 创建 OpenGL GPU 上下文
2. **渲染表面管理**：创建 BackendRenderTarget（FBO）+ Skia Surface
3. **绘制调度**：三种绘制模式（常规 / 外部画布 / 录制模式）

## 关键成员

| 成员 | 类型 | 说明 |
|------|------|------|
| `directContext` | `DirectContext?` | GPU 上下文 |
| `renderTarget` | `BackendRenderTarget?` | FBO 渲染目标 |
| `surface` | `Surface?` | Skia 绘制表面 |
| `surfaceCanvas` | `Canvas?` | Compose 画布 |

## 绘制流程

```
draw(timestamp)
  1. ensureSurface() — 惰性创建 GPU 上下文和 Surface
  2. surface.canvas.clear(TRANSPARENT) — 清屏
  3. surface.canvas.resetMatrix() — 重置变换
  4. onDraw(surfaceCanvas, timestamp) — 回调 ComposeScene.render()
  5. directContext.flush() — 刷新 GPU 命令
```

## 与其他实体的关系

- [[XComponentRender]] — 提供 EGL 环境，ComposeSceneRender 在其上创建 Skia Surface
- [[SkiaRenderer渲染管线]] — 是该管线的 Kotlin 渲染层核心

## 来源

- [[src-OHOS SkiaRenderer渲染管线设计]] — 第 4.1 节
