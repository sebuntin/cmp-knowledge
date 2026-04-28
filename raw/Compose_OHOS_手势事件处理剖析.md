# Compose for OHOS 手势事件处理机制剖析

## 一、前置知识：理解事件处理的基本概念

### 1.1 什么是手势事件？

当你在手机屏幕上**点击、滑动、长按、缩放**时，操作系统会把你的操作转化成一连串的"触摸事件"（Touch Event）。每个事件包含：

- **类型**：手指按下（Down）、移动（Move）、抬起（Up）、取消（Cancel）
- **坐标**：触摸点在屏幕上的 (x, y) 位置
- **时间戳**：事件发生的精确时间
- **手指 ID**：多点触控时区分不同手指

### 1.2 为什么需要跨语言传递？

本项目使用三种语言的协作：

```
ArkTS (OHOS 原生)  →  C++ (桥接层)  →  Kotlin (Compose 框架)
   ↓                     ↓                    ↓
 捕获触摸事件          跨语言传递           处理手势逻辑
```

- **ArkTS**：OHOS 系统的语言，负责从系统获取触摸事件
- **C++**：作为"翻译官"，把事件从 ArkTS 传递到 Kotlin
- **Kotlin**：Compose 框架的语言，负责把手势应用到 UI 组件

### 1.3 两种渲染路径

本项目支持两种渲染方式，手势处理在两种路径中略有不同：

| 渲染路径                      | 触摸事件来源                        | 是否需要 EGL 就绪   |
| ------------------------- | ----------------------------- | ------------- |
| **Fusion Renderer**（融合渲染） | ArkUI `NodeContainer.onTouch` | 否，只需容器活跃      |
| **SkiaRender**（自渲染）       | ArkUI `Stack.onTouch`         | 是，需等待 EGL 初始化 |

---

## 二、事件处理全流程概览

一次触摸事件从手指触碰屏幕到 Compose 处理完毕，经历以下 6 个阶段：

```
┌─────────────────────────────────────────────────────────────────────┐
│                        用户手指触摸屏幕                                │
└──────────────────────────┬──────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 阶段1: ArkTS 捕获                                                    │
│   OHOS 系统 → TouchEvent → .onTouch() 回调                           │
│   文件: skiarender/Compose.ets:113 / fusionRenderer/Compose.ets:126 │
└──────────────────────────┬──────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 阶段2: 坐标变换（仅互操作视图）                                          │
│   ArkUIView.onTouchEvent() → vp2px 转换 + 偏移校正                    │
│   文件: ArkUIView.ets:83 / TouchEventUtils.ets                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 阶段3: 跨语言传递 (ArkTS → Kotlin)                                     │
│   Controller.dispatchTouchEvent() → C++ NAPI 桥接 → Kotlin           │
│   文件: arkui_view_controller.cpp:245                                │
└──────────────────────────┬──────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 阶段4: 策略分发                                                       │
│   InputStrategy.onDispatchTouch() → 判断是否该处理这个事件              │
│   文件: FusionRendererStrategyImpl.kt:119 / SkiaRendererStrategyImpl │
└──────────────────────────┬──────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 阶段5: 事件转换 (OHOS TouchEvent → Compose PointerEvent)              │
│   ComposeSceneMediator.sendPointerEvent()                           │
│   - 类型映射: Down→Press, Up→Release, Move→Move, Cancel→取消          │
│   - 坐标缩放: 像素坐标 × density → Compose 逻辑坐标                     │
│   - 多指追踪: activeChangedPointers 维护所有活跃触控点                  │
│   文件: ComposeSceneMediator.ohos.kt:303                             │
└──────────────────────────┬──────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 阶段6: Compose 内部处理                                               │
│   Scene.sendPointerEvent() → 命中测试 → 事件分发 → 手势识别             │
│   文件: PointerInputEventProcessor.kt                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、逐阶段详解

### 阶段1：ArkTS 捕获触摸事件

**核心文件**：
- `ui-arkui/.../ets/skiarender/Compose.ets:113`
- `ui-arkui/.../ets/fusionRenderer/Compose.ets:126`

当用户触摸屏幕时，OHOS 系统生成 `TouchEvent`，ArkUI 框架通过 `.onTouch()` 回调将事件传递给组件。

**两种渲染路径的触摸捕获代码几乎完全相同**：

```typescript
// SkiaRender 路径 - skiarender/Compose.ets:113
.onTouch(e => {
  this.host.msgService.dragAndDropProxy?.updateTouchEvent(e);  // 拖拽代理更新
  this.requireController().dispatchTouchEvent(e, true);        // 分发给 Kotlin
})

