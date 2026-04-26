# 自渲染路径 ArkUI 原生组件混排设计

## 1. 背景：为什么需要三明治结构

在 OHOS 自渲染（SkiaRenderer）路径中，Compose UI 通过 XComponent（TEXTURE 模式）获得独立的 EGL/OpenGL ES 渲染表面。XComponent 是一个独立的渲染层，ArkUI 原生组件无法直接嵌入其中。

但实际场景中，Compose 页面经常需要混合 ArkUI 原生组件，例如：
- 文本编辑的粘贴按钮（PasteButton，安全组件，免权限）
- 系统输入法、安全控件等必须使用原生实现的组件
- 已有的 ArkUI 业务组件复用

为此，框架设计了**三明治结构**（Sandwich Layout），通过多层 NodeContainer 叠放实现原生组件与 Compose 内容的混合布局。

---

## 2. 三明治结构

### 2.1 四层叠放

`SkiaRenderCompose.ets` 的 `build()` 使用 `Stack` 叠放四层：

```
┌─────────────────────────────────────────────────────────┐
│  TextToolbarOverlay                                      │  第5层：文本工具栏
│  hitTestBehavior(Transparent)                            │  （含 PasteButton）
├─────────────────────────────────────────────────────────┤
│  NodeContainer(touchableRootView)                        │  第4层：触摸事件拦截
│  + DragAndDrop 事件处理                                   │
├─────────────────────────────────────────────────────────┤
│  NodeContainer(foreRootView)                             │  第3层：前景原生组件
│  （ArkUI 原生组件放在 Compose 上面）                       │
├─────────────────────────────────────────────────────────┤
│  XComponent(TEXTURE)                                     │  第2层：Compose 渲染面
│  backgroundColor('#00000000')  透明底色                   │     EGL/GL Surface
├─────────────────────────────────────────────────────────┤
│  NodeContainer(backRootView)                             │  第1层：背景原生组件
│  （ArkUI 原生组件放在 Compose 下面）                       │     clipShape 裁剪
└─────────────────────────────────────────────────────────┘
```

### 2.2 代码实现

```typescript
// SkiaRenderCompose.ets
build() {
  Stack() {
    Stack() {
      // 第1层：背景原生组件
      NodeContainer(this.host.backRootView)
        .size({ width: '100%', height: '100%' })
        .clipShape(new RectShape({ width: this.xComponentWidth, height: this.xComponentHeight }))

      // 第2层：Compose 渲染面（透明底色）
      XComponent({
        id: this.componentId,
        type: XComponentType.TEXTURE,
        libraryname: this.requireLibraryName(),
      })
        .backgroundColor('#00000000')
        .size({ width: '100%', height: '100%' })
        .renderFit(RenderFit.TOP_LEFT)

      // 第3层：前景原生组件
      NodeContainer(this.host.foreRootView)
        .size({ width: '100%', height: '100%' })

      // 第4层：触摸事件拦截
      NodeContainer(this.host.touchableRootView)
        .size({ width: '100%', height: '100%' })
        .onDragEnter(...)
        .onDrop(...)
    }

    // 第5层：文本工具栏
    TextToolbarOverlay({ params: this.textToolbarParams })
      .width('100%')
      .height('100%')
      .hitTestBehavior(HitTestMode.Transparent)
  }
}
```

### 2.3 三个 ArkUIRootView

```typescript
// ComposeComponentHost.ets
export class ComposeComponentHost {
  readonly touchableRootView = new ArkUIRootView();
  readonly foreRootView = new ArkUIRootView();
  readonly backRootView = new ArkUIRootView();
}
```

每个 `ArkUIRootView` 是独立的 `NodeController`，Compose 通过 `ctrl.init()` 将它们传给 Kotlin 层，Kotlin 侧按需往里面添加原生 ArkUI 节点。

---

## 3. 层选择机制

### 3.1 InteropContainer 枚举

