---
type: source
source_file: raw/Canvas生命周期详解.md
ingested: 2026-04-19
tags:
  - CMP
  - Canvas
  - 生命周期
  - 融合渲染
  - SkCanvas
  - OH_Drawing_Canvas
  - 录制回放
  - JNI桥接
---

# Canvas 生命周期详解（源文档摘要）

## 摘要

本文档详细描述了 CMP 融合渲染架构中 Canvas 在三个层次（C++ 录制层、Kotlin 层、OHOS 系统回放层）的完整生命周期，涵盖从创建、跨层传递、录制使用到系统回放四个阶段。核心要点是 Canvas 经历"录制 -> JNI 桥接 -> Compose 绘制 -> 系统回放"的完整流程，其中录制阶段的 SkCanvas 包装 OH_Drawing_Canvas，回放阶段由 OHOS RenderService 提供系统 Canvas 执行录制命令。

## 关键发现

- **三层 Canvas 类型**：C++ 层 SkCanvas（包装 OH_Drawing_Canvas）用于录制、Kotlin 层 `org.jetbrains.skia.Canvas` 通过 JNI 包装供上层使用、系统回放层 OH_Drawing_Canvas 由 RenderService 在 ContentModifier 回调中提供
- **录制 Canvas 由 RecordCmdUtils 管理生命周期**：SkCanvas 构造函数中 `fIsRecordCanvas=true` 时，OH_Drawing_Canvas 的销毁由 `OH_Drawing_RecordCmdUtils` 负责，而非 SkCanvas 析构函数；非录制 Canvas 才在析构时调用 `OH_Drawing_CanvasDestroy`
- **根节点重绘五步流程**：`doRedraw()` 依次执行 (1) 确保 SkPictureRecorder 存在 (2) 获取节点尺寸 (3) beginRecording 创建 SkCanvas (4) 调用回调将 Canvas 传递给 Kotlin 层 (5) finishRecordingAsPicture 生成 Picture
- **三种 Canvas 创建场景**：录制阶段由 `SkPictureRecorder::beginRecording()` 创建、嵌套录制由 `RenderNodeLayer.pictureRecorder` 创建、系统回放由 `OH_ArkUI_DrawContext_GetCanvas()` 从 DrawContext 获取
- **Native->Kotlin 回调桥接机制**：通过 `staticCFunction` 注册 `NodeDrawCallback`，C++ 将 `sk_canvas` 指针传递给 Kotlin，Kotlin 用 `Canvas(canvas)` 包装后传递给 ComposeScene 渲染
- **RenderNodeImplC 的 ContentModifier 注册时机**：在构造函数中即创建 ContentModifier 并注册 onDraw 回调，系统回调时通过 `OH_Drawing_CanvasDrawRecordCmdNesting` 回放录制命令

## 重要细节

### Canvas 类型总览

| 层次 | Canvas 类型 | 创建者 | 生命周期 | 用途 |
|------|-------------|--------|----------|------|
| C++ 录制层 | SkCanvas (包装 OH_Drawing_Canvas) | SkPictureRecorder | 录制期间 | 录制绘制命令 |
| Kotlin 层 | org.jetbrains.skia.Canvas | JNI 包装 | 由 C++ 层管理 | 上层 API 调用 |
| 系统回放层 | OH_Drawing_Canvas | OHOS RenderService | 回调期间 | 执行绘制命令 |

### Canvas 创建与销毁对照

| 场景 | 创建方法 | 管理者 | 销毁时机 |
|------|----------|--------|----------|
| 录制阶段 | `SkPictureRecorder::beginRecording()` -> `new SkCanvas(ohCanvas, node)` | SkPictureRecorder | `finishRecordingAsPicture()` 后 |
| 嵌套录制 | `RenderNodeLayer.pictureRecorder.beginRecording()` | RenderNodeLayer | `finishRecordingAsPicture()` 后 |
| 系统回放 | `OH_ArkUI_DrawContext_GetCanvas(context)` | OHOS System | 回调结束后 |

### 核心代码位置

| 功能 | 文件路径 | 关键方法 |
|------|----------|----------|
| Canvas 创建 | SkPictureRecorder.cpp | `beginRecording()` |
| Canvas 构造 | SkCanvas.cpp | `SkCanvas(OH_Drawing_Canvas*, OHRenderNode*)` |
| Kotlin 回调 | ArkUIViewController.kt | `NodeDrawCallback` |
| 系统回放 | RenderNodeImplC.cpp | `nodeDraw()` |
| 根节点触发 | OHRenderNode.cpp | `doRedraw()` |

### Canvas 传递的完整调用链

```
scene.render(canvas)
 -> RootNodeOwner.draw(canvas)
  -> LayoutNode.draw(canvas)
   -> NodeCoordinator.draw(canvas)
    -> layer.drawLayer(canvas)    // 到达 RenderNodeLayer
```

在 RenderNodeLayer 内部完成嵌套的 `pictureRecorder.beginRecording()` -> `performDrawLayer(pictureCanvas)` -> `finishRecordingAsPicture()` -> `canvas.drawPicture(picture)` 流程。

### 回调类型

- `NodeDrawCallback`：`void (*)(void *context, void *canvas)` - JsRenderNode 回调
- `NodeDrawCallbackC`：`void (*)(int32_t id, void* canvas)` - CRenderNode 回调，通过 id 索引 Controller

## 与已有知识的关联

- [[SkCanvas]] - 本文档详细补充了 SkCanvas 的构造参数语义（`fIsRecordCanvas` 标志对析构行为的影响）和三阶段生命周期
- [[SkPictureRecorder]] - 本文档展示了 `beginRecording()` 创建 Canvas 的完整过程和与 OHRenderNode 的关联逻辑
- [[OHRenderNode]] - 本文档补充了 `doRedraw()` 中根节点如何驱动录制和回调流程
- [[ContentModifier挂载机制]] - 本文档详细展示了 `RenderNodeImplC` 构造时注册 ContentModifier onDraw 回调的代码，以及系统回放时 `OH_Drawing_CanvasDrawRecordCmdNesting` 的执行路径
- [[融合渲染架构]] - Canvas 生命周期是融合渲染整体数据流的核心环节
- [[RenderNode生命周期]] - Canvas 生命周期与 RenderNode 生命周期紧密交织，`beginRecording()` 中创建或复用 OHRenderNode
- [[OH_Drawing命令转换]] - 系统回放阶段最终通过 OH_Drawing API 执行录制的命令

## 来源

- 源文档：`raw/Canvas生命周期详解.md`
- 相关架构文档：[[src-CMP融合渲染架构设计文档]]
