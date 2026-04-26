# OHOS SkiaRenderer 渲染管线设计文档

## 1. 背景：为什么 OHOS 不使用 SkiaLayer

在其他 Compose 平台（Desktop/macOS/iOS/Android）上，`SkiaLayer` 是 Skiko 提供的统一的渲染层抽象，负责：

| 能力 | Desktop/macOS/iOS 的 SkiaLayer |
|------|------|
| 创建 GPU 渲染上下文 | Metal/OpenGL |
| 提供绘制画布 | Skia `Canvas` |
| 管理帧循环 | VSync 回调 / 定时器 |
| 处理输入事件 | 鼠标/触控 |
| 附加到平台容器 | NSView / UIView / SurfaceView |

OHOS 上 `SkiaLayer` 是空壳实现（所有方法返回 `TODO()` 或空操作），原因是 OHOS 的渲染架构与上述平台根本不同——OHOS 使用 **XComponent** 作为原生渲染容器，通过 **EGL + OpenGL ES** 管理渲染表面，这套机制无法映射到 SkiaLayer 的单一类设计中。

OHOS 将 SkiaLayer 的职责拆散到了四层中，由不同的类协作完成：

| 能力 | OHOS SkiaRenderer 的实现 |
|------|------|
| 创建渲染表面 | **`XComponentRender`**（C++，管理 EGL 上下文） |
| Skia 渲染管线 | **`ComposeSceneRender`**（Kotlin，管理 Skia Surface） |
| 帧循环 | **`BasicArkUIViewController.onFrame()`**（VSync 回调） |
| 输入事件 | **`SkiaRenderCompose.ets`** 中 XComponent 的 `onTouch` |
| 平台容器 | **`SkiaRenderCompose.ets`** 中 XComponent 组件 |
| 尺寸感知 | **`ComposeSizeProxy`**（EGL surface → @State 变量迂回路径） |

---

## 2. 整体架构

```
┌─ ArkTS 层 ─────────────────────────────────────────────────┐
│  SkiaRenderCompose.ets                                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ XComponent (id, type=TEXTURE, libraryname)             │ │
│  │   ├── 提供 OH_NativeXComponent（渲染窗口）             │ │
│  │   ├── onTouch → controller.dispatchTouchEvent()        │ │
│  │   └── VSync → OnFrameCallbackCB → controller.onFrame()│ │
│  │                                                        │ │
│  │ ComposeSizeProxy（EGL 尺寸 → @State xComponentWidth）  │ │
│  │ NodeContainer (backRootView / foreRootView)            │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
        ↕ NAPI
┌─ C++ 层 ───────────────────────────────────────────────────┐
│  XComponentRender                                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ OH_NativeXComponent → EGLNativeWindowType              │ │
│  │ eglDisplay + eglConfig (static, 进程共享)              │ │
│  │ eglSurface + eglContext (per instance)                 │ │
│  │                                                        │ │
│  │ EglInit(window)     — 创建 EGL Surface 和 Context     │ │
│  │ EglPrepareDraw()    — eglMakeCurrent                   │ │
│  │ EglFinishDraw()     — eglSwapBuffers                   │ │
│  │ RegisterFrameCallback() — 注册 VSync 帧回调           │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  XComponentHolder (单例)                                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 管理 XComponentRender 实例和 ArkUIViewController 映射  │ │
│  │ InitXComponent()   — 从 ArkTS 侧初始化                │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
        ↕ JNI / Kotlin-Native
┌─ Kotlin 层 ────────────────────────────────────────────────┐
│  ComposeArkUIViewContainer (策略持有者)                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 持有 6 个策略接口：                                    │ │
│  │   SurfaceLifecycleHandler → SkiaRendererSurface...     │ │
│  │   FrameDispatcher         → SkiaRendererFrameDisp...   │ │
│  │   DrawPipeline            → SkiaRendererDrawPipeline   │ │
│  │   InputStrategy           → SkiaRendererInputStra...   │ │
│  │   ContentBindingStrategy  → SkiaRendererContentBi...   │ │
│  │   MediatorRenderDelegate  → SkiaRendererMediatorDe...  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ComposeSceneMediator (场景中介)                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 管理 ComposeScene 生命周期                              │ │
│  │ setContent() — 绑定 @Composable 内容                   │ │
│  │ setSize()    — 设置渲染尺寸                            │ │
│  │ onDraw()     — 委托给 MediatorRenderDelegate           │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ComposeSceneRender (Skia 渲染管线) ← 最接近 SkiaLayer 的类 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ DirectContext.makeGL()     — OpenGL GPU 上下文         │ │
│  │ BackendRenderTarget (FBO)  — 渲染目标                  │ │
│  │ Surface (Skia Surface)     — 绘制表面                  │ │
│  │ draw(timestamp)            — 执行绘制                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ComposeScene (场景)                                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ render(canvas, timestamp) — Compose UI 绘制入口        │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

---

## 3. 策略模式隔离架构

SkiaRenderer 路径通过 **6 个策略接口** 与 FusionRenderer 路径隔离，接口定义在 `RendererBackend.kt`：

### 3.1 策略接口定义

```kotlin
// RendererBackend.kt

