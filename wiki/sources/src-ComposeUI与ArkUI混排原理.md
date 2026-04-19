---
type: source
source_file: raw/ComposeUI与ArkUI混排原理.md
ingested: 2026-04-19
tags:
  - CMP
  - 混排
  - ArkUI
  - ComposeUI
---

# src-ComposeUI与ArkUI混排原理

## 摘要

本文档解析 Compose UI 与 ArkUI 原生视图的混排机制，以 `InternalArkUIViewV2` 为核心，阐述 Kotlin 层如何通过 `EmbeddedInteropForArkUINode` 桥接 ArkUI 组件的测量、布局、绘制与生命周期管理，以及 C++ 层 `InteropWrapView` 如何创建 mixed node 并处理指针事件转发，实现两种 UI 框架在同一渲染树中的深度集成。

## 关键发现

1. **InteropBridge 双层架构**：Kotlin 层 `EmbeddedInteropForArkUINode` 管理 ArkUI 视图生命周期与属性同步，C++ 层 `InteropWrapView` 负责 native mixed node 的创建、attach/detach 与绘制桥接
2. **测量回流机制**：ArkUI 组件通过 `onMeasured` 回调检测自身尺寸变化，递增 `layoutKey` 触发 Compose 重测，保证两侧布局一致
3. **坐标系统双向同步**：`Modifier.onGloballyPositioned` 计算 ArkUI 视图在 Compose Root 中的 `Offset`，`pointerInteropFilterV2` 将 Compose 触摸事件按偏移量转发到 ArkUI，ArkTS 侧再做 `offsetTouchEventLocalPosition` 反向校正
4. **延迟销毁策略**：`OHRenderNodeManager` 维护 `m_interopWrapViews` 和 `m_pendingDestroyViews`，当 PictureRecorder 仍持有 render node 时延后销毁，避免绘制中途资源释放
5. **绘制层嵌入**：`AdaptiveCanvas.drawInteropLayer` 将 ArkUI 的 `BaseRenderNode` 绘制到 Compose Canvas，并通过 `markRecordedInPicture` 标记与 PictureRecorder 的引用关系

## 重要细节

### 混排数据流

```
@Composable ArkUIView(name, parameter, modifier)
  → InternalArkUIViewV2
    → EmbeddedInteropForArkUINode (Kotlin) — 管理 wrappingView/baseView 生命周期
    → Place + MeasurePolicy — Constraints 转换为 ArkUI 尺寸
    → Modifier.onGloballyPositioned — 全局坐标偏移计算
    → pointerInteropFilterV2 — Compose → ArkUI 触摸事件转发
    → drawLayer → AdaptiveCanvas.drawInteropLayer — RenderNode 绘制嵌入
      → (JNI) InteropWrapView (C++) — mixed node 创建与管理
        → OHRenderNodeManager — 注册/销毁/延迟释放
```

### 关键类与职责

| 类/文件 | 语言 | 职责 |
|---------|------|------|
| `InternalArkUIViewV2` | Kotlin | 混排核心入口，整合测量/布局/绘制/事件/生命周期 |
| `EmbeddedInteropForArkUINode` | Kotlin | 封装 ArkUI View、RenderNode、LayoutNode 桥接逻辑 |
| `InteropWrapView` | C++ | ArkUI mixed node 创建、attach/detach、背景色/布局同步 |
| `oh_interop_touch_event_handler` | C++ | Compose → ArkUI 指针事件分发，支持多节点转发与坐标校准 |
| `OHRenderNodeManager` | C++ | mixed node 注册、销毁管理、env 获取 |
| `OHNativeCanvasProxy` | C++ | `drawInteropLayer` 实现，将 BaseRenderNode 绘制到 Compose Canvas |

### C++ 层文件结构

| 文件 | 路径 |
|------|------|
| `oh_native_interop_wrap_node.{h,cpp}` | `compose/interop/` |
| `oh_interop_touch_event_handler.{h,cpp}` | `compose/interop/` |
| `oh_native_canvas_export.{h,cpp}` | FFI 接口暴露 |

### 指针事件链路

```
pointerInteropFilterV2(container, offset)
  → ArkUIViewContainer.dispatchTouchEventV2 (Kotlin)
    → oh_interop_touch_event_handler (C++) — 按 offset 分发到目标 InteropWrapView
      → ArkUIView.ets onTouchEventV2(e, x, y)
        → offsetTouchEventLocalPosition(event, {x: -x, y: -y}) — 坐标校正
          → postTouchEvent 到 ArkUI builder
```

## 与已有知识的关联

- [[融合渲染架构]] — 混排是融合渲染架构的扩展场景，将 ArkUI 原生组件作为 interop layer 嵌入 Compose 渲染管线
- [[ContentModifier挂载机制]] — `InteropWrapView` 的 BaseRenderNode 通过 `drawInteropLayer` 绘制到 Compose Canvas 时，需与 PictureRecorder 生命周期协同（`markRecordedInPicture`）
- [[OHRenderNode]] — `OHRenderNodeManager` 管理 interop 场景下的 mixed node 注册与延迟销毁，复用同一套 RenderNode 管理框架
- [[SkCanvas]] — `AdaptiveCanvas.drawInteropLayer` 在 Compose Canvas 上绘制 ArkUI RenderNode，属于 SkCanvas 绘制能力扩展

## 来源

- 原文：`raw/ComposeUI与ArkUI混排原理.md`
- Kotlin 层源码：`androidx/compose/ui/interop/ArkUIView.ohos.kt`
- C++ 层源码：`compose/ui/ui-arkui/.../compose/interop/*.cpp`
- Demo 示例：`composeApp/src/ohosArm64Main/kotlin/com/tencent/compose/sample/video/VideoPlayer.kt`
