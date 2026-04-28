---
type: source
source_file: raw/Kotlin Jetpack 实战  09. 图解协程原理.md
ingested: 2026-04-28
tags:
  - 协程
  - CPS
  - Continuation
  - 状态机
---

# src-图解协程原理

## 摘要

图解 + 动画形式解释 Kotlin 协程的底层原理：编译器通过 CPS 变换将 suspend 函数转为状态机，单个 Continuation 实例在状态间复用，实现轻量级用户态协作式并发。

## 关键发现

- **suspend 函数 = 隐式 Continuation 参数**：编译器为每个 suspend 函数追加 `Continuation` 参数，类型从 `() -> T` 变为 `(Continuation) -> Any?`（返回值可能是 COROUTINE_SUSPENDED、实际结果或 null）
- **label 状态机**：编译器生成 `ContinuationImpl` 子类，用 `label` 整数 + `when` 块实现状态转换；每个状态设置 label 为下一值，调用下一个 suspend 函数并检查返回值
- **单实例复用**：整个协程生命周期内只创建一个 Continuation 对象，所有状态转换共享同一实例，内存开销远低于回调链
- **假 suspend 函数**：标记了 suspend 但内部无其他 suspend 调用的函数永不挂起，但编译器仍会做 CPS 变换
- **用户态协作式**：协程不依赖内核线程，通过 Dispatcher 调度，可在不同线程间切换

## 与已有知识的关联

- Recomposer 的工作协程基于此协程机制：`suspendCancellableCoroutine` 挂起 → `workContinuation.resume()` 唤醒
- `LaunchedEffect`、`rememberCoroutineScope` 的生命周期管理依赖协程取消机制
- `withFrameNanos` 的挂起/恢复本质是协程状态机的一次状态转换

## 来源

- [[图解协程原理]] — 概念页
