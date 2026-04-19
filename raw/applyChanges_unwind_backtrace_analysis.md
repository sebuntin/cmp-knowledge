# applyChanges 中 `_Unwind_Backtrace` 根因分析

> 数据来源：hiperf pid=37777 libkn.so `raw-instruction-retired`，采样总量 1,642,697,537  
> 现象：`_Unwind_Backtrace` 在 `applyChanges` 调用栈中占比 155M/178M ≈ **87%**

---

## 一、背景知识

### 1.1 Kotlin/Native 异常机制 — 为什么 throw 会触发 `_Unwind_Backtrace`

**JVM 与 KN 的关键区别**

| 平台 | 栈追踪采集时机 | 成本 |
|------|-------------|------|
| JVM（Android） | 懒惰采集：仅在调用 `e.stackTrace` 或打印时遍历 | 不打印则近乎零 |
| Kotlin/Native（OHOS） | **急切采集**：每次 `throw` 立即遍历全部栈帧 | 与栈深线性相关 |

KN 的急切采集流程：

```
throw SomeException()
    ↓
KN 运行时立刻调用 _Unwind_Backtrace()
    ↓
ARM64 逐帧解析 .eh_frame / DWARF 调试信息
    ↓
将完整栈帧列表存入 exception.stackTrace 字段
    ↓
即使后续 catch 后不使用 stackTrace，代价已经发生
```

在 Compose 的调用链中，调用栈深度达 **40-70 帧**，每次 throw 的 unwind 成本被线性放大。

---

### 1.2 Compose SlotTable — 组合树如何存储和更新

**SlotTable 是什么**

Compose 把整个 UI 树（所有 `@Composable` 函数的调用结果）存储在一个叫 `SlotTable` 的扁平数组中：

```
你写的代码:                    SlotTable 存储的内容:
Column {                      [Group(Column), Group(Row), Group(Icon),
  Row {                          Group(Title), Group(Image), ...]
    Icon()
    Title()
  }
  Image()
}
```

每个 `Group` 里除了 UI 节点外，还存储了作用域内所有 `remember { }` 的值，包括 `LaunchedEffectImpl` 等对象。

**applyChanges 的职责**

重组结束后，Compose 不立即改树，而是把变更记录为 `ChangeList`。`applyChanges()` 是真正写入 SlotTable 的时机：

```
重组计算（纯计算，不改树）
    ↓ 生成 ChangeList
applyChanges()                                    [Composition.kt:1146]
    ├── applyChangesInLocked(changes)             [Composition.kt:1098]
    │     └── changes.executeAndFlushAllPendingChanges(...)
    │           └── SlotWriter.removeCurrentGroup(...)  ← 删除离开的 Group
    └── rememberManager.dispatchRememberObservers()     ← 通知生命周期
          ↓
    onForgotten / onRemembered 回调
```

**removeCurrentGroup 做什么**（源码：`Composer.kt:4465`）

```kotlin
internal fun SlotWriter.removeCurrentGroup(rememberManager: RememberManager) {
    forAllDataInRememberOrder(currentGroup) { _, slot ->
        if (slot is RememberObserverHolder) {
            rememberManager.forgetting(slot)   // ← 通知对象即将被移除
        }
        if (slot is RecomposeScopeImpl) {
            slot.release()
        }
    }
    removeGroup()
}
```

---

### 1.3 RememberObserver 接口 — remember 对象的生命周期

```kotlin
interface RememberObserver {
    fun onRemembered()   // 对象进入 SlotTable 时调用
    fun onForgotten()    // 对象从 SlotTable 移除时调用
    fun onAbandoned()    // 对象从未被提交到 SlotTable（重组失败）
}
```

**`LaunchedEffectImpl` 实现**（源码：`Effects.kt:282`）

```kotlin
class LaunchedEffectImpl(
    private val parentCoroutineContext: CoroutineContext,
    private val task: suspend CoroutineScope.() -> Unit,
) : RememberObserver {
    private var job: Job? = null

    override fun onRemembered() {
        job = scope.launch(block = task)           // 组件出现时，启动协程
    }

    override fun onForgotten() {
        job?.cancel(LeftCompositionCancellationException())   // 组件离开时，取消协程
        job = null
    }
}

private class LeftCompositionCancellationException :
    PlatformOptimizedCancellationException("The coroutine scope left the composition")
                                                              // [Effects.kt:390]
```

`LaunchedEffect` 的本质：把一个持有协程 Job 的 `RememberObserver` 存进 SlotTable，让 Compose 在组件移除时自动调用 `cancel`。

---

### 1.4 LazyList 工作原理 — 为什么滑动时频繁触发 cancel

**SubcomposeLayout 按需组合**

`LazyColumn`/`LazyRow` 使用 `SubcomposeLayout`，在每次测量时按需组合当前可见范围的 item：