// Fusion Renderer 路径 - fusionRenderer/Compose.ets:126
.onTouch(e => {
  this.host.msgService.dragAndDropProxy?.updateTouchEvent(e);  // 拖拽代理更新
  this.requireController().dispatchTouchEvent(e, true);        // 分发给 Kotlin
})
```

**OHOS TouchEvent 的结构**：

```typescript
interface TouchEvent {
  type: TouchType        // 0=Down, 1=Up, 2=Move, 3=Cancel
  timestamp: number      // 纳秒级时间戳
  touches: TouchObject[] // 当前屏幕上所有触摸点
  changedTouches: TouchObject[]  // 本次发生变化的触摸点
}

interface TouchObject {
  id: number     // 手指标识
  x: number      // 相对于组件的 x 坐标（vp 单位）
  y: number      // 相对于组件的 y 坐标（vp 单位）
  screenX: number  // 相对于屏幕的 x 坐标
  screenY: number  // 相对于屏幕的 y 坐标
}
```

> **通俗理解**：想象你在一张桌子上放了一张透明纸（ArkTS 层）。当你的手指触碰到透明纸时，纸上的传感器记录了触碰的位置和方式，然后把这些信息装进一个"信封"（TouchEvent）里，准备寄给下一位处理者。

---

### 阶段2：坐标变换（互操作视图专用）

**核心文件**：
- `ui-arkui/.../ets/compose/ArkUIView.ets:83`
- `ui-arkui/.../ets/compose/TouchEventUtils.ets`

当触摸事件发生在**嵌入 Compose 的原生 ArkUI 互操作视图**（`ArkUIView`）上时，需要额外的坐标变换。

```typescript
// ArkUIView.ets:83
onTouchEvent(e: TouchEvent) {
  const offset = this.getPositionToParent()  // 获取自身相对父容器的偏移
  const event = transformTouchEvent(e, vp2px)// 将所有vp坐标转换为px像素
  offsetTouchEventLocalPosition(event, {     // 减去偏移，得到准确的本地坐标
    x: -vp2px(offset.x),
    y: -vp2px(offset.y)
  })
  return this.builderNode.postTouchEvent(event) // 投递给内部 BuilderNode
}
```

**为什么要做坐标变换？**

OHOS 系统的坐标使用 **vp**（虚拟像素）单位，但 Compose 内部使用 **px**（物理像素）。vp 和 px 之间的转换由 `vp2px` 函数完成。同时，互操作视图在父容器中可能有偏移，需要减去这个偏移量才能得到正确的本地坐标。

```
┌─────────────────────────────┐
│ ComposeContainer            │
│  ┌────────────┐             │
│  │ ArkUIView  │ ← 触摸点     │
│  │  (有偏移)   │   需要减去偏移│
│  └────────────┘             │
└─────────────────────────────┘
```

> **通俗理解**：就像你在一张地图上标记了一个点，但地图本身被移动过。你需要减去地图移动的距离，才能得到这个点在原始坐标系中的正确位置。

---

### 阶段3：跨语言传递（ArkTS → Kotlin）

**核心文件**：`ui-arkui/.../cpp/compose/arkui_view_controller.cpp:245`

触摸事件从 ArkTS 传递到 Kotlin 需要经过 NAPI（Node-API）桥接层：

```
ArkTS: controller.dispatchTouchEvent(e, true)
   ↓ (NAPI 调用)
C++:  ArkUIViewController_dispatchTouchEvent(controller,     
         nativeTouchEvent, ignoreInteropView)
   ↓ (调用 Kotlin/Native 导出函数)
