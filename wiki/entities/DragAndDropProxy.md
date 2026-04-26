---
type: entity
category: ArkTS 类
created: 2026-04-20
updated: 2026-04-20
tags:
  - DragAndDrop
  - ArkTS
  - OHOS
  - dragController
sources:
  - 代码探索分析
related:
  - "[[HarmonyOSDragAndDropManager]]"
  - "[[ComposeSceneDragAndDropNode]]"
  - "[[Messenger通信机制]]"
---

# DragAndDropProxy

## 定义

ArkTS 层的拖拽代理类，直接调用 OHOS `dragController` API。作为 Kotlin 层与 OHOS 系统拖拽服务之间的桥梁。

## 核心职责

1. **接收 Kotlin 层拖拽请求** — 通过 Messenger 监听 startDrag/cancelDrag 消息
2. **调用 OHOS 原生 API** — `dragController.createDragAction()` + `startDrag()`
3. **处理系统拖拽回调** — onDragEnter/onDragMove/onDragLeave/onDrop/onDragEnd
4. **数据格式转换** — Kotlin JSON → OHOS `UnifiedData`（text/image/file）
5. **拖拽预览管理** — CustomBuilder 构建预览图，DragPreview 动态更新背景色

## 关键方法

| 方法 | 说明 |
|------|------|
| `startDrag(message)` | 解析 JSON，创建 UnifiedData + DragAction，启动系统拖拽 |
| `cancelDrag(message)` | 取消指定 dragActionId 的拖拽 |
| `handleDropEvent(event, eventType)` | 处理系统拖拽事件，提取坐标和数据，通过 Messenger 通知 Kotlin |
| `handleDragEnter/Leave/Move/End(event)` | 各事件类型快捷入口 |
| `extractDragData(event)` | 从 UnifiedData 提取 PlainText/Image/File |
| `createUnifiedData(dataConfig)` | 将 DragDataConfig 转为 UnifiedData |
| `updateDropTargetStatus(message)` | 根据目标状态动态更新 DragPreview 背景色 |

## 支持的数据类型

| 类型 | OHOS 类 | 说明 |
|------|---------|------|
| text | `PlainText` | 纯文本 |
| image | `Image` | 图片 URI / Base64 data URI / 文件路径 |
| file | `File` | 文件 URI / 文件路径 |

## 拖拽预览机制

1. Kotlin 层传入 Base64 编码的 PNG 预览图
2. 通过 `dragPreviewBuilder` 回调在组件上下文中创建 Image 组件显示
3. 拖拽过程中通过 `DragPreview.setForegroundColor()` 动态更新背景色：
   - 有可接收目标时：半透明绿色 `#3300CC00`
   - 无可接收目标时：透明 `Color.Transparent`
4. 颜色变化带 100ms 平滑动画

## 文件位置

`compose_multiplatform_core/compose/ui/ui-arkui/src/ohosArm64Main/cpp/compose/src/main/ets/compose/draganddrop/DragAndDropProxy.ets`