```kotlin
// ArkUIView.ohos.kt:92
enum class InteropContainer { BACK, FORE, TOUCHABLE }
```

### 3.2 开发者显式指定

放在哪个层**不是框架自动决定的**，而是开发者在调用时通过 `container` 参数显式选择。

**高层 API — `ArkUIView`**：
```kotlin
InternalArkUIView(
    name = "MyNativeView",
    modifier = Modifier.size(100.dp),
    container = InteropContainer.BACK  // 默认 BACK
)
```

**底层 API — `ArkUINodeHandle`**：
```kotlin
// 通用版，默认 BACK
ArkUINodeHandle(
    factory = { createNode() },
    modifier = Modifier.size(100.dp),
    container = InteropContainer.BACK  // 默认
)

// 专用的 Fore 版本
ForeArkUINodeHandle(
    factory = { createNode() },
    modifier = Modifier.size(100.dp)
    // 内部强制 container = InteropContainer.FORE
)
```

### 3.3 选择逻辑

```kotlin
// ArkUINativeView.ohos.kt:124
val interopContainer = when (container) {
    InteropContainer.BACK      → LocalBackArkUINativeInteropContainer.current      // → backRootView
    InteropContainer.FORE      → LocalForeArkUINativeInteropContainer.current      // → foreRootView
    InteropContainer.TOUCHABLE → LocalTouchableArkUINativeInteropContainer.current // → touchableRootView
}
```

三个 `CompositionLocal` 在框架初始化时注入，分别对应三个 `ArkUIRootView`。

### 3.4 各层对比

| `container` 值 | 去向 | 视觉位置 | 挖洞 | 典型场景 |
|---|---|---|---|---|
| `BACK`（默认） | backRootView | Compose 下面 | 自动在 Compose 上挖透明洞 | 大部分原生组件 |
| `FORE` | foreRootView | Compose 上面 | 不需要 | 安全组件、输入法 |
| `TOUCHABLE` | touchableRootView | 最顶层 | 不需要 | 仅拦截事件的透明层 |

---

## 4. BACK 层的挖洞机制

选择 `BACK` 的组件有一个关键的额外操作——在 Compose 画布上画一个**透明洞**：

```kotlin
// ArkUINativeView.ohos.kt:165-169
InteropContainer.BACK -> it.drawBehind {
    drawRect(Color.Transparent, blendMode = BlendMode.DstAtop)
}
```

### 4.1 为什么需要挖洞

XComponent 的 Compose 渲染面是不透明的。BACK 层的原生组件在 XComponent 下面，如果不挖洞，Compose 内容会完全遮住它。`drawRect(Color.Transparent, blendMode = BlendMode.DstAtop)` 在原生组件的精确位置将 Compose 像素擦除为透明，让下面的原生组件露出来。

### 4.2 挖洞是精确的

透明洞**只在该组件的精确位置和尺寸范围内**。其他区域仍然是 Compose 的不透明内容，可以正常覆盖或与原生组件并列。

---

## 5. 为什么默认值是 BACK

### 5.1 BACK 让原生组件行为像普通 Compose 子组件

```kotlin
Column {
    Text("标题")          // Compose
    ArkUIView(...)        // 原生组件，默认 BACK
    Text("底部")          // Compose
}
```

**BACK 效果**：

```
foreRootView:  空
XComponent:    [标题] [透明洞→原生按钮] [底部]
backRootView:  [原生按钮]
```

原生按钮被上下两个 Compose Text 包围，可以被其他 Compose 内容（如底部 Text、弹窗、菜单、动画）正常覆盖。

**如果默认是 FORE**：

```
foreRootView:  [原生按钮]                    ← 永远在最上面
XComponent:    [标题]        [底部]           ← "底部"被原生按钮挡住
backRootView:  空
```

原生按钮始终盖在所有 Compose 内容之上，无法被弹窗、菜单、动画等覆盖。