Kotlin: ComposeArkUIViewContainer.dispatchTouchEvent(nativeTouchEvent, ignoreInteropView)
```

**C++ 桥接代码**：

```cpp
// arkui_view_controller.cpp:245
void ArkUIViewController_dispatchTouchEvent(
    ArkUIViewController *controller,
    void *nativeTouchEvent,
    bool ignoreInteropView
) {
    if (controller == nullptr) {
        LOGE("controller is null");
        return;
    }
    // 调用 Kotlin/Native 编译导出的函数
    androidx_compose_ui_arkui_ArkUIViewController_dispatchTouchEvent(
        controller, nativeTouchEvent, ignoreInteropView
    );
}
```

**Kotlin 侧接收**：

```kotlin
// ComposeArkUIViewContainer.kt:384
override fun dispatchTouchEvent(
    nativeTouchEvent: napi_value,
    ignoreInteropView: Boolean
): Boolean {
    return inputStrategy.onDispatchTouch(nativeTouchEvent)
}
```

> **通俗理解**：NAPI 就像一个"同声传译器"。ArkTS 说话（事件），C++ 翻译，Kotlin 听到翻译后的内容。整个过程对用户是无感知的。

---

### 阶段4：策略分发（InputStrategy）

**核心文件**：
- `ui/.../ohosMain/fusionRenderer/.../FusionRendererStrategyImpl.kt:119`
- `ui/.../ohosMain/skia/.../SkiaRendererStrategyImpl.kt`

系统使用**策略模式**来决定如何处理触摸事件。两种渲染路径各有自己的 `InputStrategy` 实现：

```
                    ┌──────────────────┐
                    │  InputStrategy   │  ← 策略接口
                    │  (接口定义)       │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                              ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│ FusionRenderer           │  │ SkiaRenderer             │
│ InputStrategy            │  │ InputStrategy            │
│                          │  │                          │
│ shouldDispatchTouch():   │  │ shouldDispatchTouch():   │
│   container.isActive()   │  │   !surfaceDestroyed      │
│                          │  │                          │
│ onDispatchTouch():       │  │ onDispatchTouch():       │
│   mediator.sendPointer.. │  │   if (!eglReady) return  │
│                          │  │   mediator.sendPointer.. │
└──────────────────────────┘  └──────────────────────────┘
```

**Fusion Renderer 策略**（融合渲染）：

```kotlin
// FusionRendererStrategyImpl.kt:119
internal class FusionRendererInputStrategy(
    private val container: ComposeArkUIViewContainer
) : InputStrategy {
    override fun shouldDispatchTouch(): Boolean = container.isActive()

    override fun onDispatchTouch(nativeTouchEvent: napi_value): Boolean {
        if (!container.isActive()) return true  // 不活跃时返回 true（不消费）
        return container.mediator?.sendPointerEvent(
            container.requiredEnv, nativeTouchEvent
        ) ?: false
    }
}
```

**SkiaRender 策略**（自渲染）：

```kotlin
// SkiaRendererStrategyImpl.kt
internal class SkiaRendererInputStrategy(
    private val container: ComposeArkUIViewContainer
) : InputStrategy {
    override fun shouldDispatchTouch(): Boolean = !container.nativeSurfaceHasBeenDestroyed

    override fun onDispatchTouch(nativeTouchEvent: napi_value): Boolean {
        if (!container.isEglReady()) return false  // EGL 未就绪时不处理
        return container.mediator?.sendPointerEvent(
            container.requiredEnv, nativeTouchEvent
        ) ?: false
    }
}
```

**关键区别**：

| 维度 | Fusion Renderer | SkiaRender |
|------|----------------|------------|
| 判断条件 | `isActive()`（容器是否活跃） | `isEglReady()`（EGL 是否初始化） |
| 不满足时返回 | `true`（不消费事件） | `false`（拒绝事件） |

> **通俗理解**：策略模式就像"门口的保安"。Fusion Renderer 的保安只看"有没有营业"（isActive），SkiaRender 的保安还要检查"设备是否准备好了"（EGL 就绪）。只有通过检查的事件才能进入下一环节。

---

### 阶段5：事件转换（核心环节）

**核心文件**：`ui/.../scene/ComposeSceneMediator.ohos.kt:303`

这是整个流程中**最关键**的环节——将 OHOS 原生的触摸事件转换为 Compose 框架能理解的指针事件。

#### 5.1 类型映射

OHOS 和 Compose 对触摸事件类型的定义不同，需要映射：

```
OHOS TouchType          Compose PointerEventType
─────────────          ─────────────────────
0 (Down)         →     Press     (手指按下)
1 (Up)           →     Release   (手指抬起)
2 (Move)         →     Move      (手指移动)
3 (Cancel)       →     取消处理   (系统取消，不走正常映射)
```

```kotlin
// ComposeSceneMediator.ohos.kt:393
private fun Int.asPointerEventType(): PointerEventType = when (this) {
    0 -> PointerEventType.Press    // TouchType.Down
    1 -> PointerEventType.Release  // TouchType.Up
    2 -> PointerEventType.Move    // TouchType.Move
    3 -> PointerEventType.Release  // Cancel（特殊处理，不走此分支）
    else -> PointerEventType.Unknown
}
```

#### 5.2 坐标缩放

OHOS 的触摸坐标以**物理像素**为单位，Compose 内部使用**密度无关像素（dp）**。转换公式：

```
Compose 坐标 = 原始坐标 × density（屏幕密度系数）
```

```kotlin
// ComposeSceneMediator.ohos.kt:413
private fun napi_value.getChangedPointers(density: Float): List<ComposeScenePointer> {
    val changedPointers = mutableListOf<ComposeScenePointer>()
    // ... 遍历 changedTouches 数组 ...
    val x = JsEnv.getValueDouble(xProp)?.toFloat()
    val y = JsEnv.getValueDouble(yProp)?.toFloat()

    changedPointers.add(
        ComposeScenePointer(
            id = PointerId(id),           // 手指唯一标识
            position = Offset(
                x * density,              // 像素 × 密度 = Compose 坐标
                y * density
            ),
            pressed = type.asPointerEventType().isPressed(),  // 是否按下
            type = PointerType.Touch,     // 触摸类型
            pressure = 1f,                // 压力值（OHOS 触摸默认为1）
            historical = historicalPoints  // 历史触摸点（高频采样）
        )
    )
    return changedPointers
}
```

#### 5.3 多指触控追踪

Compose 使用 `activeChangedPointers` 字典来追踪所有**当前活跃的触摸点**：

```kotlin
// ComposeSceneMediator.ohos.kt:198
private val activeChangedPointers = mutableMapOf<PointerId, ComposeScenePointer>()