interface SurfaceLifecycleHandler {
    fun onSurfaceCreated(component: OHNativeXComponent, width: Int, height: Int)
    fun onSurfaceChanged(width: Int, height: Int)
    fun onSurfaceDestroyed()
}

interface FrameDispatcher {
    fun invalidate()
    fun onFrame(timestamp: Long, targetTimestamp: Long)
    fun onIdle(timeLeft: Long)
    fun dispose()
    fun shouldRunBackgroundHeartbeat(): Boolean  // SkiaRenderer=true
    fun requiresPostDrawFlush(): Boolean          // SkiaRenderer=true (需 EGL flush)
}

interface DrawPipeline {
    fun onDraw(canvas: Canvas?, id: String, timestamp: Long, targetTimestamp: Long)
}

interface InputStrategy {
    fun shouldDispatchTouch(): Boolean
    fun onDispatchTouch(nativeTouchEvent: napi_value): Boolean
}

interface ContentBindingStrategy {
    fun onMediatorCreated(mediator: ComposeSceneMediator, content: @Composable () -> Unit)
    fun onFirstSurfaceChanged(mediator: ComposeSceneMediator, content: @Composable () -> Unit)
}

interface MediatorRenderDelegate {
    fun setRenderSize(width: Int, height: Int)
    fun draw(canvas: Canvas?, id: String, timestamp: Long, targetTimestamp: Long)
    fun dispose()
    fun resetSurface()
    fun close()
}
```

### 3.2 SkiaRenderer 策略实现要点

| 策略 | SkiaRenderer 特有行为 |
|------|----------------------|
| `SurfaceLifecycleHandler` | onSurfaceCreated 时立即创建 mediator 和设置尺寸 |
| `FrameDispatcher` | `shouldRunBackgroundHeartbeat=true`（XComponent VSync 需要后台心跳）、`requiresPostDrawFlush=true`（需 `EglFinishDraw()`） |
| `DrawPipeline` | 检查 `nativeSurfaceHasBeenDestroyed` 标志防止销毁后绘制 |
| `InputStrategy` | 分发触摸前检查 EGL 是否就绪（`isEglReady()`） |
| `ContentBindingStrategy` | `onMediatorCreated` 时立即 `setContent()`（不等 Surface 变化） |
| `MediatorRenderDelegate` | 持有 `ComposeSceneRender` 实例，管理渲染尺寸和绘制 |

### 3.3 与 FusionRenderer 的关键差异

| 维度 | SkiaRenderer | FusionRenderer |
|------|-------------|----------------|
| Surface 来源 | XComponent + EGL | RenderNode (OHOS RenderService) |
| 帧循环 | XComponent VSync + 后台心跳 | `postFrameCallback` + willDraw 事件 |
| 绘制后操作 | `EglFinishDraw()`（`eglSwapBuffers`） | 无需 flush（系统自动合成） |
| 内容绑定时机 | mediator 创建时立即 `setContent()` | 延迟到首次 `onSurfaceChanged` |
| 后台心跳 | 需要 | 不需要 |
| 尺寸通知 | `ComposeSizeProxy`（迂回路径） | `onAreaChange` 直接传递 |

---

## 4. 核心类详解

### 4.1 ComposeSceneRender — Skia 渲染管线管理

**文件**: `ui/src/ohosArm64Main/kotlin/.../scene/ComposeSceneRender.ohos.kt`

这是 OHOS 上最接近 SkiaLayer 的类，负责 Skia 渲染管线的完整管理。

**核心资源**:

```kotlin
class ComposeSceneRender(val onDraw: (Canvas, Long) -> Unit) {
    private var directContext: DirectContext? = null      // GPU 上下文
    private var renderTarget: BackendRenderTarget? = null  // FBO 渲染目标
    private var surface: Surface? = null                  // Skia 绘制表面
    private var surfaceCanvas: Canvas? = null             // Compose 画布
}
```

**Surface 创建流程** (`ensureSurface()`):

```
DirectContext.makeGL()
  → BackendRenderTarget.makeGL(width, height, sampleCnt=1, stencilBits=0, FBO=0, format=0x8058)
    → Surface.makeFromBackendRenderTarget(
        directContext, renderTarget,
        SurfaceOrigin.BOTTOM_LEFT,   ← OpenGL 坐标系原点在左下
        SurfaceColorFormat.RGBA_8888,
        ColorSpace.sRGB
      )
      → surfaceCanvas = surface.canvas.asComposeCanvas()
