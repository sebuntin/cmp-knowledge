---
type: entity
category: C++ 类
created: 2026-04-19
updated: 2026-04-19
sources:
  - CMP融合渲染架构设计文档.md
tags:
  - CMP
  - C++
  - OHRender
  - SkPicture
  - 录制器
related:
  - "[[融合渲染架构]]"
  - "[[SkPicture与脏区管理]]"
  - "[[OHRenderNode]]"
  - "[[SkCanvas]]"
---

# SkPictureRecorder

## 定义

SkPictureRecorder 是 Skia 提供的绘制指令录制器，在融合渲染中负责将 Compose 绘制操作录制为 SkPicture（通过 OH_Drawing_RecordCmd 实现），同时计算脏区。

## 基本信息

| 属性 | 值 |
|------|-----|
| **语言** | C++ |
| **位置** | `OHRender/OHRender/src/core/SkPictureRecorder.cpp` |
| **头文件** | `OHRender/OHRender/include/core/SkPictureRecorder.h` |

## 核心方法

| 方法 | 说明 |
|------|------|
| `beginRecording(SkRect, bbh)` | 开始录制：创建 OH_Drawing_Canvas、OHRenderNode、SkCanvas |
| `finishRecordingAsPicture()` | 完成录制：计算脏区、获取 RecordCmd、创建 SkOHPicture |
| `getRecordingCanvas()` | 获取当前录制的 Canvas |

## 录制流程

```
beginRecording(cullRect)
  1. OH_Drawing_RecordCmdUtilsBeginRecording() → 获取 OH_Drawing_Canvas
  2. OHRenderNode::CreateNormalNode() → 创建关联节点
  3. new SkCanvas(ohCanvas, node) → 创建包装 Canvas
  → 返回 SkCanvas 供绘制使用

[绘制操作 drawRect/drawPath/...]

finishRecordingAsPicture()
  1. getFinishDrawBounds() → 获取最终脏区
  2. setRealFrame(paintArea) → 设置到 RenderNode
  3. OH_Drawing_RecordCmdUtilsFinishRecording() → 获取 RecordCmd
  4. sk_make_sp<SkOHPicture>(...) → 创建 Picture 对象
  → 返回 SkPicture
```

## 关键成员

| 成员 | 说明 |
|------|------|
| `fOHRecorder` | OH_Drawing_RecordCmdUtils 实例 |
| `fRecordCanvas` | 当前录制的 SkCanvas |
| `fNowOHNode` | 当前关联的 OHRenderNode |
| `fCullRect` | 当前裁剪矩形 |
| `fActivelyRecording` | 是否正在录制 |

## 与其他实体的关系

- [[SkCanvas]] — 创建并使用 SkCanvas 进行录制
- [[OHRenderNode]] — 每次录制关联一个 OHRenderNode
- 生成的 SkOHPicture 持有 RecordCmd 和 OHRenderNode 引用

## 来源

- [[src-CMP融合渲染架构设计文档]] — 第一章 1.3 节、第二章
