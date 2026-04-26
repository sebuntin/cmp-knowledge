---
type: analysis
created: 2026-04-20
updated: 2026-04-20
tags:
  - DragAndDrop
  - OHOS
  - 跨平台
  - 事件传递
  - Messenger
related:
  - "[[ComposeSceneDragAndDropNode]]"
  - "[[HarmonyOSDragAndDropManager]]"
  - "[[DragAndDropProxy]]"
  - "[[Messenger通信机制]]"
  - "[[融合渲染架构]]"
---

# DragAndDrop 在 OHOS 平台的实现

## 摘要

DragAndDrop（拖拽）功能让用户在屏幕上长按元素拖到另一个位置放下。CMP 项目中，这个功能横跨 Compose Kotlin 层、Skiko 桥接层、Kotlin 平台管理器和 ArkTS 原生层四层，数据通过 Messenger（JSON 消息通道）逐层接力传递。

## 四层架构

```
用户手指操作
    ↕
④ ArkTS 层（DragAndDropProxy.ets）—— 调用 OHOS 原生 dragController API
    ↕ Messenger（JSON 消息通道）
③ Kotlin 层（HarmonyOSDragAndDropManager）—— 管理拖拽状态，生成预览图
    ↕
② 桥接层（ComposeSceneDragAndDropNode）—— 把平台事件分发给 Compose 内部
    ↕
① Compose 层（DragAndDropNode + Modifier）—— 开发者用的 API
```

### 第①层：Compose API 层

开发者通过 Modifier 声明拖拽行为：

- `Modifier.dragAndDropSource` — 声明元素可拖拽（数据源）
- `Modifier.dragAndDropTarget` — 声明区域可接收放置（目标）

这些 Modifier 内部创建 `DragAndDropNode`，组成一棵**拖拽节点树**。系统通过命中测试判断手指在哪个节点上，将事件分发给对应节点。

关键接口：
- `DragAndDropTarget` — 7 个回调（onStarted/onEntered/onMoved/onExited/onChanged/onDrop/onEnded）
- `DragAndDropEvent` — 平台相关的拖拽事件（OHOS 上内部是 JSON 字符串）
- `DragAndDropTransferData` — 传输数据（OHOS 上仅支持 text）

### 第②层：事件分发器（ComposeSceneDragAndDropNode）

**收发室角色**——从平台层收事件，分发到 Compose 节点树。

- 实现 `DragAndDropTarget` 接口
- `ensureStartedOwner()` 管理 `DragAndDropOwner` 的切换（旧的结束、新的开始）
- 所有事件转发给 `currentRootNode`（第①层的节点树根）

### 第③层：Kotlin 平台管理器（HarmonyOSDragAndDropManager）

OHOS 平台的核心管理类，职责：

**拖出去（Drag）：**
1. Compose 手势检测触发 `requestDragAndDropTransfer()`
2. 用 Skia 把拖拽预览图绘制为 `ImageBitmap` → PNG 编码 → Base64 字符串
3. 打包 JSON（文本数据 + 预览图 + 触摸点坐标）
4. 通过 Messenger 发送 `"compose.ui.DragAndDrop:startDrag"` 给 ArkTS

**拖进来（Drop）：**
1. ArkTS 传来 `"compose.ui.DragAndDrop:dropEvent"` 消息
2. 解析 JSON 判断事件类型（enter/move/leave/drop/end）
3. 首次事件时调用 `rootNode.acceptDragAndDropTransfer()` 判断是否接受此拖拽会话
4. 按类型分发事件（onEntered/onMoved/onExited/onDrop/onEnded）
5. move 事件时额外通知 ArkTS 层当前是否有可接收的目标（用于高亮提示）

### 第④层：ArkTS 原生桥接（DragAndDropProxy）

直接调用 OHOS 系统 API 的层。