```
用户向下滑动 100px
    ↓
LazyList 重新测量
    ↓
可见范围变化：item[0] 离开顶部，item[12] 进入底部
    ↓
SubcomposeLayout.disposeOrReuseStartingFromIndex()   [SubcomposeLayout.kt:711]
    ├── item[0] → composition.dispose()
    │     ↓ removeCurrentGroup → LaunchedEffect.onForgotten() → cancel()
    └── item[12] → 新建 composition → onRemembered() → 启动协程
```

**三种离开路径**（源码：`SubcomposeLayout.kt:711-760`）

| 路径 | 触发条件 | 是否触发 cancel |
|------|---------|--------------|
| `dispose()` | 超出 reuse pool 限额，彻底销毁 | ✅ 触发 |
| `deactivate()` | 进入 reuse pool 休眠 | ✅ 触发 |
| reuse pool 命中 | 新 item 复用旧 slot，直接重组 | ❌ 不触发 |

若未配置 `SubcomposeSlotReusePolicy`（默认 `NoOpSubcomposeSlotReusePolicy`），每个离开 viewport 的 item 都走 `dispose`，**每次都触发 cancel**。

---

## 二、完整调用链（源码级）

```
[用户滑动 LazyList，item[N] 离开 viewport]
    ↓
Snapshot.sendApplyNotifications()
    ↓
Recomposer 调度重组（协程恢复）
    ↓
CompositionImpl.recompose()
    ↓
Composer.compose() — DFS 重新执行 composable 树
    ↓ [遇到 key 不匹配 / 条件分支变化]
startReplaceGroup → recordDelete()
或
SubcomposeLayout.disposeOrReuseStartingFromIndex()   [SubcomposeLayout.kt:919]
    ↓
applyChanges() → applyChangesInLocked()              [Composition.kt:1098]
    ↓
SlotWriter.removeCurrentGroup(rememberManager)       [Composer.kt:4465]
    forAllDataInRememberOrder:
        slot is RememberObserverHolder → rememberManager.forgetting(slot)
    ↓
RememberEventDispatcher.dispatchRememberObservers()  [RememberEventDispatcher.kt:194]
    for i in leaving.size-1 downTo 0:
        wrapped.onForgotten()
    ↓
LaunchedEffectImpl.onForgotten()                     [Effects.kt:290]
    job?.cancel(LeftCompositionCancellationException())
    ↓
KN throw LeftCompositionCancellationException        [Effects.kt:390]
    ↓
KN 运行时: ExceptionUtilsKt.captureStack()
    ↓
_Unwind_Backtrace()    ← hiperf 采样集中命中处
    (ARM64 帧数 40-70 帧 × DWARF eh_frame 解析)
```

---

## 三、触发场景全集

### 场景 A：LazyList 快速滑动（频率最高）

**用户行为**：快速滑动 `LazyColumn`/`LazyRow`，每帧 1-3 个 item 进出 viewport。

**技术触发路径**：

```
LazyList 测量阶段
  └── disposeOrReuseStartingFromIndex(startIndex)    [SubcomposeLayout.kt:711]
        ├── slotId NOT in reusableSlotIdsSet
        │     └── composition.dispose()              ← 超出 reuse pool 限额
        └── slotId in reusableSlotIdsSet
              └── nodeState.reuseComposition()
                    └── composition.deactivate()     [Composition.kt:1390]
                          └── deactivateCurrentGroup → forgetting → onForgotten → cancel
```

**每帧取消次数** = 离开 viewport 的 item 数 × 每 item 内的 LaunchedEffect 数。  
典型场景（每 item 含图片加载 + 动画两个 LaunchedEffect）每帧触发 **3-6 次** `_Unwind_Backtrace`。

---

### 场景 B：`LaunchedEffect(key)` 的 key 在重组中变化

**用户行为**：
- 点击切换 Tab → `LaunchedEffect(tabIndex)` key 变化
- 搜索框输入文字 → `LaunchedEffect(query)` 每次击键重启
- 分页加载 → `LaunchedEffect(page)` 随页码递增

**技术触发路径**：

```
重组执行 startReplaceGroup(key)                [Composer.kt:1543]
  └── slotKey != key（key 发生变化）
        ├── recordDelete()                     ← 标记旧 group 删除
        └── reader.skipGroup()

applyChanges → SlotWriter.removeCurrentGroup   [Composer.kt:4465]
  └── LaunchedEffectImpl → forgetting → onForgotten → job.cancel()
        → _Unwind_Backtrace()
```

---

### 场景 C：含 `LaunchedEffect` 的组件被条件性移除

**用户行为**：
- `if (isExpanded) { DetailPanel() }` — 折叠/展开面板
- `if (showDialog) { Dialog { ... } }` — 对话框关闭
- Navigation 返回上一页 — 页面 composable 销毁

