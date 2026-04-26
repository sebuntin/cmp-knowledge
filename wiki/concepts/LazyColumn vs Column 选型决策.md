---
type: concept
created: 2026-04-20
updated: 2026-04-20
tags:
  - LazyColumn
  - Column
  - 选型决策
  - 首帧性能
  - Compose
sources:
  - "[[src-LazyColumn与Column原理及性能对比分析]]"
related:
  - "[[SubcomposeLayout与懒组合]]"
  - "[[融合渲染架构]]"
---

# LazyColumn vs Column 选型决策

## 定义

Column（全量组合）和 LazyColumn（视口驱动懒组合）的选择决策框架。核心原则：LazyColumn 的性能优势只在大量 item + 滚动场景下成立，少量固定内容应优先使用 Column。

## 决策树

```
是否需要展示列表？
├── 否 → 使用普通布局（Box/Column/Row）
├── 是 → 数据量是否大？（>20 项或不确定）
    ├── 否，且首帧敏感 → 使用 Column
    └── 是，或需要滚动 → 使用 LazyColumn
```

## Column 适用场景

- 子项数量固定且较少（通常 <20）
- 内容无需滑出销毁（如首屏功能入口）
- 对首帧性能敏感
- 需要长期保持项内 `remember` 状态

## LazyColumn 适用场景

- 数据量大（数百至数千项）
- 需要滚动浏览
- 子项高度相近且可滑出释放

## 直观差异

| 维度 | Column | LazyColumn |
|------|--------|------------|
| 组合时机 | 父组件重组时全量组合 | 仅视口内按需组合 |
| 滚动能力 | 需外层 `verticalScroll()` | 内置滚动 |
| 项生命周期 | 与父组件共存亡 | 滑出即 Dispose |
| 状态保持 | `remember` 长期保持 | 滑出后 `remember` 丢失 |

## LazyColumn 首帧优化策略

如果必须在首页使用 LazyColumn：
1. 减少首屏项数（控制卡片高度，不超过 5-6 项）
2. 推迟复杂内容（LaunchedEffect 延迟图片加载）
3. 避免嵌套 LazyColumn（多重 Subcomposition 指数级放大开销）
4. 使用 `itemContentType` 帮助优化重组路径
5. 使用 `item.key` 业务唯一标识支持 Diffing 和动画

## 关键要点

- LazyColumn 首帧是"批量创建"而非"懒加载"——视口为空时必须连续创建所有可见项
- CMP 单线程模型（无并行重组 + 主线程 SkPicture 录制）进一步放大 LazyColumn 首帧开销
- <20 项固定列表用 Column，LazyColumn 的固定架构成本（Subcomposition、Provider、State 追踪）不可忽略

## 来源

- [[src-LazyColumn与Column原理及性能对比分析]] — 全文
