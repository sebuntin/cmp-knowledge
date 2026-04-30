---
type: concept
created: 2026-04-28
updated: 2026-04-28
sources:
  - raw/揭秘 Compose 原理：图解 Composable 的本质.md
tags:
  - Composable
  - Compose编译器插件
  - Composer
  - Recomposition
  - Snapshot
related:
  - "[[SideEffect机制]]"
  - "[[图解协程原理]]"
---

# Composable本质

## 定义

@Composable 注解触发 Compose 编译器插件对函数进行变换：注入 Composer 参数、用 startRestartGroup/endRestartGroup 包裹函数体，使函数具备重组能力。

## 详解

### 编译器变换类比

| 注解 | 添加的参数 | 作用 |
|------|----------|------|
| `suspend` | `Continuation` | 实现异步挂起/恢复 |
| `@Composable` | `Composer` | 实现组合/重组 |

普通函数无法调用 Composable 函数——它无法提供 Composer 参数。

### 重组机制

编译后的 Composable 函数结构：

```kotlin
// 原始代码
@Composable fun Greeting(name: String) { Text("Hello $name") }

// 编译后伪代码
fun Greeting(name: String, composer: Composer) {
    composer.startRestartGroup(key)    // 标记重组范围起点
    // ... 函数体 ...
    composer.endRestartGroup()          // 标记重组范围终点
    // 注册 ScopeUpdateScope 回调
    // → 状态变化时重新调用此函数
}
```

### 重组范围与状态读取

重组范围由**状态读取的位置**决定：

```
@Composable fun Screen() {
    val name by state              // 读取发生在 Screen 作用域
    Text(name)                     // → Screen 整体重组

    // 优化：推迟读取
    NameDisplay { state.value }    // 读取推迟到 NameDisplay 内部
                                   // → 只有 NameDisplay 重组
}
```

### 推迟读取优化

| 传递方式 | 读取阶段 | 效果 |
|---------|---------|------|
| `value: T` | Composition | 触发重组 |
| `() -> T` lambda | Layout/Draw | 跳过重组，直接布局+绘制 |

## 关键要点

- @Composable 本质是编译器插件注入的 Composer 参数
- 重组 = 再次调用函数，由 ScopeUpdateScope 回调触发
- 重组范围由状态读取位置决定，lambda 推迟读取可缩小范围
- Compose 运行时平台无关——这是 Compose Multiplatform 的基础

## 与其他概念的关系

- [[图解协程原理]] — suspend 和 @Composable 都是编译器变换，类比理解
- [[SideEffect机制]] — Side Effect 是 Composable 与外部世界的桥梁
- [[帧时钟协作机制]] — Recomposer 驱动重组的实际执行

## 来源

- [[src-揭秘Composable的本质]] — 完整文档
