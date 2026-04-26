---
type: concept
created: 2026-04-20
updated: 2026-04-20
tags:
  - SubcomposeLayout
  - LazyColumn
  - 懒组合
  - 性能
  - Compose
sources:
  - "[[src-LazyColumn与Column原理及性能对比分析]]"
related:
  - "[[LazyColumn vs Column 选型决策]]"
  - "[[融合渲染架构]]"
---

# SubcomposeLayout 与懒组合

## 定义

SubcomposeLayout 是 Compose 中一种特殊的布局机制，允许在测量（Layout）阶段按需触发组合（Composition）。它是 LazyColumn 实现视口驱动懒加载的核心技术基础。

## 详解

### 常规 vs SubcomposeLayout

在常规布局（Column/Row/Box）中，组合和测量是严格分离的两个阶段：
- **组合阶段**：执行所有 `@Composable` 函数，生成 UI 树
- **测量阶段**：对已有的 UI 节点进行几何计算

SubcomposeLayout 打破了这种分离：子项的 Composable 函数不是在 Recomposition 阶段执行，而是在父组件 `measure()` 过程中通过 `subcompose()` 动态触发。

### 执行机制

```kotlin
// LazyListMeasurePolicy.measure() 简化
while (currentOffset < viewportSize && currentIndex < itemCount) {
    // 在测量阶段按需组合
    val placeable = subcompose(currentIndex) {
        itemProvider.getItem(currentIndex).invoke()
    }.first().measure(childConstraints)
    currentOffset += placeable.height
    currentIndex++
}
```

### 为什么更贵

每项组合前需：保存当前 Composer 状态 → 切换到子 Composition 的 SlotTable → 执行函数 → 恢复父级状态。即使 item 数量少，这套上下文切换的固定开销不可避免。

## 关键要点

- SubcomposeLayout 让组合与测量交织，无法分离
- 首帧时视口为空，while 循环必须逐次 subcompose + measure 填满视口，顺序阻塞在同一帧内
- CMP 单线程模型下，这些 subcompose 调用无法并行

## 与其他概念的关系

- [[LazyColumn vs Column 选型决策]] — SubcomposeLayout 是 LazyColumn 的架构成本来源
- [[融合渲染架构]] — CMP 单线程特性进一步放大 SubcomposeLayout 的首帧开销

## 来源

- [[src-LazyColumn与Column原理及性能对比分析]] — 第 5-6 章详解
