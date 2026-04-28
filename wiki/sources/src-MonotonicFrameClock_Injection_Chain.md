---
type: source
created: 2026-04-27
updated: 2026-04-27
source_file: raw/MonotonicFrameClock_Injection_Chain.md
ingested: 2026-04-27
tags:
  - 帧时钟
  - MonotonicFrameClock
  - BroadcastFrameClock
  - CoroutineContext
  - 依赖注入
related:
  - "[[帧时钟协作机制]]"
---

# MonotonicFrameClock 注入链分析

## 摘要

分析 Compose 环境中 `withFrameNanos` 如何通过 Kotlin 协程上下文的依赖注入机制，最终执行到 `Recomposer` 内部维护的 `BroadcastFrameClock`。文档揭示了帧时钟的发布/订阅架构：Recomposer 为发布者，动画/Effect 协程为订阅者，CoroutineContext 为 DI 容器。

## 关键发现

- **注入链路 5 步**：Recomposer 持有 BroadcastFrameClock → 合成到 effectCoroutineContext → 通过 Composition/rememberCoroutineScope 传播 → 消费者协程继承上下文 → `withFrameNanos` 寻址到 BroadcastFrameClock
- **`withFrameNanos` 是路由器**：顶层挂起函数本身不实现帧等待，而是从 `coroutineContext.monotonicFrameClock` 查找实际实现
- **依赖注入容器**：CoroutineContext 充当 DI 容器，确保订阅者无需显式引用就能找到正确的帧时钟
- **与帧时钟协作机制的补充关系**：本文档聚焦注入链路的"Why"，帧时钟协作机制文档描述运行时的"How"（两级级联、六阶段、双路径 dispatch）

## 与已有知识的关联

- 补充了 [[帧时钟协作机制]] 中 CoroutineContext 传播的具体机制
- 本文档描述的注入链是 [[帧时钟协作机制]] 中"协程上下文组装"的理论基础