// 在 sendPointerEvent 中：
// 1. 移除已抬起的触摸点
activeChangedPointers.removeIf { (_, pointer) -> !pointer.pressed }
// 2. 添加新的/更新的触摸点
activeChangedPointers.putAll(changedPointers.associateBy { it.id })
// 3. 合成完整的触摸点列表
val pointers = activeChangedPointers.values.toList()
```

**多指触控的典型流程**：

```
时间线 →
┌──────────────┬──────────────────────┬──────────────────┐
│  手指1 Down   │  手指2 Down           │  手指1 Up        │
│              │  手指1 Move           │  手指2 Move      │
├──────────────┼──────────────────────┼──────────────────┤
│ activeChangedPointers:              │                  │
│ {1: pointer1} │ {1: pointer1,       │ {2: pointer2}    │
│              │  2: pointer2}        │                  │
└──────────────┴──────────────────────┴──────────────────┘
```

#### 5.4 Cancel 事件的特殊处理

Cancel 事件（类型=3）表示**系统取消了当前的触摸序列**（如来电打断、系统弹窗）。处理方式与普通事件不同：

```kotlin
// ComposeSceneMediator.ohos.kt:306
if (event.rawTouchType == 3) {
    activeChangedPointers.clear()    // 清空所有追踪的触摸点
    scene.cancelPointerInput()       // 通知 Compose 取消所有进行中的手势
    return true                      // 返回 true 表示事件已消费
}
```

#### 5.5 GC 抑制优化

触摸事件（尤其是 Press）可能触发 Kotlin/Native 的垃圾回收（GC），导致卡顿。系统在手指按下时**抑制 GC**，在手指抬起或取消时**恢复 GC**：

```kotlin
// ComposeSceneMediator.ohos.kt:342
private fun suppressGCIfNeed(eventType: PointerEventType) {
    when (eventType) {
        PointerEventType.Move -> { /* Move 不处理 */ }
        PointerEventType.Press -> configuration.internalStartGCSuppressor()
        else -> configuration.internalStopGCSuppressor()
    }
}
```

> **通俗理解**：事件转换就像"翻译+单位换算"。OHOS 说"手指0在位置(100, 200)按下了"，翻译后变成 Compose 能理解的"ID为0的指针在密度坐标(300, 600)处产生了 Press 事件"（假设 density=3）。

---

### 阶段6：Compose 内部处理

**核心文件**：`ui/.../commonMain/.../pointer/PointerInputEventProcessor.kt`

事件转换完成后，进入 Compose 框架的标准处理流程。这个过程对所有平台通用。

#### 6.1 处理流程

```
scene.sendPointerEvent(eventType, pointers, timeMillis, nativeEvent)
   ↓