```

**三种绘制模式**:

| 方法 | 场景 | 流程 |
|------|------|------|
| `draw(timestamp)` | 常规渲染 | ensureSurface → clear → onDraw → flush |
| `drawWithCanvas(canvas, timestamp)` | 外部提供画布 | 直接 onDraw |
| `drawByPictureRecorder(timestamp)` | 需录制模式 | PictureRecorder 录制 → Surface 回放 → flush |

**绘制流程**:

```
draw(timestamp)
  1. ensureSurface()                    — 惰性创建 GPU 上下文和 Surface
  2. surface.canvas.clear(TRANSPARENT)  — 清屏（避免某些设备拖影）
  3. surface.canvas.resetMatrix()       — 重置变换矩阵
  4. onDraw(surfaceCanvas, timestamp)   — 回调 ComposeScene.render()
  5. directContext.flush()              — 刷新 GPU 命令
```

### 4.2 XComponentRender — EGL 上下文管理

**文件**: `ui-arkui/.../cpp/compose/xcomponent_render.h/.cpp`

C++ 层负责管理 EGL 渲染上下文，与 OHOS 的 `OH_NativeXComponent` 交互。

**核心 EGL 资源**:

```cpp
class XComponentRender {
    OH_NativeXComponent *const component;  // OHOS 原生 XComponent
    ArkUIViewController *controller;        // Kotlin 层控制器

    EGLNativeWindowType eglWindow;          // 原生窗口
    EGLSurface eglSurface = EGL_NO_SURFACE; // EGL 绘制表面
    EGLContext eglContext = EGL_NO_CONTEXT;  // EGL 上下文
    static EGLDisplay eglDisplay;            // EGL 显示连接（进程共享）
    static EGLConfig eglConfig;              // EGL 帧缓冲配置（进程共享）
};
```

**关键方法**:

| 方法 | 作用 | EGL 调用 |
|------|------|---------|
| `EglInit(window)` | 初始化 EGL 环境 | `eglCreateWindowSurface` + `eglCreateContext` |
| `EglPrepareDraw()` | 准备绘制 | `eglMakeCurrent` |
| `EglFinishDraw()` | 完成绘制 | `eglSwapBuffers` |
| `RegisterFrameCallback()` | 注册 VSync 帧回调 | `OH_NativeXComponent_RegisterOnFrameCallback` |

**帧回调注册**:

```
RegisterFrameCallback()
  → OH_NativeXComponent_RegisterOnFrameCallback(component, &callback)
  → callback.OnFrameCallbackCB(component, timestamp, targetTimestamp)
    → controller->onFrame(timestamp, targetTimestamp)
```

### 4.3 SkiaRendererMediatorDelegate — 渲染代理

**文件**: `ui/src/ohosMain/skia/kotlin/.../platform/SkiaRendererStrategyImpl.kt`

连接 `ComposeSceneMediator` 和 `ComposeSceneRender` 的桥梁：

```kotlin
class SkiaRendererMediatorDelegate(
    sceneProvider: () -> ComposeScene,
    private val messenger: MessengerImpl
) : MediatorRenderDelegate {
    private val render: ComposeSceneRender by lazy {
        ComposeSceneRender(onDraw = sceneProvider()::render)
    }

    override fun draw(canvas: Canvas?, id: String, timestamp: Long, targetTimestamp: Long) {
        render.draw(targetTimestamp)  // 直接调用 ComposeSceneRender.draw()
    }

    override fun setRenderSize(width: Int, height: Int) {
        render.setSize(width, height)
    }
}
```

注意：`draw()` 方法**忽略了传入的 canvas 参数**，因为 ComposeSceneRender 自己管理 Surface 和 GPU 上下文。

---

## 5. 完整帧渲染流程

```
用户操作 / VSync
    ↓
