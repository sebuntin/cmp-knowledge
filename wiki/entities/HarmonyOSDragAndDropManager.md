---
type: entity
category: Kotlin 类
created: 2026-04-20
updated: 2026-04-20
tags:
  - DragAndDrop
  - OHOS
  - 平台管理器
  - Messenger
sources:
  - 代码探索分析
related:
  - "[[ComposeSceneDragAndDropNode]]"
  - "[[DragAndDropProxy]]"
  - "[[Messenger通信机制]]"
---

# HarmonyOSDragAndDropManager

## 定义

OHOS 平台的 `PlatformDragAndDropManager` 实现。管理拖拽状态、生成预览图、通过 Messenger 与 ArkTS 层通信。

## 核心职责

1. **拖拽启动** — `requestDragAndDropTransfer()` 接收 Compose 层手势，生成预览图后通过 Messenger 发给 ArkTS
2. **事件接收** — 注册 Messenger 监听器，接收 ArkTS 传来的拖拽事件（enter/move/leave/drop/end）
3. **预览图生成** — 用 Skia 将 `DrawScope` 绘制结果编码为 PNG → Base64，传给 ArkTS 显示
4. **会话管理** — 跟踪 `activeDragActionId` 和 `currentDropSessionAccepted`，支持取消正在进行的拖拽

## 关键方法

| 方法 | 说明 |
|------|------|
| `requestDragAndDropTransfer(source, offset)` | Compose 手势触发入口 |
| `startDrag(transferData, decorationSize, drawDragDecoration, touchPoint)` | 构造 JSON 并通过 Messenger 发送 startDrag 消息 |
| `handleDropEventMessage(message)` | 处理 ArkTS 传来的拖拽事件 |
| `handleDragResultMessage(message)` | 处理拖拽最终结果 |
| `createDragPreviewImage(...)` | 用 Skia 绘制预览图并编码为 Base64 |
| `cancelActiveDrag()` | 取消当前拖拽操作 |

## 消息类型常量

| 常量 | 值 | 方向 |
|------|------|------|
| `MESSAGE_TYPE_START_DRAG` | `compose.ui.DragAndDrop:startDrag` | → ArkTS |
| `MESSAGE_TYPE_CANCEL_DRAG` | `compose.ui.DragAndDrop:cancelDrag` | → ArkTS |
| `MESSAGE_TYPE_DROP_EVENT` | `compose.ui.DragAndDrop:dropEvent` | ← ArkTS |
| `MESSAGE_TYPE_DRAG_RESULT` | `compose.ui.DragAndDrop:dragResult` | ← ArkTS |
| `MESSAGE_TYPE_UPDATE_DROP_TARGET_STATUS` | `compose.ui.DragAndDrop:updateDropTargetStatus` | → ArkTS |

## 预览图生成流程

```
DrawScope 绘制回调
  → ImageBitmap(w×h, hasAlpha=true)
  → Canvas + CanvasDrawScope 执行绘制
  → asSkiaBitmap() → Image.makeFromBitmap()
  → encodeToData(PNG) → ByteArray
  → encodeBase64() → String
```

## 文件位置

`compose_multiplatform_core/compose/ui/ui/src/ohosArm64Main/kotlin/androidx/compose/ui/platform/PlatformDragAndDropManager.ohos.kt`
