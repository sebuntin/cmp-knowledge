# **混排原理**

# **ArkUIView Compose 混排原理与示例说明**

本文梳理 `androidx.compose.ui.interop.ArkUIView.ohos.kt` 中 `InternalArkUIViewV2` 的关键流程，并结合 `composeApp/src/ohosArm64Main/kotlin/com/tencent/compose/sample/video/VideoPlayer.kt` 演示 ArkUI 视图与 Compose 内容混排的使用方式。

![https://docimg3.docs.qq.com/image/AgAAEbEDSvoo7Bp4XMtLtrCjozU08ivi.png?w=2226&h=1618](https://docimg3.docs.qq.com/image/AgAAEbEDSvoo7Bp4XMtLtrCjozU08ivi.png?w=2226&h=1618)

------

## **1.** `InternalArkUIViewV2` **结构概览（Kotlin 层）**

源文件：`compose/ui/ui/src/ohosArm64Main/kotlin/androidx/compose/ui/interop/ArkUIView.ohos.kt`

核心入口：`@Composable internal fun InternalArkUIViewV2(...)`（127-307 行）

### **1.1 主要步骤**

1. **初始化 interop 上下文**

```kotlin
val interopContext = LocalArkUIInteropContext.current
val embeddedInteropComponent = remember { EmbeddedInteropForArkUINode(...) }
```

`EmbeddedInteropForArkUINode` 负责管理 ArkUI 的 `wrappingView/baseView`、生命周期与更新逻辑。

2. **Place + MeasurePolicy**

- 使用 `Place`（Compose 自定义布局容器）包装 ArkUI 组件。
- `measurePolicy` 中会：

- 将 Compose 的 `Constraints` 转成 ArkUI 识别的尺寸；
- 通过 `component.measure()` 获取 ArkUI 测量结果；
- 对 wrap content / adaptive 高度做约束；
- 更新 `componentSize` 以记录当前布局大小。

3. **全局坐标与指针同步**

- `Modifier.onGloballyPositioned`：计算 ArkUI 视图在 Root 中的 `Offset`，用于指针事件偏移。
- `pointerInteropFilterV2(container, lastOffset)`：使用扩展的指针过滤器，将 Compose 触摸事件转发到 ArkUI。

4. **绘制层**

- `drawLayer` 中调用 `AdaptiveCanvas.drawInteropLayer(baseRenderNode, wrappingViewHandle, density)`，把 ArkUI RenderNode 绘制到 Compose Canvas。

5. **生命周期管理**

- `DisposableEffect` 内创建 `ArkUIView` 并设置 `onCreate`/`onRelease`：
  - `embeddedInteropComponent.ensureWrappingView()` 懒创建 ArkUI native 视图；
  - `interopContext.deferAction(VIEW_ADDED)` / `VIEW_REMOVED` 负责将 native 节点挂载/卸载到 ArkUI 树。
- `LaunchedEffect(background)`、`LaunchedEffect(parameter)` 分别更新背景色与参数。
- `SideEffect` 更新 `updater`，保证在每次重组后仍能同步 Compose 属性到 ArkUI。

6. **测量回流机制**

- `ArkUIView` 的 `onMeasured` 回调若检测到 ArkUI 侧尺寸变化，会 `layoutKey++` 触发 Compose 重测，确保两侧尺寸一致。

### **1.2 关键数据流**

| 参数                                | 作用                                               |
| ----------------------------------- | -------------------------------------------------- |
| `name`                              | ArkUI 组件名，对应 ArkTS/ArkUI 端的注册组件        |
| `parameter`                         | `JsObject`，用于向 ArkTS 组件传递属性              |
| `updater / composeParameterUpdater` | Compose -> ArkUI 属性同步                          |
| `adaptiveParams`                    | 控制最大高度、translate 等适配策略                 |
| `embeddedInteropComponent`          | 封装 ArkUI View、RenderNode、LayoutNode 等桥接逻辑 |

------

## **2.** `VideoPlayer` **Demo（Compose 用法）**

文件：`composeApp/src/ohosArm64Main/kotlin/com/tencent/compose/sample/video/VideoPlayer.kt`

```
package com.tencent.compose.video

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.interop.ArkUIView
import androidx.compose.ui.napi.js

@Composable
actual fun VideoPlayer(
	modifier: Modifier,
	url: String
) {
	ArkUIView(
		name = "video",
		modifier = modifier,
		parameter = js {
		"src"(url)
		"autoplay"(true)
		"controls"(true)
		}
	)
}
```

说明：

- 通过 `ArkUIView` 高阶 API（实际内部会选择 `InternalArkUIViewV2`），直接在 Compose 中声明一个 ArkUI “video” 组件。
- `parameter = js { ... }` 使用 `kotlinx.js` 构造 `JsObject`，传入视频源、自动播放、控制条等参数。
- 配合 Compose 的 `modifier`，即可在布局中自由摆放 ArkUI video 视图，实现混排。

------

## **3. 混排要点与最佳实践**

1. **保证 ArkUIView 名称与 ArkTS 注册一致**：`name = "video"` 需要在 ArkTS 侧有对应 Builder。
2. **参数更新**：`parameter` 变化会触发 `LaunchedEffect(parameter)` 重新下发；复杂场景可以自定义 `update` / `updater`。
3. **尺寸同步**：若 ArkUI 组件内部自适应尺寸，务必实现 `onMeasured` 并在尺寸变化时刷新 Compose 布局。
4. **指针/触摸**：`pointerInteropFilterV2` 会带上 `Offset`，保证 Compose 坐标到 ArkUI 坐标的转换正确，必要时在 ArkTS 侧也要处理 `offsetTouchEventLocalPosition`。
5. **性能建议**：避免频繁创建/销毁 `ArkUIView`，可通过 `remember` 对象复用；同时注意在 `DisposableEffect` 中释放 native 资源。

------

## **4. Native / C++ 侧对应逻辑**

### **4.1 目录与角色**

路径：`compose/ui/ui-arkui/src/ohosArm64Main/cpp/compose/src/main/cpp/compose/interop`

| 文件                                     | 作用                                                         |
| ---------------------------------------- | ------------------------------------------------------------ |
| `oh_native_interop_wrap_node.{h,cpp}`    | `InteropWrapView`，负责 ArkUI mixed node 创建、attach/detach、背景色/布局同步 |
| `oh_interop_touch_event_handler.{h,cpp}` | Compose → ArkUI 指针事件处理器，支持多节点转发、坐标校准     |

### **4.2** `InteropWrapView` **细节**

- **创建**：通过 FFI 函数 `androidx_compose_ui_arkui_utils_create_mixed_view_with_js` 调用 `InteropWrapView::CreateMixedNode`，一次性获得 wrapping node、base render node、JS ArkUIView 引用。
- **生命周期管理**：
  - `AttachToParent()` 调用 ArkUI `NativeNodeApi::addChild` 将 wrapping node 加入自定义节点树。
  - `DetachFromParent()` 从父节点移除；若 PictureRecorder 仍持有 render node，会交给 `OHRenderNodeManager::DestroyMixedNode` 做延迟销毁。
  - `OHRenderNodeManager` 维护 `m_interopWrapViews`、`m_pendingDestroyViews`，与 Compose 层的 add/remove/hierarchy 事件对应。
- **绘制**：`OHNativeCanvasProxy::drawInteropLayer` 会把 `BaseRenderNode` 绘制到 Compose Canvas，并根据 `wrapView->markRecordedInPicture` 处理 PictureRecorder 的引用。
- **属性更新**：背景色等接口通过 `androidx_compose_ui_arkui_utils_set_background_color` 等 FFI 暴露，Kotlin 层 `EmbeddedInteropForArkUINode` 调用。

### **4.3 指针事件链路**

1. `pointerInteropFilterV2(embeddedInteropComponent.container, lastOffset)` → Kotlin 端 `ArkUIViewContainer.dispatchTouchEventV2`。
2. Native `oh_interop_touch_event_handler` 维护一个或多个 `InteropWrapView`，`dispatchTouchEventV2` 会根据提供的 offset 进行事件分发。
3. ArkTS (`ArkUIView.ets`) 中 `onTouchEventV2(e, x, y)` 将 Compose 的 root 坐标转换为本地坐标（`offsetTouchEventLocalPosition(event, { x: -x, y: -y })`），然后 `postTouchEvent` 到 ArkUI builder。

### **4.4 其它配套组件**

- **FFI & RenderManager**：`oh_native_canvas_export.{h,cpp}` 暴露 `drawInteropLayer`、`attach/detach` 等 C 接口，供 Kotlin 使用；`OHRenderNodeManager` 负责 mixed node 的注册、销毁、env 获取。
- **PictureRecorder / Canvas**：在 Compose → ArkUI 绘制时，需要同步 RenderNode 在 PictureRecorder 中的生命周期（`markRecordedInPicture` 等），避免被过早释放。
- **ArkTSBridge**：提供 dpi/scale、window metrics、JS binding 等信息，供 touch/布局等逻辑使用。

------

## **5. 参考文件**

- Kotlin 层：`androidx/compose/ui/interop/ArkUIView.ohos.kt`
- C++ 层：`compose/ui/ui-arkui/.../compose/interop/*.cpp`
- Demo：`composeApp/src/ohosArm64Main/kotlin/com/tencent/compose/sample/video/VideoPlayer.kt`

通过 Kotlin + Native 两侧的协作，Compose 可以嵌入 ArkUI 原生组件，实现绘制 指针 生命周期的完整混排链路，同时复用 Compose 的状态与布局体系。