OHOS 系统
    ↓
OnFrameCallbackCB(component, timestamp, targetTimestamp)  ← C++ 帧回调
    ↓
controller->onFrame(timestamp, targetTimestamp)            ← Kotlin 帧入口
    ↓
container.onFrame(timestamp, targetTimestamp)              ← 策略分发
    ↓
frameDispatcher.onFrame(timestamp, targetTimestamp)        ← SkiaRendererFrameDispatcher
    ↓
container.superOnFrame(timestamp, targetTimestamp)
    ↓
EglPrepareDraw()                                          ← eglMakeCurrent
    ↓
drawPipeline.onDraw(canvas, id, ts, targetTs)              ← SkiaRendererDrawPipeline
    ↓
mediator.onDraw(canvas, id, ts, targetTs)
    ↓
mediatorRenderDelegate.draw(canvas, id, ts, targetTs)      ← SkiaRendererMediatorDelegate
    ↓
ComposeSceneRender.draw(targetTimestamp)                    ← Skia 渲染
    ↓
  ensureSurface()  → DirectContext.makeGL() + Surface
  clear(TRANSPARENT) + resetMatrix()
  onDraw(surfaceCanvas, timestamp)
    ↓
  ComposeScene.render(canvas, timestamp)                    ← Compose UI 绘制
    ↓
  directContext.flush()                                     ← GPU 命令提交
    ↓
EglFinishDraw()                                            ← eglSwapBuffers
    ↓
OHOS 合成显示
```

---

## 6. 尺寸通知的迂回路径

SkiaRenderer 路径的尺寸通知比 FusionRenderer 复杂，需要通过 `ComposeSizeProxy` 迂回：

```
EGL surface resize
  → sizeChangeDispatcher.onComposeSizeChange(id, width, height)
  → messenger.send("compose.ui:sizechange", json)
  → ComposeSizeProxy (ArkTS 侧)
  → @State xComponentWidth / xComponentHeight 更新
  → XComponent 尺寸更新
```

原因是 ArkTS 层无法直接感知 EGL surface 的尺寸变化（EGL 在 C++ 层管理），必须通过 Messenger 消息通道传递到 ArkTS 层。

---

## 7. XComponent 类型选择

SkiaRenderCompose 使用 `XComponentType.TEXTURE`：

```typescript
XComponent({
    id: this.componentId,
    type: XComponentType.TEXTURE,  // 纹理模式
    libraryname: this.requireLibraryName(),
})
```

TEXTURE 模式意味着 XComponent 作为纹理层嵌入 ArkUI 组件树，支持与其他 ArkUI 组件的混合布局。

---

## 8. 关键文件索引

| 文件 | 语言 | 职责 |
|------|------|------|
| `ui/src/ohosArm64Main/.../scene/ComposeSceneRender.ohos.kt` | Kotlin | Skia 渲染管线（GPU 上下文 + Surface + 绘制） |
| `ui/src/ohosMain/skia/.../platform/SkiaRendererStrategyImpl.kt` | Kotlin | 6 个策略实现 |
| `ui/src/ohosArm64Main/.../platform/RendererBackend.kt` | Kotlin | 策略接口定义 |
| `ui/src/ohosArm64Main/.../window/ComposeArkUIViewContainer.kt` | Kotlin | 策略持有者容器 |
| `ui-arkui/.../cpp/compose/xcomponent_render.h/.cpp` | C++ | EGL 上下文管理 |
| `ui-arkui/.../cpp/compose/xcomponent_holder.h/.cpp` | C++ | XComponent 单例管理 |
| `ui-arkui/.../ets/skiarender/Compose.ets` | ArkTS | 平台容器 + XComponent 组件 |
| `ui-arkui/.../ets/compose/ComposeSizeProxy.ets` | ArkTS | EGL 尺寸通知代理 |
| `third_party/skiko/.../ohosMain/skia/.../SkiaLayer.ohos.kt` | Kotlin | SkiaLayer 空壳实现 |