PointerInputEventProcessor.process(pointerEvent)
   ↓
   ├── 1. 创建 InternalPointerEvent（包装事件数据）
   ├── 2. 命中测试（Hit Test）—— 找到触摸点下方的 UI 组件
   ├── 3. 构建事件分发路径（Hit Path）
   ├── 4. 沿路径分发事件
   └── 5. 返回消费状态
```

#### 6.2 命中测试（Hit Test）

当手指按下时，Compose 从根节点开始，向下遍历 UI 树，找到包含触摸坐标的最深层组件：

```
┌────────────────────────────────┐
│  根节点 (Root LayoutNode)       │
│  ┌──────────────────────────┐  │
│  │ Column                   │  │
│  │  ┌────────────────────┐  │  │
│  │  │ Button ← 命中!     │  │  │  手指触摸点 (x, y)
│  │  │    (x,y) 在按钮内   │  │  │     ↓
│  │  └────────────────────┘  │  │  落在 Button 上
│  │  ┌────────────────────┐  │  │
│  │  │ Text               │  │  │
│  │  └────────────────────┘  │  │
│  └──────────────────────────┘  │
└────────────────────────────────┘
```

```kotlin
// PointerInputEventProcessor.kt:96
for (i in 0 until internalPointerEvent.changes.size()) {
    val pointerInputChange = internalPointerEvent.changes.valueAt(i)
    if (pointerInputChange.changedToDownIgnoreConsumed()) {
        // 从根节点开始命中测试
        root.hitTest(pointerInputChange.position, hitResult, pointerInputChange.type)
        if (hitResult.isNotEmpty()) {
            // 记录命中路径，后续事件沿此路径分发
            hitPathTracker.addHitPath(pointerInputChange.id, hitResult)
        }
    }
}
```

#### 6.3 事件分发

事件沿命中路径分发，经过三层 pass：

```
         初始 (Initial)              主 (Main)              最终 (Final)
         父→子 方向                  子→父 方向             父→子 方向
    ┌──────────────┐          ┌──────────────┐       ┌──────────────┐
    │ 父节点先收到   │          │ 子节点先收到   │       │ 父节点先收到   │
    │ 可拦截事件     │          │ 可消费事件    │       │ 做最终处理     │
    └──────────────┘          └──────────────┘       └──────────────┘

    用于: 父组件拦截             用于: 手势识别        用于: 清理/通知
    (如 ScrollView 拦截)
```

#### 6.4 事件消费

如果某个组件"消费"了事件（`isConsumed = true`），上层组件就不会再处理它：

```kotlin
// PointerInputEventProcessor.kt:136
var anyChangeConsumed = false
for (i in 0 until internalPointerEvent.changes.size()) {
    val change = internalPointerEvent.changes.valueAt(i)
    if (change.isConsumed) {
        anyChangeConsumed = true
        break
    }
}
return ProcessResult(
    dispatchedToAPointerInputModifier = dispatchedToSomething,
    anyMovementConsumed = anyMovementConsumed,
    anyChangeConsumed = anyChangeConsumed  // 返回给 OHOS，决定是否继续传递
)
```

#### 6.5 手势识别

Compose 内置了多种手势检测器，它们基于协程（Coroutine）工作：

```kotlin
// 开发者使用示例
Modifier.pointerInput(Unit) {
    detectTapGestures { offset ->
        // 点击手势识别成功
    }
}

