---
type: source
created: 2026-04-20
updated: 2026-04-20
source_file: "raw/LazyColumn 与 Column 原理及性能对比分析.md"
ingested: 2026-04-20
tags:
  - LazyColumn
  - Column
  - 性能优化
  - 首帧
  - SubcomposeLayout
  - Compose
---

# LazyColumn 与 Column 原理及性能对比分析

## 摘要

系统对比 Compose 中 Column（全量组合）和 LazyColumn（视口驱动懒组合）的架构原理与性能差异。核心结论：LazyColumn 不是"带回收机制的列表"，而是"以视口为作用域的组合控制器"。其性能优势只在大量 item + 滚动场景下才能抵消 Subcomposition 架构开销。当所有 item 始终可见且数量较少时，懒价值为零，但成本一分不少。

## 关键发现

1. **LazyColumn 的本质是组合控制器，不是回收列表** — 滑出视口的项被整体 Dispose（销毁组合树），而非复用视图，重新进入时从零组合
2. **SubcomposeLayout 打破阶段分离** — 子项的 Composable 函数不在 Recomposition 阶段执行，而在 Layout 的 `measure()` 中通过 `subcompose()` 动态触发
3. **首帧 LazyColumn 无懒加载优势** — 视口为空时必须连续 subcompose + measure 填满第一屏，在 CMP 单线程模型下顺序执行无法并行
4. **item.key 是项级身份标识机制** — 支持数据变化时的 Diffing、动画（animateItemPlacement）、SubcomposeLayout 槽位复用，但不能阻止滑出后的 Dispose
5. **CMP 单线程特性的叠加放大** — 无并行重组 + 主线程 SkPicture 录制 + 首帧集中爆发，三重因素使 LazyColumn 首帧开销更显著
6. **<20 项固定列表应优先用 Column** — LazyColumn 的 Subcomposition、Provider 查找、State 追踪、SlotTable 上下文切换等固定开销不可避免

## 重要细节

### 四层内部架构

```
LazyListScope (DSL 注册层) —— 只注册工厂，不创建
    ↓
LazyListItemProvider (项工厂层) —— 索引到 Composable lambda 的映射
    ↓
LazyListState (状态层) —— firstVisibleItemIndex/Offset
    ↓
LazyListMeasurePolicy (布局策略层) —— while 循环决定哪些索引进入视口
    ↓
LazyLayout (SubcomposeLayout) —— subcompose() 按需创建/销毁项
```

### 首帧执行流程

```
LazyListMeasurePolicy.measure()
  ├─ subcompose(index=0) { ItemContent(0) }  ← 创建第1项
  ├─ subcompose(index=1) { ItemContent(1) }  ← 创建第2项
  ├─ ...直到填满视口（通常 8-15 项）
```

### Column vs LazyColumn 开销对比

| 开销项 | Column | LazyColumn |
|--------|--------|------------|
| 组合层 | 直接作为父级子节点 | SubcomposeLayout 独立子组合 |
| 内容获取 | 直接执行 lambda | 通过 LazyListItemProvider 间接调用 |
| 状态读取 | 无额外 | 读取 LazyListState 触发 Snapshot 追踪 |
| SlotTable | 单一层级 | 父 + 多个子 SlotTable |

### item.key 四个作用

1. **Diffing** — 数据变化时按 key 差分，避免全量重组
2. **动画** — animateItemPlacement() 依赖 key 追踪跨帧位移
3. **槽位复用** — SubcomposeLayout 通过 key 匹配已有组合，跳过 subcompose()
4. **rememberSaveable 恢复** — key 作为存储键的一部分辅助状态恢复

## 与已有知识的关联

- [[SubcomposeLayout与懒组合]] — LazyColumn 的核心架构机制
- [[LazyColumn vs Column 选型决策]] — 何时选择哪种布局
- [[融合渲染架构]] — CMP 单线程模型下 LazyColumn 首帧开销的放大效应
