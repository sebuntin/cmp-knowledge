# ByteKMP preCompose 竞品分析

## 一、目的：解决什么问题

preCompose 解决的是 **页面首帧耗时** 问题。

在正常 Compose 流程中，一个页面从创建到可见要经历：

```
创建 Mediator → 等待 Surface 就绪 → setContent(组合) → 布局 → 绘制 → 首帧可见
                ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                           这段是用户可感知的等待时间
```

其中 **组合（Composition）** 阶段执行所有 `@Composable` 函数，如果页面复杂（多层嵌套、大量子组合），或业务代码中包含耗时操作（网络请求模拟、计算密集型布局），这个阶段可能消耗数百毫秒。

preCompose 的核心思路：**把组合阶段提前到页面不可见时执行，用户导航到页面时只需做渲染，跳过最耗时的组合阶段。**

```
preCompose 触发时（后台）：创建 Mediator → 立即 setContent(组合) → 布局完成
用户导航到页面时：                                   直接渲染 → 首帧可见
                                                     极快！
```

## 二、业务如何接入

从 ByteKMP 的示例代码可以看到，接入分三步：

### Step 1：提前触发预组合

在用户还没导航到目标页面前（比如在列表页、或者页面预加载阶段），调用 ArkTS 的 `preCompose()` 函数：

```typescript
this.preloadHandler = preCompose(
  'PreComposeSample',           // 1. Composable 的注册名（对应 @ArkTsExportComposable 注解）
  0,                             // 2. 目标页面参数（传给 Composable 的初始值）
  {},                            // 3. 额外参数
  new PreComposeParam(           // 4. 业务参数 + 性能回调
    this.selectedOptionIndex,
    { onDrawFrame: (time) => { /* 首帧回调 */ } }
  ),
  { width: vp2px(180), height: vp2px(180) }  // 5. 预期尺寸（确保预组合布局准确）
)
```

### Step 2：标记预加载完成

当用户真正导航到目标页面时，调用 `markPreloaded()` 通知框架使用预组合的结果：

```typescript
this.preloadHandler?.markPreloaded()
this.showPreCompose = true   // 显示 Compose 组件
```

### Step 3：清理资源

当不再需要预组合内容时（比如切换场景、离开页面），调用 `disposePreCompose()` 释放资源：

```typescript
disposePreCompose(this.preloadHandler?.getUuid() ?? "")
```

### 完整业务接入示例

来自 ByteKMP Sample 的 `PreComposePage.ets`：

```typescript
@Component
export struct PreComposePage {
  @State showPreCompose: boolean = false
  @State preComposeCostTime: number = 0
  @State private preloadHandler ?: PreloadHandler = undefined
  private preComposeStartTime: number = 0
  private composeSize = 180

  @Builder
  preComposeUI() {
    if (this.showPreCompose) {
      // Step 2 完成：显示预组合好的 Compose 组件
      PreComposeSample(new PreComposeParam(this.selectedOptionIndex, undefined))
    } else if (!this.preloadHandler) {
      Text("点击触发 PreCompose")
        .onClick(_ => {
          // Step 1：触发预组合
          this.preloadHandler = preCompose(
            'PreComposeSample',
            0,
            {},
            new PreComposeParam(this.selectedOptionIndex, {
              onDrawFrame: (time) => {
                this.preComposeCostTime = time - this.preComposeStartTime
              }
            }),
            { width: vp2px(this.composeSize), height: vp2px(this.composeSize) }
          )
        })
    } else {
      // 预组合已完成，等待用户操作
      Text("PreCompose 触发成功，等待3s后点击加载 ComposeView")
        .onClick(_ => {
          // Step 2：标记预加载完成，显示页面
          this.preloadHandler?.markPreloaded()
          this.preComposeStartTime = new Date().getTime()
          this.showPreCompose = true
          this.preloadHandler = undefined
        })
    }
  }
}
```

## 三、实现原理

整个 preCompose 的核心是一个 `isPreCompose: Boolean` 标志，它改变了 **Content 绑定的时序**。

### 正常流程（isPreCompose = false）

```
1. 创建 ComposeSceneMediator
2. 等待 onRender() 或 onSurfaceChanged() 被调用（Surface 就绪）
3. 此时才调用 setContent() — 组合阶段发生在这里
4. 首帧渲染
```

关键代码在 `ComposeSceneMediator.ohos.kt`:

```kotlin
// onRender() 中（第 282 行）
if (scene.size == null) {
    val size = IntSize(width, height)
    scene.size = size
    if (!isPreCompose) {    // ← 正常模式：等到首帧渲染时才 setContent
        setContent()
        lifecycleOwner.lifecycle.run {
            currentState = Lifecycle.State.RESUMED
        }
    }
}
```

### PreCompose 流程（isPreCompose = true）

```
1. 创建 ComposeSceneMediator
2. 在 init{} 块中立即调用 setContent() — 组合阶段提前到此处！
3. 此时没有 Surface，组合完成但不会渲染
4. 用户导航到页面时，onPageAppear() 触发 invalidate() → 触发 onRender()
5. onRender() 跳过 setContent()，直接用已组合好的内容渲染首帧
```

关键代码：

```kotlin
// init{} 块中（第 464 行）
if (isPreCompose) {
    HarkoScope.launch { setContent() }   // ← 立即执行组合！不等 Surface
}

// onRender() 中（第 282 行）
if (!isPreCompose) { setContent() }     // ← preCompose 模式跳过

// onSurfaceChanged() 中（第 318 行）
if (needSetContent && !isPreCompose) { setContent() }  // ← preCompose 模式跳过

// onPageAppear() 中（第 394 行）
if (needRedraw) {
    invalidate()   // ← 触发重绘，使用已组合好的内容
}
```

