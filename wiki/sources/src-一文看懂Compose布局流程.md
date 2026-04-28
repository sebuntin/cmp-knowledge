---
type: source
source_file: raw/一文看懂 Jetapck Compose 布局流程.md
ingested: 2026-04-28
tags:
  - 布局流程
  - MeasurePolicy
  - Constraints
  - IntrinsicMeasurement
  - 单次测量
---

# src-一文看懂Compose布局流程

## 摘要

系统讲解 Compose 布局流程：MeasurePolicy 定义三步测量（测子节点、定自身尺寸、放置子节点），Constraints 自顶向下传播，Kotlin 类型系统强制单次测量保证 O(n) 布局时间，Intrinsic Measurement 解决单次测量下的尺寸协商问题。

## 关键发现

- **布局三步合一**：不同于 Android 的 onMeasure/onLayout/onDraw 分离，Compose 将 measure+place 合并到单个 MeasurePolicy.measure() lambda 中，Kotlin 类型系统强制正确顺序
- **MeasurePolicy 是函数式接口**：定义 `MeasureScope.measure(measurables, constraints): MeasureResult`，每个布局容器（Column/Row/Box）提供自己的实现
- **Constraints 替代 Android MeasureSpec**：父节点传递 Constraints（min/max 宽高）给子节点，比 MeasureSpec 更显式，避免多轮测量问题
- **Modifier 节点形成布局树中的子树**：组合后 modifier 变成 ModifierNode 链，被修饰的 Composable 成为链的叶子节点，Layout 修饰符沿链拦截约束
- **强制单次测量**：同一 Measurable 测量两次会抛异常，保证 O(n) 布局时间，不论嵌套深度——解决了 Android 嵌套 RelativeLayout 的指数级测量问题
- **Intrinsic Measurement 解决单次测量限制**：正式测量前，父节点可查询子节点的固有尺寸（min/max intrinsic 宽高），这个预查询提供了足够信息设置正确约束

## 与已有知识的关联

- MeasurePolicy 和 Constraints 传播是 CMP `ComposeSceneMediator.setSize()` 后触发布局的机制
- 单次测量保证对 Fusion Renderer 路径至关重要——SkPictureRecorder 必须在单次布局中捕获完整绘制
- Intrinsic Measurement 帮助 CMP 中 NodeContainer 组件在 C++ 渲染层接管前确定正确尺寸

## 来源

- [[布局流程]] — 概念页
