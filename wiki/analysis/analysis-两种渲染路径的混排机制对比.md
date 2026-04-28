---
type: analysis
created: 2026-04-27
updated: 2026-04-27
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

FusionRenderer 的 Compose 内容本身就是 ArkUI 组件树的一部分（通过 NodeController / RenderNode 嵌入），原生混排是天然支持的。SkiaRenderer 的 Compose 内容在独立的 XComponent 渲染面上，与 ArkUI 组件树隔离，需要三明治结构 + 挖洞机制才能实现混排。

## 架构理念差异

### FusionRenderer：内嵌式混排

```
ArkUI 组件树
  ├── ArkUI Node A
  ├── NodeContainer (ComposeNodeController)
  │     └── CRenderNode / JsRenderNode
  │           └── ContentModifier ← Compose 绘制内容聚合在这里
  └── ArkUI Node B
```

Compose 的绘制内容通过 RenderNode **直接嵌入** ArkUI 组件树。原生组件和 Compose 内容在同一棵树上，Z 序由 ArkUI 布局系统统一管理。

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

| 能力 | FusionRenderer | SkiaRenderer |
|------|---------------|-------------|
| 原生组件在 Compose 上方 | 天然支持（Z 序控制） | foreRootView 层 |
| 原生组件在 Compose 下方 | 天然支持（Z 序控制） | backRootView 层 + 挖洞 |
| 原生组件被弹窗覆盖 | 天然支持 | 仅 BACK 层支持，FORE 层穿透 |
| 原生组件跟随滚动 | 天然支持 | BACK 层天然，FORE 层不跟随 Z 序 |
| 安全组件 (PasteButton) | 直接使用 | 通过 TextToolbarOverlay + Messenger |
| 挖洞需求 | 无 | BACK 层需要 |
| 混排复杂度 | 低（单层 NodeController） | 高（五层 Stack + 三个 ArkUIRootView） |

## 挖洞机制的必要性

### 为什么 SkiaRenderer 需要挖洞

XComponent 的 Compose 渲染面是不透明的 GPU Surface。BACK 层原生组件在 XComponent 下面，不挖洞就会被完全遮住。

```kotlin
// 挖洞代码：在原生组件位置将 Compose 像素擦除为透明
drawRect(Color.Transparent, blendMode = BlendMode.DstAtop)
```

### 为什么 FusionRenderer 不需要挖洞

FusionRenderer 的 Compose 内容通过 RenderNode 嵌入 ArkUI 树，ArkUI 的布局系统天然处理 Z 序和遮挡关系。原生组件与 Compose 内容在同一渲染管线上，不存在"谁遮住谁"的问题。

## 通信机制对比

| 交互场景 | FusionRenderer | SkiaRenderer |
|---------|---------------|-------------|
| 原生组件事件 → Compose | 直接通过 NodeController 回调 | Messenger JSON 通道 |
| Compose → 原生组件更新 | 直接操作 NodeHandle | 直接操作 NodeHandle |
| 文本工具栏 | Compose 内部处理 | TextToolbarOverlay + Messenger |
| 拖拽事件 | 通过 NodeContainer 事件 | touchableRootView + DragAndDrop 回调 |

SkiaRenderer 路径的部分交互需要通过 Messenger 通道在 Kotlin 和 ArkTS 之间传递，而 FusionRenderer 可以更直接地处理。

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