Modifier.pointerInput(Unit) {
    detectDragGestures { change, dragAmount ->
        // 拖拽手势识别
    }
}

Modifier.pointerInput(Unit) {
    detectTransformGestures { centroid, pan, zoom, rotation ->
        // 缩放/旋转手势识别
    }
}
```

手势识别器内部通过 `awaitPointerEvent()` 挂起协程，等待下一个触摸事件：

```
协程挂起                    协程恢复                     手势判定
   ↓                          ↓                           ↓
awaitPointerEvent()  ←  sendPointerEvent() 通知  ←  系统触摸事件
   ↓                          ↓                           ↓
等待中...              检查事件序列是否符合          Down → Move → Move → Up
                       手势条件                        = 拖拽手势 ✓
```

> **通俗理解**：命中测试就像"打靶"——系统找出手指下方最深层的组件。事件消费就像"抢答"——谁先消费了事件，其他人就不能再用了。手势识别就像"看连续剧"——需要观察一系列事件的组合模式才能判断用户做了什么手势。

---

## 四、完整调用链路图

以下是手指按下（Down）→ 移动（Move）→ 抬起（Up）的完整调用链：

```
用户手指触摸
    │
    ▼
[OHOS 系统] 生成 TouchEvent {type=0(DOWN), changedTouches=[{id=0, x=100, y=200}]}
    │
    ▼
[ArkTS] .onTouch(e) 回调
    │  文件: skiarender/Compose.ets:113 或 fusionRenderer/Compose.ets:126
    │  操作: 拖拽代理更新 + 调用 dispatchTouchEvent
    ▼
[ArkTS → C++ → Kotlin] NAPI 桥接传递
    │  文件: arkui_view_controller.cpp:245
    │  操作: 将 napi_value 传递到 Kotlin/Native
    ▼
[Kotlin] ComposeArkUIViewContainer.dispatchTouchEvent()
    │  文件: ComposeArkUIViewContainer.kt:384
    │  操作: 委托给 InputStrategy
    ▼
[Kotlin] InputStrategy.onDispatchTouch()
    │  文件: FusionRendererStrategyImpl.kt:119 或 SkiaRendererStrategyImpl.kt
    │  操作: 检查是否应该处理事件
    ▼
[Kotlin] ComposeSceneMediator.sendPointerEvent()
    │  文件: ComposeSceneMediator.ohos.kt:303
    │  操作:
    │  1. 检查是否 Cancel 事件（type=3）
    │  2. 获取事件类型：0→Press
    │  3. 抑制 GC（Press 时）
    │  4. 提取触摸点并转换坐标
    │  5. 更新 activeChangedPointers
    │  6. 调用 scene.sendPointerEvent()
    ▼
[Kotlin] PointerInputEventProcessor.process()
    │  文件: PointerInputEventProcessor.kt:65
    │  操作:
    │  1. 创建 InternalPointerEvent
    │  2. 命中测试 (root.hitTest)
    │  3. 构建分发路径 (hitPathTracker.addHitPath)
    │  4. 分发事件 (hitPathTracker.dispatchChanges)
    │  5. 检查消费状态
    ▼
[Kotlin] 手势识别器（协程）
    │  操作: detectTapGestures / detectDragGestures / 等
    │  结果: 识别出手势类型，回调给开发者代码
    ▼
[返回值] Boolean（事件是否被消费）
    │  ← true: 事件已消费，OHOS 不再向上传递
    │  ← false: 事件未消费，OHOS 继续向上传递给父组件
    ▼
