---
type: concept
created: 2026-04-28
updated: 2026-04-28
sources:
  - raw/深入理解 Jetpack Compose DrawModifier.md
tags:
  - DrawModifier
  - DrawModifierNode
  - drawContent
  - 绘制管线
related:
  - "[[LayoutModifier机制]]"
  - "[[布局流程]]"
  - "[[融合渲染架构]]"
---

# DrawModifier机制

## 定义

DrawModifier 通过 DrawModifierNode 接口和 NodeCoordinator 链实现绘制遍历。所有绘制（包括元素自身内容）都通过 DrawModifierNode.draw() 执行，drawContent() 是链式调用的关键纽带。

## 详解

### 三个绘制修饰符

| API | 绘制位置 | 典型场景 |
|-----|---------|---------|
| `drawBehind` | 内容后面 | 背景、水印 |
| `drawWithContent` | 完全控制前后顺序 | 裁剪、遮罩、调试叠加 |
| `drawWithCache` | 缓存对象跨帧复用 | Brush、Path 缓存 |

### 绘制遍历流程

```
LayoutNode.draw(canvas)
  → outerCoordinator.draw(canvas)
    → drawContainedDrawModifiers(canvas)
      → head(Nodes.Draw) 找到第一个 DrawModifierNode
      → node.draw()              // 执行自定义绘制
        → drawContent()          // 🔗 链接到下一个
          → 下一个 DrawModifierNode.draw()
            → ... 最终到达元素内容绘制
```

### drawContent() 的关键作用

```kotlin
Modifier.drawWithContent {
    drawRect(Color.Red)     // 在内容前绘制
    drawContent()           // 🔗 必须调用！否则后续内容和元素本身都不绘制
    drawRect(Color.Blue)   // 在内容后绘制
}
```

忘记调用 drawContent() → 元素内容消失。

### 全部内容通过修饰符绘制

没有独立的"元素内容绘制"路径。Text 的文本渲染也在某个 DrawModifierNode.draw() 内完成。整个绘制管线是修饰符驱动的。

## 关键要点

- DrawModifierNode 是所有绘制操作的统一接口
- drawContent() 是链式调用的纽带，不调用则链断裂
- 元素自身内容也通过 DrawModifierNode 绘制，无独立路径
- kindSet 位掩码支持高效查找 Draw 类型节点

## 与其他概念的关系

- [[LayoutModifier机制]] — 同属 Modifier.Node 体系，共享 NodeCoordinator
- [[布局流程]] — 绘制是布局之后的第三阶段
- [[融合渲染架构]] — CMP 中 DrawModifierNode 链的遍历最终到达 C++ SkCanvas

## 来源

- [[src-深入理解DrawModifier]] — 完整文档
