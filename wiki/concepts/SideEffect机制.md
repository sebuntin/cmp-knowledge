---
type: concept
created: 2026-04-28
updated: 2026-04-28
sources:
  - raw/带着问题学，Compose附带效应(Side Effect)一探究竟.md
tags:
  - SideEffect
  - LaunchedEffect
  - DisposableEffect
  - snapshotFlow
  - Composition生命周期
related:
  - "[[帧时钟协作机制]]"
  - "[[Composable本质]]"
---

# SideEffect机制

## 定义

Compose Side Effect API 体系提供在 Composable 生命周期内安全执行非纯 UI 操作（网络请求、监听器注册、协程启动等）的受控接口。

## 详解

### API 分类

| API | 触发时机 | 典型场景 |
|-----|---------|---------|
| `SideEffect` | 每次成功重组后同步执行 | 日志、状态同步 |
| `LaunchedEffect` | 进入组合时启动协程，key 变化时重启 | 网络请求、动画 |
| `DisposableEffect` | 进入/退出组合时回调 | 注册/注销监听器 |
| `rememberUpdatedState` | 重组时自动更新引用 | 长运行协程中保持最新值 |
| `snapshotFlow` | 状态变化时发射到 Flow | 搜索联想、防抖 |
| `produceState` | 非 Compose 数据源转 State | Flow/LiveData 转 State |

### LaunchedEffect 生命周期

```
进入组合 → 启动协程（effectDispatcher）
  ↓
key 变化 → 取消旧协程 → 启动新协程
  ↓
离开组合 → 取消协程
```

### 一帧启动延迟

LaunchedEffect 首次进入组合有一帧延迟：

```
帧 K 阶段 3: performRecompose → LaunchedEffect.onRemembered → dispatch 到 effectDispatcher
帧 K+1 阶段 1: flush effectDispatcher → 执行协程体
帧 K+1 阶段 3: broadcastFrameClock.sendFrame → 协程中 withFrameNanos 恢复
```

### snapshotFlow 原理

```kotlin
snapshotFlow { state.value }
  .debounce(300)
  .collect { ... }
```

底层：`Snapshot.registerApplyObserver` + readSet 追踪依赖，状态变化时重新执行 block 并发射。

## 关键要点

- Side Effect 不是"坏东西"，而是与外部世界交互的受控接口
- LaunchedEffect 的 key 变化机制确保协程与 Composable 生命周期同步
- rememberUpdatedState 解决长运行协程中的值过期问题
- snapshotFlow 桥接 Snapshot 系统和 Flow 操作符

## 与其他概念的关系

- [[帧时钟协作机制]] — LaunchedEffect 运行在 effectDispatcher 上，帧时钟驱动其执行
- [[Composable本质]] — Side Effect 是 Composable 函数纯组合模型与命令式世界的桥梁

## 来源

- [[src-Compose附带效应一探究竟]] — 完整文档