**特点**：子树被递归 `removeCurrentGroup`，子树内每个 `LaunchedEffect` 都触发一次 cancel。深层嵌套组件可能一次触发 5-10 次 `_Unwind_Backtrace`。

---

### 场景 D：`rememberCoroutineScope` 宿主组件被移除

**用户行为**：
- 路由跳转，旧页面 composable 离开组合树
- `AnimatedContent` 动画切换，旧内容子树被销毁
- `Pager` 滑动超出 `offscreenPageLimit`

**特点**（源码：`Effects.kt:428`）：

```kotlin
override fun onForgotten() {
    coroutineScope.cancel(LeftCompositionCancellationException())
}
```

若 scope 内同时运行 N 个协程，内部 N 个子 Job 各自 cancel，`_Unwind_Backtrace` 被调用 **N 次**。

---

### 场景 E：SubcomposeLayout key 变化（非 LazyList）

**用户行为**：
- 屏幕旋转 → `BoxWithConstraints` 触发 SubcomposeLayout 重建
- `SelectionContainer` 选中范围变化导致 subcompose key 变更
- 自定义 `SubcomposeLayout` 传入新 key

**触发路径**：同场景 A 的 `dispose()`/`deactivate()` 路径，只是触发源不同。

---

### 场景 F：`DisposableEffect` 的 `onDispose` 中手动 cancel

```kotlin
DisposableEffect(key) {
    val job = scope.launch { ... }
    onDispose { job.cancel() }   // ← 用户代码主动 cancel
}
```

`onDispose` 在 `dispatchSideEffects` 阶段执行，其中的 `job.cancel()` 同样触发 KN throw → unwind。

---

## 四、对滑动性能与负载的影响

| 维度 | 影响 | 量化 |
|------|------|------|
| **指令消耗** | 帧内多次 cancel 累计 unwind 开销 | 155M / 采样窗口，占 applyChanges 的 87% |
| **主线程阻塞** | applyChanges 在主线程同步执行，unwind 不可并行 | 阻塞时间 ∝ item 离开数 × 栈深 |
| **帧率压力** | 快速滑动时每帧 3-6 次 cancel，叠加 applyChanges 其他逻辑 | 对 60fps 有直接压力 |
| **内存抖动** | `LeftCompositionCancellationException` 每次 cancel 分配一个新对象 | 间接增加 GC 压力 |
| **级联开销** | cancel 后新 item onRemembered 启动新协程，产生 forget+remember 双倍成本 | 每 item 各一次 |

**关键认知**：这 155M 指令**不是业务逻辑的开销**，而是 KN 运行时异常实现机制对高频 cancel 操作收取的"税"。

---

## 五、优化方案

| 优先级 | 方案 | 原理 | 适用场景 |
|--------|------|------|---------|
| ⭐⭐⭐ | 生产包添加 `-Xbinary=sourceInfoType=none` | 关闭 KN 急切栈追踪，throw 时不调用 `_Unwind_Backtrace` | 所有场景，**直接消除 155M** |
| ⭐⭐⭐ | `SubcomposeSlotReusePolicy(5)` 配置 LazyList | item 走 reuse pool 路径时不触发 cancel | LazyList item 含 LaunchedEffect |
| ⭐⭐ | `LaunchedEffect` key 改用稳定 id（数据库 id 而非 index） | 避免 item 复用时 key 变化导致不必要的 cancel+restart | 以 index 为 key 的场景 |
| ⭐⭐ | 将网络/IO 逻辑上移到 ViewModel 协程 | ViewModel scope 不依赖组合树，不因 item 移除而 cancel | 图片加载、数据请求 |
| ⭐ | 减少单 item 内 `LaunchedEffect` 数量 | 每减少 1 个，每次 item 离开少 1 次 unwind | item 含多个 effect |
| ⭐ | 频繁变化的 key 用 `rememberUpdatedState` + `LaunchedEffect(Unit)` | key 变化时不重启 effect，内部读取最新值 | 搜索框防抖、实时过滤 |

---

## 六、验证方法

```bash
# 确认 _Unwind_Backtrace 的直接调用者是异常路径而非 GC 路径
jq '[ .[] | select(.libName=="libkn.so" and .symbol=="_Unwind_Backtrace") ] |
    group_by(.callerSymbol) |
    map({caller: .[0].callerSymbol, count: length}) |
    sort_by(-.count) | .[0:5]' perf.json
```

**预期结果**：top callers 出现 `ExceptionOps_ThrowException` / `kotlin::ExceptionUtilsKt__ExceptionUtilsKt$captureStack` 等 KN 异常栈帧采集符号。

若出现 `mm::ThreadData::gcSafePoint` 等 GC 符号，则说明还有 GC 栈根扫描叠加，需分别处理两个来源。
