---
type: source
source_file: raw/揭秘 Compose 原理：图解 Composable 的本质.md
ingested: 2026-04-28
tags:
  - Composable
  - Compose编译器插件
  - Composer
  - Recomposition
  - Snapshot
---

# src-揭秘Composable的本质

## 摘要

揭秘 Composable 函数的底层机制：Compose 编译器插件注入 Composer 参数，用 startRestartGroup/endRestartGroup 包裹函数体，通过 ScopeUpdateScope 实现重组回调，Snapshot 系统拦截状态读写驱动无效化。

## 关键发现

- **@Composable 改变函数签名**：如同 suspend 添加 Continuation 参数，@Composable 添加 Composer 参数；普通函数无法调用 Composable 函数——它无法提供 Composer
- **Composable 执行是 N 叉树 DFS 遍历**：嵌套的 Composable 形成树结构，执行顺序是可预测的深度优先遍历
- **重组 = 再次调用函数**：编译器用 startRestartGroup/endRestartGroup 包裹函数体，末尾注册 ScopeUpdateScope 回调，状态变化时递归重新调用同一函数
- **重组范围由状态读取位置决定**：Snapshot 系统通过自定义 getter 拦截状态读取；读取发生的 ScopeUpdateScope 被标记为无效。将读取推迟到 lambda 中可缩小重组范围
- **"尽可能推迟读取"是核心优化**：传递 `() -> T` 而非 `T` 可将读取从 Composition 阶段推迟到 Layout/Draw 阶段，跳过重组直接走布局+绘制
- **Compose 平台无关**：编译器插件、Runtime、Snapshot 系统是纯 Kotlin，这是 Compose Multiplatform 的基础

## 与已有知识的关联

- ScopeUpdateScope 就是 `observations` 中 RecomposeScopeImpl 的底层机制
- "推迟读取"直接关联 Snapshot 系统的 readObserver——读取时机决定了订阅表的更新时机
- Compose Multiplatform（CMP）正是利用平台无关性在 OHOS 上运行

## 来源

- [[Composable本质]] — 概念页
