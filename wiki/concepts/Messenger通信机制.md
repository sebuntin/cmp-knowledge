---
type: concept
created: 2026-04-20
updated: 2026-04-20
tags:
  - Messenger
  - 跨平台通信
  - JSON
  - Kotlin-ArkTS桥接
sources:
  - 代码探索分析
related:
  - "[[HarmonyOSDragAndDropManager]]"
  - "[[DragAndDropProxy]]"
  - "[[融合渲染架构]]"
---

# Messenger 通信机制

## 定义

Messenger 是 CMP 项目中 Kotlin 层与 ArkTS 层之间的**双向 JSON 消息通信通道**。两层的代码运行在不同运行时中（Kotlin/Native 和 ArkTS JS 引擎），无法直接调用，因此通过 Messenger 传递 JSON 字符串来协调工作。

## 通信模式

```
Kotlin 层                    ArkTS 层
    │                            │
    ├── messenger.send(type, json) ──→  onReceive(type, handler)
    │                            │
    ├── messenger.onReceive(type, handler) ←── messenger.send(type, json)
    │                            │
```

- **send** — 发送消息，同步等待返回值（同步 RPC 风格）
- **onReceive** — 注册消息监听器，收到消息后处理并返回响应

## 消息命名约定

消息类型采用 **命名空间:操作** 格式：

```
compose.ui.{模块}:{操作}
```

例如 `compose.ui.DragAndDrop:startDrag`。

## 在 DragAndDrop 中的应用

5 种消息类型实现完整的拖拽生命周期：

| 消息 | 方向 | 触发时机 |
|------|------|---------|
| `startDrag` | K → A | Compose 检测到拖拽手势 |
| `cancelDrag` | K → A | 主动取消拖拽 |
| `dropEvent` | A → K | OHOS 系统触发拖拽事件 |
| `dragResult` | A → K | 拖拽结束，通知成功/失败 |
| `updateDropTargetStatus` | K → A | 目标状态变化，更新预览高亮 |

## 与其他子系统的关系

Messenger 不仅用于 DragAndDrop，还承载了整个 CMP 框架中 Kotlin-ArkTS 跨层通信：
- 尺寸变化通知
- 触摸事件传递
- 渲染模式切换
- DragAndDrop 事件

所有跨层通信都通过同一个 Messenger 实例，通过消息类型区分不同子系统。

## 关键要点

- 数据格式统一为 JSON 字符串，双方各自解析
- send 是同步调用（调用方阻塞等待返回值）
- 消息类型是字符串常量，通过命名空间避免冲突
