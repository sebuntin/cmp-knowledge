---
type: concept
created: 2026-04-28
updated: 2026-04-28
sources:
  - raw/深入理解 Jetpack Compose LayoutModifier.md
tags:
  - LayoutModifier
  - NodeChain
  - NodeCoordinator
  - Constraints
  - 测量布局
related:
  - "[[DrawModifier机制]]"
  - "[[布局流程]]"
---

# LayoutModifier机制

## 定义

LayoutModifier 通过 LayoutModifierNode 和 NodeChain 双向链表实现分层测量。约束从外向内传播（Modifier 从左到右），尺寸从内向外回传（从右到左）。

## 详解

### NodeChain 结构

```
Modifier.size(100).padding(16).background(Red)

LayoutNode
  │
  outerCoordinator (LayoutModifierNodeCoordinator for size)
    │ 约束: 100x100
    ▼
  coordinator (LayoutModifierNodeCoordinator for padding)
    │ 约束: (100-32)x(100-32) = 68x68
    ▼
  innerCoordinator (InnerNodeCoordinator)
    │ 实际内容测量
    ▼
  被修饰的 Composable 内容
```

### 约束传播方向

```
约束 →→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→ 从外向内
 outerCoord      coord       innerCoord    实际内容
 ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←← 尺寸回传
```

### Draw 修饰符共享 Coordinator

```kotlin
Modifier.size(100)     // LayoutModifierNode → LayoutModifierNodeCoordinator
  .background(Red)     // DrawModifierNode → 共享上面的 Coordinator！
  .padding(16)         // LayoutModifierNode → 新的 LayoutModifierNodeCoordinator
```

background 的绘制区域由 size 的约束决定，不是自己的。

### Modifier 顺序至关重要

```kotlin
Modifier.size(100).size(200)  // 结果 100dp（左侧先约束）
Modifier.size(200).size(100)  // 结果 200dp（左侧先约束）
```

### required 变体

`requiredSize()`、`requiredWidth()` 忽略父约束，但视觉边界仍被父分配裁剪。

## 关键要点

- NodeChain 将 Modifier 链扁平化为 NodeCoordinator 双向链表
- 约束从外向内传播，尺寸从内向外回传
- Draw 修饰符共享右侧最近 Layout 修饰符的 Coordinator
- Modifier 顺序直接影响最终测量结果
- required 变体绕过约束但视觉边界仍受限

## 与其他概念的关系

- [[DrawModifier机制]] — Draw 修饰符共享 Layout 修饰符的 Coordinator
- [[布局流程]] — LayoutModifier 是布局阶段约束传播的具体实现
- [[融合渲染架构]] — CMP 中 NodeChain 架构完全相同

## 来源

- [[src-深入理解LayoutModifier]] — 完整文档
