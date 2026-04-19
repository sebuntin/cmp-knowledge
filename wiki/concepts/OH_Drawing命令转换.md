---
type: concept
created: 2026-04-19
updated: 2026-04-19
sources:
  - CMP融合渲染架构设计文档.md
tags:
  - CMP
  - 融合渲染
  - OH_Drawing
  - 命令转换
related:
  - "[[融合渲染架构]]"
  - "[[SkCanvas]]"
  - "[[ContentModifier挂载机制]]"
---

# OH_Drawing 命令转换

## 定义

OH_Drawing 命令转换是将 Skia 的 Canvas 绘制操作（drawRect、drawPath 等）转换为 OHOS 原生的 OH_Drawing 命令（OH_Drawing_RecordCmd）的过程，使 Compose UI 能在 OHOS 平台的 RenderService 上执行渲染。

## 详解

### 转换发生在两个阶段

**1. 录制阶段（实时转换）**

每次调用 SkCanvas 绘制方法时，立即转换为 OH_Drawing 命令并记录：

```
SkCanvas.drawRect(rect, paint)
  → convertPaintToPen(paint)        — SkPaint 转 OH_Drawing_Pen
  → OH_Drawing_CanvasDrawRect()     — 记录到 RecordCmd
  → markDrawBounds(rect, paint)     — 同时更新脏区
```

**2. 回放阶段（命令执行）**

通过 `OH_Drawing_CanvasDrawRecordCmdNesting()` 执行命令序列：
- 支持嵌套执行（Nesting），可在命令中执行另一个命令序列
- 保持 Canvas 状态一致性

### 命令映射表

| SkCanvas 操作 | OH_Drawing 命令 | 说明 |
|--------------|----------------|------|
| `drawRect` | `OH_Drawing_CanvasDrawRect` | 绘制矩形 |
| `drawPath` | `OH_Drawing_CanvasDrawPath` | 绘制路径 |
| `drawText` | `OH_Drawing_CanvasDrawText` | 绘制文本 |
| `drawImage` | `OH_Drawing_CanvasDrawImage` | 绘制图片 |
| `clipRect` | `OH_Drawing_CanvasClipRect` | 裁剪矩形 |
| `clipPath` | `OH_Drawing_CanvasClipPath` | 裁剪路径 |
| `save` | `OH_Drawing_CanvasSave` | 保存状态 |
| `restore` | `OH_Drawing_CanvasRestore` | 恢复状态 |
| `translate` | `OH_Drawing_CanvasTranslate` | 平移变换 |
| `concat` | `OH_Drawing_CanvasConcatMatrix` | 矩阵变换 |

### OH_Drawing_RecordCmdUtils 生命周期

```
Create() → BeginRecording() → [绘制操作] → FinishRecording() → Destroy()
                                       ↓
                              获取 OH_Drawing_RecordCmd
```

### SkCanvas 转换运算符

SkCanvas 包装了 `OH_Drawing_Canvas*`，通过转换运算符透明传递：

```cpp
operator OH_Drawing_Canvas*() const {
    return fDrawingCanvas;  // 直接返回内部 OH_Drawing_Canvas
}
```

## 关键要点

- 转换在录制阶段实时发生，非批量后处理
- `OH_Drawing_RecordCmdUtils` 管理 RecordCmd 的完整生命周期
- SkCanvas 通过包装模式透明地将操作转发给 OH_Drawing
- 嵌套执行（Nesting）支持 Picture 的递归回放

## 与其他概念的关系

- [[融合渲染架构]] — 命令转换是数据流的核心环节
- [[SkCanvas]] — 执行命令转换的载体
- [[ContentModifier挂载机制]] — 转换后的命令通过 ContentModifier 聚合
- [[SkPicture与脏区管理]] — 命令转换与脏区计算在录制阶段并行

## 来源

- [[src-CMP融合渲染架构设计文档]] — 第三章：SkPicture 到 OH_Drawing 命令转换机制
