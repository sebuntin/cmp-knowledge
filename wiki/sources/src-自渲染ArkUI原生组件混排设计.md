---
type: source
created: 2026-04-26
updated: 2026-04-26
source_file: raw/自渲染ArkUI原生组件混排设计.md
ingested: 2026-04-26
tags:
  - 自渲染
  - ArkUI
  - 混排
  - 三明治结构
  - NodeContainer
  - XComponent
  - InteropContainer
  - PasteButton
related:
  - "[[融合渲染架构]]"
  - "[[Messenger通信机制]]"
---

# 自渲染路径 ArkUI 原生组件混排设计

## 摘要

本文档描述 OHOS 自渲染路径中 Compose UI 与 ArkUI 原生组件的混合布局方案。核心设计是**三明治结构**：通过 Stack 叠放 5 层 NodeContainer / XComponent，使原生组件可以出现在 Compose 内容的上方或下方，并通过挖洞机制让 BACK 层组件可见。

## 关键发现

- **三明治五层叠放**：backRootView → XComponent → foreRootView → touchableRootView → TextToolbarOverlay
- **三层 InteropContainer**：BACK（默认，Compose 下面 + 挖洞）、FORE（Compose 上面）、TOUCHABLE（最顶层事件拦截）
- **BACK 层挖洞机制**：`drawRect(Color.Transparent, blendMode = BlendMode.DstAtop)` 在原生组件位置擦除 Compose 像素
- **默认 BACK 的设计原因**：让原生组件像 Compose 子组件一样能被覆盖、Z 序由布局决定
- **PasteButton 免权限集成**：利用 OHOS 安全组件机制，用户点击即授权，不需要 manifest 声明权限

## 重要细节

### 三个 ArkUIRootView

每个 ArkUIRootView 是独立的 NodeController，Compose 通过 ctrl.init() 将其传给 Kotlin 层按需添加原生节点。

### 挖洞精确性

透明洞只在组件的精确位置和尺寸范围内，其他区域仍然是 Compose 不透明内容。

### 文本工具栏通信

工具栏显示/隐藏通过 Messenger JSON 通道：Kotlin `messenger.send("compose.ui.TextToolbar:showMenu", ...)` → ArkTS TextToolbar 收到 → @State 更新 → 重新渲染。PasteButton 点击后通过 `messenger.send("compose.ui.TextToolbar:showMenu.onPaste", "")` 回传。

### FORE 层的限制

FORE 层组件永远在最上层，无法被弹窗、菜单、动画覆盖，只用于安全组件等特殊场景。

## 与已有知识的关联

- 补充了 [[融合渲染架构]] 自渲染路径的 UI 混排机制
- 文本工具栏通信复用了 [[Messenger通信机制]] 的 JSON 消息通道
- 与 FusionRenderer 路径的混排方式形成对比（FusionRenderer 直接通过 NodeController 管理）