### 5.2 没有覆盖能力的后果

如果原生组件永远在最上层（FORE），以下场景全部失效：

| 场景 | 问题 |
|------|------|
| Dialog / 弹窗 | 原生组件穿透弹窗，露在外面 |
| 下拉菜单 / Popup | 菜单被原生组件遮挡 |
| LazyList 滚动 | 原生组件不跟随 Z 序，始终浮在上面 |
| 动画覆盖 | 原生组件从动画下方"刺出来" |
| Snackbar / Toast | 被原生组件挡住 |

### 5.3 一句话

默认 BACK 确保原生组件是 Compose UI 树的"一等公民"——能被覆盖、能被遮挡、Z 序由 Compose 布局决定。FORE 是"钉在最上层"的特殊需求，属于例外情况。

---

## 6. PasteButton 免权限集成

### 6.1 安全组件机制

`PasteButton` 是 OHOS 的安全控件（Security Component），特殊性在于：

1. **用户主动点击** = 系统确认用户意图，相当于"授权"
2. 系统在 `onClick` 的 `result` 参数中发放**临时授权令牌**
3. 持有令牌才能访问剪贴板，令牌有效期很短
4. 应用**不需要在 manifest 中声明 `ohos.permission.READ_PASTE`**

### 6.2 实现

`TextToolbar.ets` 中，粘贴按钮使用 `PasteButton`，其他按钮（Cut、Copy、SelectAll）是普通 `Button`：

```typescript
if (this.params?.onPaste) {
  Stack() {
    PasteButton({ text: PasteDescription.PASTE, buttonType: ButtonType.Normal })
      .onClick((event, result) => {
        this.params?.onPaste?.()  // result 包含系统授权的临时凭证
      })
  }
  .onTouch((event) => {
    event.stopPropagation()  // 阻止触摸事件穿透到下层
  })
}
```

PasteButton 必须放在 foreRootView（Compose 上层），因为它需要系统直接处理点击事件进行授权。

### 6.3 通信链路

工具栏的显示/隐藏通过 Messenger JSON 通道完成：

```
Kotlin 层（Compose 文本选中）
  → messenger.send("compose.ui.TextToolbar:showMenu",
                   "left,top,right,bottom,Cut,Copy,Paste")
    → ArkTS 层 TextToolbar 收到消息
      → onShow(params) 回调
        → @State textToolbarParams 更新
          → TextToolbarOverlay 重新渲染

用户点击 PasteButton
  → onClick → onPaste()
    → messenger.send("compose.ui.TextToolbar:showMenu.onPaste", "")
      → Kotlin 层收到，执行粘贴逻辑（此时有系统临时授权）
```

---

## 7. 关键文件索引

| 文件 | 语言 | 职责 |
|------|------|------|
| `ui-arkui/.../ets/skiarender/Compose.ets` | ArkTS | 三明治 Stack 结构、XComponent 配置 |
| `ui-arkui/.../ets/compose/ComposeComponentHost.ets` | ArkTS | 三个 ArkUIRootView 持有者 |
| `ui-arkui/.../ets/compose/ArkUIRootView.ets` | ArkTS | NodeController 实现 |
| `ui-arkui/.../ets/compose/texttoolbar/TextToolbar.ets` | ArkTS | 文本工具栏 + PasteButton |
| `ui/.../interop/ArkUIView.ohos.kt` | Kotlin | ArkUIView 互操作入口、InteropContainer 枚举 |
| `ui/.../interop/arkc/ArkUINativeView.ohos.kt` | Kotlin | 底层 ArkUI 节点互操作、层选择逻辑、挖洞机制 |
| `ui/.../interop/arkc/ArkUINativeInteropContainer.kt` | Kotlin | 原生组件容器，管理 add/remove 和 Z 序 |
| `ui/.../interop/LocalInteropContainer.ohos.kt` | Kotlin | 三个 CompositionLocal 注入 |