[ArkTS] 返回给 OHOS 系统
```

---

## 五、关键设计点总结

### 5.1 为什么用策略模式？

两种渲染路径对手势的处理条件不同：
- **Fusion Renderer**：不需要 OpenGL/EGL，只需容器活跃即可
- **SkiaRender**：必须等待 EGL 初始化完成

策略模式让 `ComposeArkUIViewContainer` 不需要知道具体细节，只通过 `InputStrategy` 接口调用即可。

### 5.2 为什么要追踪 activeChangedPointers？

OHOS 的每个 TouchEvent 只包含**本次变化的触摸点**（changedTouches），但 Compose 需要**所有活跃的触摸点**来正确处理多点触控。因此系统维护了一个 `activeChangedPointers` 字典，在每次事件到来时更新：

```
事件到来 → 移除已抬起的指针 → 添加/更新变化的指针 → 合成完整指针列表 → 发送给 Compose
```

### 5.3 历史触摸点（Historical Points）的作用

OHOS 的触摸采样率可能高于 Compose 的帧率。系统会在一次回调中提供多个历史触摸点，让手势识别器（特别是速度计算）更加精确：

```kotlin
// 提取历史触摸点
val historicalPoints = mutableListOf<HistoricalChange>()
val historicalPointsArray = JsEnv.callFunction(this, historicalPointsFun)
// ... 遍历并转换坐标 ...

// 附加到每个 ComposeScenePointer
ComposeScenePointer(
    // ...
    historical = historicalPoints  // 历史数据用于速度计算
)
```

### 5.4 GC 抑制为什么重要？

在 Kotlin/Native 中，垃圾回收（GC）会暂停所有线程。如果 GC 在触摸事件处理期间触发，会导致明显的卡顿（"掉帧"）。通过在手指按下时抑制 GC，可以保证流畅的触摸响应。

### 5.5 Cancel 事件的特殊性

Cancel 事件表示触摸序列被系统中断（来电、弹窗等）。此时必须：
1. 清空所有追踪的指针
2. 通知 Compose 取消所有进行中的手势

如果不正确处理 Cancel，会导致手势识别器"卡死"在中间状态，无法响应后续触摸。

---

## 六、文件索引

| 文件 | 角色 |
|------|------|
| `ets/skiarender/Compose.ets` | SkiaRender 路径触摸事件入口 |
| `ets/fusionRenderer/Compose.ets` | Fusion Renderer 路径触摸事件入口 |
| `ets/compose/ArkUIView.ets` | 互操作视图触摸事件处理 + 坐标变换 |
| `ets/compose/TouchEventUtils.ets` | 触摸事件坐标变换工具 |
| `cpp/arkui_view_controller.cpp` | C++ NAPI 桥接层 |
| `ComposeArkUIViewContainer.kt` | Kotlin 侧事件接收 + 策略分发 |
| `FusionRendererStrategyImpl.kt` | Fusion Renderer 输入策略 |
| `SkiaRendererStrategyImpl.kt` | SkiaRender 输入策略 |
| `ComposeSceneMediator.ohos.kt` | 事件转换核心（OHOS→Compose） |
| `PointerInputEventProcessor.kt` | Compose 通用事件处理（命中测试+分发） |

---

## 七、一次完整触摸操作的时序示例

以用户**点击一个按钮**为例：

```
T=0ms  用户手指触碰屏幕
       → OHOS 生成 TouchEvent{type=Down, touches=[{id=0,x=150,y=300}]}
       → ArkTS .onTouch() 捕获
       → NAPI 传递到 Kotlin
       → FusionRendererInputStrategy: isActive()=true ✓
       → ComposeSceneMediator.sendPointerEvent():
           rawTouchType=0 → PointerEventType.Press
           getChangedPointers(): [{id=0, position=Offset(450, 900)}]  (density=3)
           activeChangedPointers = {0: pointer}
           GC 抑制启动
       → scene.sendPointerEvent(Press, pointers, timeMillis, nativeEvent)
       → PointerInputEventProcessor.process():
           hitTest → 找到 Button 组件
           addHitPath → 记录分发路径
           dispatchChanges → Button 的 pointerInput 接收到 Press
       → detectTapGestures: 记录按下位置，启动超时计时器

T=50ms 用户手指未移动就抬起
       → OHOS 生成 TouchEvent{type=Up, touches=[{id=0,x=150,y=300}]}
       → 同样的传递链路...
       → ComposeSceneMediator: PointerEventType.Release
           GC 抑制停止
       → detectTapGestures:
           检查: 按下时间 < 500ms ✓
           检查: 位移距离 < 8dp ✓
           → 判定为"点击"手势，触发 onTap(offset) 回调
```
