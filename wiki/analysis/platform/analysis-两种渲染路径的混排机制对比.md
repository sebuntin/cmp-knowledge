---
type: analysis
created: 2026-04-27
updated: 2026-04-30
tags:
  - FusionRenderer
  - SkiaRenderer
  - 混排
  - ArkUI
  - NodeContainer
  - 三明治结构
  - 对比分析
related:
  - "[[三明治混排结构]]"
  - "[[同层渲染]]"
  - "[[SkiaRenderer渲染管线]]"
  - "[[融合渲染架构]]"
  - "[[Messenger通信机制]]"
sources:
  - raw/自渲染ArkUI原生组件混排设计.md
  - raw/ComposeUI与ArkUI混排原理.md
  - raw/融合渲染整体方案总结.md
---

# 两种渲染路径的混排机制对比

## 研究问题

FusionRenderer 和 SkiaRenderer 路径如何实现 Compose UI 与 ArkUI 原生组件的混合布局？两种方案的架构理念有何根本差异？

## 结论

FusionRenderer 路径从 `harmonyApiVersion >= 22` 起通过 **ExternalRenderNode 同层渲染** 将原生组件直接嵌入 Compose 绘制管线，实现真正的像素级混合。旧设备回退到叠层方式。SkiaRenderer 的 Compose 内容在独立的 XComponent 渲染面上，与 ArkUI 组件树隔离，始终使用三明治结构 + 挖洞机制。

## 架构理念差异

### FusionRenderer：同层渲染（ExternalRenderNode）

```
Compose 绘制遍历
  ├── Compose UI 内容
  ├── DrawModifier.onDraw()
  │     └── drawRenderNode(ExternalRenderNode, rect)
  │           └── 原生 ArkUI 组件像素 → 合成到 Compose Canvas
  └── Compose UI 内容

ArkUI 组件树
  ├── NodeContainer (ComposeNodeController)
  │     └── CRenderNode / JsRenderNode
  │           └── ContentModifier ← Compose 绘制内容
  │           └── ExternalRenderNode ← 原生组件挂载点
```

FusionRenderer 路径通过 `ExternalRenderNode` 将原生组件的渲染结果注入 Compose 的 `DrawModifier` 绘制遍历。`InteropViewPainter.onDraw()` 调用 `canvas.nativeCanvas.drawRenderNode(externalRenderNode, rect)`，原生组件的像素直接合成到 Compose Canvas 上。

**策略路由**：`FusionInteropViewStrategy.useStacked()` 决定使用同层还是叠层：
- `harmonyApiVersion >= 22`：使用 ExternalRenderNode 同层渲染
- `harmonyApiVersion < 22`（且 `enableCApi`）：回退到叠层方式
- ArkTS RenderNode（`!enableCApi`）：使用 ExternalRenderNode 同层渲染

**旧设备回退（叠层）**：API 版本低于 22 的 CAPI 设备仍使用叠层方式，与 SkiaRenderer 类似但架构更简单（单层 NodeController）。

### SkiaRenderer：叠层式混排

```
Stack {
  NodeContainer(backRootView)     ← 原生组件 (Compose 下面)
  XComponent(TEXTURE)             ← Compose 渲染面 (独立 GPU Surface)
  NodeContainer(foreRootView)     ← 原生组件 (Compose 上面)
  NodeContainer(touchableRootView) ← 事件拦截层
  TextToolbarOverlay              ← 文本工具栏
}
```

Compose 的绘制内容在 XComponent 的独立 Surface 上，与 ArkUI 组件树**物理隔离**。原生组件通过多层 NodeContainer 叠放在 XComponent 的上方或下方。

## 混排能力对比

| 能力 | FusionRenderer（同层渲染） | FusionRenderer（旧设备叠层） | SkiaRenderer |
|------|--------------------------|--------------------------|-------------|
| 渲染方式 | ExternalRenderNode 像素合成 | 叠层 | 三明治叠层 |
| 原生组件在 Compose 上方 | 支持（Compose Z 序） | 支持（Z 序控制） | foreRootView 层 |
| 原生组件在 Compose 下方 | 支持（Compose Z 序） | 支持（Z 序控制） | backRootView 层 + 挖洞 |
| 原生组件被弹窗覆盖 | 支持 | 支持 | 仅 BACK 层支持 |
| 原生组件跟随滚动 | 支持（DrawModifier 布局联动） | 支持 | BACK 层天然 |
| 挖洞需求 | 无 | 无 | BACK 层需要 |
| 触摸事件处理 | `mapPointFromGlobal()` 坐标映射 | NodeController 回调 | Messenger JSON |
| 安全组件 (PasteButton) | 直接使用 | 直接使用 | TextToolbarOverlay + Messenger |
| 混排复杂度 | 低（DrawModifier + Painter） | 低（单层 NodeController） | 高（五层 Stack + 挖洞） |

## 挖洞机制的必要性

### 为什么 SkiaRenderer 需要挖洞

XComponent 的 Compose 渲染面是不透明的 GPU Surface。BACK 层原生组件在 XComponent 下面，不挖洞就会被完全遮住。

```kotlin
// 挖洞代码：在原生组件位置将 Compose 像素擦除为透明
drawRect(Color.Transparent, blendMode = BlendMode.DstAtop)
```

### 为什么 FusionRenderer 不需要挖洞

FusionRenderer 通过 ExternalRenderNode 同层渲染，原生组件的像素直接合成到 Compose Canvas 上。Compose 和原生内容共享同一绘制表面，Z 序由 Compose 布局决定，不存在独立的渲染面遮挡问题。

旧设备叠层模式下，Compose 和原生内容都在同一个 ArkUI 组件树上（通过 NodeController），ArkUI 布局系统统一管理 Z 序，同样不需要挖洞。

## 通信机制对比

| 交互场景 | FusionRenderer（同层渲染） | SkiaRenderer |
|---------|--------------------------|-------------|
| 原生组件事件 → Compose | `mapPointFromGlobal()` + `pointerInteropFilterRenderNode()` | Messenger JSON 通道 |
| Compose → 原生组件更新 | 直接操作 ExternalRenderNode | 直接操作 NodeHandle |
| 文本工具栏 | Compose 内部处理 | TextToolbarOverlay + Messenger |
| 拖拽事件 | 通过 NodeContainer 事件 | touchableRootView + DragAndDrop 回调 |

同层渲染的触摸事件通过 `ExternalRenderNode.mapPointFromGlobal(x, y)` 进行坐标映射，将 Compose 触摸坐标转换为原生组件坐标系。这比 SkiaRenderer 的 Messenger JSON 通道更直接、更低延迟。

## 选择建议

| 场景 | 推荐路径 | 原因 |
|------|---------|------|
| 大量原生组件混排 | FusionRenderer | 天然混排，无挖洞开销 |
| 纯 Compose 内容 | 两者均可 | 无混排需求时差异不大 |
| 需要安全组件 | 两者均可 | FusionRenderer 直接用，SkiaRenderer 通过 Overlay |
| 需要完全 GPU 控制 | SkiaRenderer | 独立 GPU 上下文 |

## 来源

- [[src-自渲染ArkUI原生组件混排设计]] — 三明治结构详解
- [[src-ComposeUI与ArkUI混排原理]] — FusionRenderer 混排机制
- [[src-融合渲染整体方案总结]] — 两种路径概览
