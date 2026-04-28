---
type: entity
category: Kotlin 类
created: 2026-04-20
updated: 2026-04-20
tags:
  - DragAndDrop
  - 事件分发
  - Skiko
sources:
  - 代码探索分析
related:
  - "[[HarmonyOSDragAndDropManager]]"
  - "[[DragAndDropProxy]]"
  - "[[analysis-DragAndDrop在OHOS平台的实现]]"
---

# ComposeSceneDragAndDropNode

## 定义

平台拖拽事件进入 Compose 拖拽节点树的**唯一入口**。实现 `DragAndDropTarget` 接口，作为 `PlatformDragAndDropManager` 与 Compose UI 框架之间的桥梁。

## 核心职责

1. **实现 DragAndDropTarget 接口** — 处理 7 个生命周期回调（onStarted/onEntered/onMoved/onExited/onChanged/onDrop/onEnded）
2. **Owner 切换管理** — `ensureStartedOwner()` 在 DragAndDropOwner 变更时正确结束旧会话、开始新会话
3. **所有平台的统一入口** — 各平台（OHOS/Web/Desktop/iOS）的 PlatformDragAndDropManager 通过它接入 Compose 拖拽系统
4. **转发到节点树** — 事件最终由 `currentRootNode` 分发到具体的 @Composable 组件

## 关键成员

| 成员 | 说明 |
|------|------|
| `dragAndDropOwner: () -> DragAndDropOwner` | 当前 DragAndDropOwner 的懒获取 |
| `startedOwner: DragAndDropOwner?` | 已启动会话的 Owner |
| `currentRootNode: DragAndDropNode` | 拖拽节点树根节点 |
| `hasEligibleDropTarget: Boolean` | 是否有可接收放置的子节点 |
| `acceptDragAndDropTransfer(event)` | 判断是否接受拖拽会话 |
| `startDragAndDropTransfer(offset, ...)` | 启动拖拽传递 |

## 设计模式

使用**代理模式**——所有实际拖拽处理委托给 `DragAndDropOwner` 实例。`ensureStartedOwner()` 确保 Owner 切换时状态正确转移。

## 文件位置

`compose_multiplatform_core/compose/ui/ui/src/skikoMain/kotlin/androidx/compose/ui/scene/ComposeSceneDragAndDropNode.skiko.kt`