**拖出去：**
1. 收到 Kotlin 的 startDrag 消息
2. 将文本数据包装为 OHOS `UnifiedData`（支持 text/image/file）
3. 调用 `dragController.createDragAction()` 创建拖拽动作
4. 用 `CustomBuilder` 构建拖拽预览（手指旁边的半透明图）
5. `dragAction.startDrag()` 启动系统拖拽
6. 监听 `statusChange`，结束时通知 Kotlin

**拖进来：**
1. OHOS 系统触发 onDragEnter/onDragMove/onDragLeave/onDrop/onDragEnd
2. 提取坐标（`vp2px` 转为像素）和数据（从 `UnifiedData` 提取 PlainText/Image/File）
3. 打包 JSON 通过 Messenger 发给 Kotlin

## Messenger 通信协议

Kotlin 与 ArkTS 之间通过 Messenger 传递 JSON 字符串：

| 消息类型 | 方向 | 用途 |
|---------|------|------|
| `compose.ui.DragAndDrop:startDrag` | Kotlin → ArkTS | 启动拖拽 |
| `compose.ui.DragAndDrop:cancelDrag` | Kotlin → ArkTS | 取消拖拽 |
| `compose.ui.DragAndDrop:dropEvent` | ArkTS → Kotlin | 拖拽事件 |
| `compose.ui.DragAndDrop:dragResult` | ArkTS → Kotlin | 拖拽结果 |
| `compose.ui.DragAndDrop:updateDropTargetStatus` | Kotlin → ArkTS | 目标状态更新 |

JSON 事件格式示例：
```json
{
  "type": "move",
  "position": { "x": 150.5, "y": 320.0 },
  "data": { "type": "text", "content": "Hello" }
}
```

## 完整数据流图

```
┌─────────────────────────────────────────────────────┐
│                 Compose @Composable                  │
│  dragAndDropSource ─→ DragAndDropNode 树 ←── target │
└──────────────────────┬──────────────────────────────┘
                       │
            ComposeSceneDragAndDropNode
                       │
        HarmonyOSDragAndDropManager
        （预览图 PNG→Base64、JSON 解析）
                       │ Messenger (JSON)
                       │
            DragAndDropProxy (ArkTS)
            （OHOS dragController API）
                       │
            OHOS 系统拖拽服务
                       │
                  用户手指操作
```

## 关键文件索引

| 文件 | 语言 | 职责 |
|------|------|------|
| `ui/src/commonMain/.../DragAndDrop.kt` | Kotlin | 跨平台接口（DragAndDropTarget、DragAndDropEvent expect 声明） |
| `ui/src/commonMain/.../DragAndDropNode.kt` | Kotlin | 拖拽节点树实现 |
| `ui/src/ohosArm64Main/.../DragAndDrop.ohos.kt` | Kotlin | OHOS 的 DragAndDropEvent 实现（JSON 解析） |
| `ui/src/ohosArm64Main/.../PlatformDragAndDropManager.ohos.kt` | Kotlin | HarmonyOSDragAndDropManager 核心管理器 |
| `ui/src/skikoMain/.../ComposeSceneDragAndDropNode.skiko.kt` | Kotlin | 事件分发桥接 |
| `ui-arkui/.../DragAndDropProxy.ets` | ArkTS | 调用 OHOS dragController API |
| `ui-arkui/.../drag_and_drop.h` | C | OHOS NDK 拖拽 API 头文件 |

## 支持的数据类型

- **text** — 纯文本（`PlainText.textContent`）
- **image** — 图片（URI / Base64 data URI / 文件路径）
- **file** — 文件（URI / 文件路径）

## 与已有知识的关系

- [[融合渲染架构]] — DragAndDrop 与渲染管线独立，共享 Messenger 通信通道
- [[Messenger通信机制]] — DragAndDrop 使用 Messenger 的 5 种消息类型
- DragAndDrop 不依赖渲染模式（Fusion Renderer / SkiaRender 均支持）