### 时序对比图

```
正常模式:
  构造Mediator → [等待Surface] → setContent → 布局 → 绘制 → 首帧
                 |<————— 用户可感知等待 ——————>|

PreCompose模式:
  构造Mediator → setContent → 布局(后台完成)
  ...时间流逝...
  onPageAppear → invalidate → 绘制 → 首帧
                 |<- 几乎即时 ->|
```

### 参数传递链路

```
ArkTS preCompose() 调用
  → Entrance.kt: ComposeController.initRenderNode(isPreCompose=true, preComposeProbe=...)
    → RenderingUIView(isPreCompose=true, preComposeProbe=...)
      → ComposeSceneMediator(isPreCompose=true, ...)
        → init{} 块中立即 setContent()
```

## 四、性能度量

ByteKMP 还提供了配套的性能度量能力：

### PreComposeProbe 接口

定义在 `PerformanceTracer.common.kt`：

```kotlin
interface PreComposeProbe {
    fun isActualLaunched(): Long   // 返回实际启动时间戳
}
```

这个探针在每帧结束时被调用（`RenderingUIView.onDraw()`）：

```kotlin
frameDelegate.onFrameEnd(currentNanoTime(), id.toString(), preComposeProbe?.isActualLaunched())
```

配合 ArkTS 侧的 `enableFrameMonitor(true)` 和 `onDrawFrame` 回调，业务可以精确对比 Normal Compose vs PreCompose 的首帧耗时差异。

### FrameData 数据模型

```kotlin
data class FrameData(
    val id: String = "",
    val frameStartTimeNs: Long,
    val frameEndTimeNs: Long,
    val currentTimeNs: Long,
    val launchTimeStampMs: Long? = null,    // ← preCompose 探针提供的时间戳
    val metaFrameData: MetaFrameData? = null
)
```

### 性能监控开关

```kotlin
object KPerfComposeConfig {
    var enableTraceDelegate = false
    var enableFrameMonitor = false   // ← 需要开启才能收集帧数据
}
```

ArkTS 侧在 `aboutToAppear` 中开启：

```typescript
aboutToAppear(): void {
    enableFrameMonitor(true)
}
```

## 五、关键限制与约束

1. **尺寸必须预知**：`preCompose()` 调用时需要传入预期的 `{width, height}`，因为组合和布局在 Surface 就绪前就执行了。如果实际尺寸与预传尺寸不一致，会导致重新布局。

2. **Lifecycle 管理差异**：preCompose 模式下，Lifecycle 在 `init{}` 时处于 CREATED 状态，直到 `onPageShow()` 才变为 RESUMED。依赖 Lifecycle 状态的业务逻辑（如 `LifecycleResumeEffect`）需要考虑这个差异。

3. **不适用于所有场景**：如果页面内容依赖运行时数据（如网络请求返回后才确定显示什么），预组合的价值有限——预组合的只是占位/骨架屏，真实内容仍需等数据返回后重组。

4. **资源占用**：预组合会提前占用内存（组合树、LayoutNode 树等），需要在合适时机调用 `disposePreCompose()` 释放。

## 六、与 CMP 的对比

| 维度 | CMP（我们） | ByteKMP preCompose |
|------|------------|-------------------|
| Content 绑定时序 | Fusion Renderer：延迟到 `onFirstSurfaceChanged` | 可选：提前到 Mediator 构造时 |
| 首帧优化手段 | Picture 缓存、节点复用、脏区管理 | 页面级预组合 + 预布局 |
| 业务侵入性 | 无（框架内部透明优化） | 需要业务侧主动调用 `preCompose()` |
| 适用场景 | 所有页面通用 | 适合可预测页面（Tab页、预知布局的详情页） |
| 渲染路径 | Fusion Renderer + SkiaRender 双路径 | 单一渲染路径（基于 Harko） |
| 度量能力 | 无内置首帧度量 | PreComposeProbe + FrameMonitor 内置支持 |

## 七、关键源码索引

| 文件 | 位置 | 职责 |
|------|------|------|
| `ComposeSceneMediator.ohos.kt` | `compose/ui/ui/src/ohosArm64Main/.../scene/` | preCompose 核心逻辑：isPreCompose 标志控制 setContent 时序 |
| `RenderingUIView.kt` | `compose/ui/ui/src/ohosArm64Main/.../window/` | 传递 isPreCompose 给 Mediator，帧度量集成 |
| `Entrance.kt` | `compose/ui/ui/src/ohosArm64Main/.../window/` | API 入口：initRenderNode 接受 isPreCompose 参数 |
| `PerformanceTracer.common.kt` | `compose/ui/ui-util/src/commonMain/.../util/` | PreComposeProbe 接口定义 |
| `PreComposePage.ets` | `ByteKMPSample/app/ohosApp/.../precompose/` | 业务接入示例 |

## 八、总结

ByteKMP 的 preCompose 本质上是一个 **页面级预组合策略**：通过将组合阶段从"Surface 就绪后"提前到"Mediator 创建时"，把首帧耗时中最不可控的组合阶段从用户可见路径中移除。这是一个典型的 **用空间换时间、用预计算换响应速度** 的优化思路。

它的实现非常简洁——核心就是 `isPreCompose` 一个布尔标志改变了 `setContent()` 的调用时机，加上 `onPageAppear()` 中的一次 `invalidate()` 触发渲染。复杂度主要在 API 设计和生命周期管理上。
