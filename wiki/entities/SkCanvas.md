---
type: entity
category: C++ 类
created: 2026-04-19
updated: 2026-04-20
sources:
  - CMP融合渲染架构设计文档.md
tags:
  - CMP
  - C++
  - OHRender
  - Canvas
  - 绘制
related:
  - "[[融合渲染架构]]"
  - "[[OH_Drawing命令转换]]"
  - "[[SkPicture与脏区管理]]"
  - "[[SkPictureRecorder]]"
---

# SkCanvas

## 定义

SkCanvas 是 Skia 的绘制画布类，在融合渲染中包装了 `OH_Drawing_Canvas`，负责将绘制操作转换为 OH_Drawing 命令，同时跟踪脏区。

## 基本信息

| 属性 | 值 |
|------|-----|
| **语言** | C++ |
| **位置** | `OHRender/OHRender/src/core/SkCanvas.cpp` |
| **头文件** | `OHRender/OHRender/include/core/SkCanvas.h` |

## 核心职责

1. **命令转换**：将 Skia 绘制操作转发给 OH_Drawing_Canvas
2. **脏区跟踪**：每次绘制操作时通过 `markDrawBounds()` 更新 `fDrawBounds`
3. **Paint 转换**：通过 `attachPaint()` / `detachPaint()` 将 SkPaint 转换为 OH_Drawing_Pen

## 关键方法

| 方法 | 说明 |
|------|------|
| `onDrawRect(rect, paint)` | 矩形绘制 → OH_Drawing_CanvasDrawRect + markDrawBounds |
| `onDrawPath(path, paint)` | 路径绘制 → OH_Drawing_CanvasDrawPath + markDrawBounds |
| `markDrawBounds(area, paint)` | 核心脏区更新方法 |
| `getFinishDrawBounds()` | 返回 `fDrawBounds`（最终脏区） |
| `adjustAndMap(area, paint)` | 坐标转换 + Paint 影响 |

## 转换运算符

```cpp
operator OH_Drawing_Canvas*() const {
    initDrawingCanvas();    // 确保 OH_Drawing_Canvas 已初始化
    return fDrawingCanvas;
}
```

注意：转换前会调用 `initDrawingCanvas()` 确保内部画布就绪，不是简单的透明访问。

## 关键成员

| 成员 | 类型 | 说明 |
|------|------|------|
| `fDrawingCanvas` | `OH_Drawing_Canvas*` | 内部包装的 OH_Drawing Canvas |
| `fDrawBounds` | `std::optional<SkRect>` | 当前脏区边界框 |
| `fDrawingNode` | `OHRenderNode*` | 当前关联的 RenderNode |

## 绘制操作通用流程

```
onDrawXxx(params, paint)
  1. attachPaint(paint)     — SkPaint → OH_Drawing_Pen
  2. OH_Drawing_CanvasDrawXxx() — 记录到 RecordCmd
  3. detachPaint()          — 清理 Pen
  4. markDrawBounds(area, paint) — 更新脏区
```

## 与其他实体的关系

- [[SkPictureRecorder]] — 创建 SkCanvas 并使用其录制功能
- [[OHRenderNode]] — SkCanvas 持有 OHRenderNode 引用用于脏区关联
- [[OH_Drawing命令转换]] — SkCanvas 是命令转换的直接执行者

## 来源

- [[src-CMP融合渲染架构设计文档]] — 第一章 1.3 节、第二章、第三章
