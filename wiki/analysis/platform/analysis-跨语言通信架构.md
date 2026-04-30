---
type: analysis
created: 2026-04-27
updated: 2026-04-27
sources:
  - raw/ComposeUI与ArkUI混排原理.md
  - raw/Compose_OHOS_手势事件处理剖析.md
tags:
  - 跨语言
  - NAPI
  - Messenger
  - ArkTS
  - Kotlin
  - C++
  - 桥接
related:
  - "[[Messenger通信机制]]"
  - "[[手势事件处理机制]]"
  - "[[三明治混排结构]]"
  - "[[analysis-DragAndDrop在OHOS平台的实现]]"
  - "[[融合渲染架构]]"
  - "[[analysis-两种渲染路径的混排机制对比]]"
---

# 跨语言通信架构

本分析综合 Messenger 通信、手势事件传递、DragAndDrop、三明治混排等跨语言交互场景，提炼 CMP 中 Kotlin/C++/ArkTS 三语言通信的统一模式与差异。

## 一、三种通信机制

CMP 中三语言交互通过三种机制实现，各有适用场景：

| 机制 | 通道 | 方向 | 数据格式 | 适用场景 |
|------|------|------|---------|---------|
| **NAPI 直接调用** | napi_value 参数传递 | ArkTS → C++ → Kotlin | C 结构体 / napi_value | 高频、低延迟（触摸、渲染回调） |
| **Messenger JSON** | libcompose_arkui_utils.so | 双向 | JSON 字符串 | 低频、结构化数据（拖拽状态、配置） |
| **KN cinterop** | Kotlin/Native 编译时绑定 | Kotlin → C/C++ | C 函数签名 | Kotlin 调用 C++ API（渲染库） |

## 二、NAPI 直接调用——高频场景

### 2.1 调用链路

```
ArkTS: controller.dispatchTouchEvent(e, true)
  ↓ napi_call_function
C++:   ArkUIViewController_dispatchTouchEvent(controller, nativeTouchEvent, ignoreInteropView)
  ↓ KN 导出函数调用
Kotlin: ComposeArkUIViewContainer.dispatchTouchEvent(nativeTouchEvent, ignoreInteropView)
```

### 2.2 特征

- **同步调用**：ArkTS 调用阻塞等待 Kotlin 返回 Boolean（事件是否消费）
- **零拷贝**：napi_value 直接传递指针，不做数据序列化
- **高频**：触摸事件可达 120Hz（每帧多次 Move）
- **关键文件**：`arkui_view_controller.cpp`（所有 NAPI 函数入口）

### 2.3 使用的场景

| 场景 | ArkTS 入口 | Kotlin 落点 |
|------|-----------|------------|
| 触摸事件 | `.onTouch()` → `dispatchTouchEvent()` | `ComposeArkUIViewContainer.dispatchTouchEvent()` |
| 渲染回调 | `onDraw()` → `onDrawC()` | `ControllerManager.renderNodeDraw()` |
| 尺寸变化 | `onAreaChange()` → `reSize()` | `ComposeArkUIViewContainer.onSurfaceChanged()` |
| 页面生命周期 | `aboutToAppear()` → `initOHRenderNode()` | `ComposeArkUIViewContainer.initOHRenderNode()` |
| 创建 NativeRoot | `createNativeRoot()` | `ComposeArkUIViewController` 构造 |

### 2.4 NAPI 函数命名约定

```
ArkTS 导入:  import { funcName } from 'libentry.so'  或  from 'libcompose_arkui_utils.so'
C++ 导出:    napi_value funcName(napi_env env, napi_callback_info info)
Kotlin 导出: @CName("funcName") fun funcName(...)
```

## 三、Messenger JSON——结构化通信

### 3.1 架构

```
Kotlin                              ArkTS
┌──────────────┐                  ┌──────────────┐
│ Messenger    │ ── JSON ──────→  │ msgService   │
│ .sendMessage │                  │ .onMessage() │
│              │ ←── JSON ──────  │              │
│ .onMessage() │                  │ .sendMessage │
└──────────────┘                  └──────────────┘
         ↑↓                              ↑↓
    libcompose_arkui_utils.so       NAPI 注册回调
```

### 3.2 消息类型

| 类型 | 方向 | 用途 |
|------|------|------|
| 拖拽请求 | K→A | 启动/更新/结束拖拽 |
| 拖拽状态 | A→K | 拖拽结果通知 |
| 配置信息 | A→K | 屏幕密度、字体比例等 |
| 组件注册 | A→K | 互操作视图注册 |

### 3.3 特征

- **异步**：消息队列，不阻塞调用方
- **结构化**：JSON 格式，包含 type + payload
- **低频**：非每帧触发（拖拽、配置变更等）
- **双向**：Kotlin 和 ArkTS 都可发起

## 四、KN cinterop——Kotlin 调用 C++

### 4.1 模式

```
Kotlin: 通过 .def 文件声明 C 函数
  → cinterop 工具生成 Kotlin 绑定
  → Kotlin 代码直接调用 C 函数（无运行时桥接开销）
```

### 4.2 使用场景

| 场景 | Kotlin 调用 | C++ 实现 |
|------|-----------|---------|
| OH_Drawing API | `OH_Drawing_CanvasDrawRect(...)` | libnative_drawing.so |
| NAPI 操作 | `napi_get_value_double(...)` | libace_napi.z.so |
| 渲染库内部 | `skikobridge_set_platform_provider` | libskikobridge.so |

## 五、三种机制的选择决策

```
需要跨语言通信
│
├─ 频率？
│  ├─ 每帧多次（触摸、渲染）
│  │  └─ NAPI 直接调用（零拷贝、同步）
│  │
│  └─ 偶尔触发（拖拽、配置）
│     └─ Messenger JSON（异步、结构化）
│
├─ 方向？
│  ├─ ArkTS → Kotlin
│  │  └─ NAPI（触摸、生命周期、渲染回调）
│  │
│  ├─ 双向
│  │  └─ Messenger（拖拽协商、配置交换）
│  │
│  └─ Kotlin → C/C++
│     └─ KN cinterop（渲染 API、系统调用）
│
└─ 数据量？
   ├─ 小（坐标、标志位）→ NAPI 参数传递
   └─ 中等（拖拽数据、配置）→ JSON 序列化
```

## 六、关键约束

1. **NAPI 线程安全**：NAPI 调用必须在主线程的 napi_scope 内。`initOHRenderNode` 必须在 `aboutToAppear` 中调用就是因为需要 napi_scope。CRenderNode 通过 `napi_call_threadsafe_function_with_priority` 绕过此限制。

2. **Messenger 序列化成本**：JSON 序列化/反序列化有 GC 和解析开销，不适合高频场景。

3. **KN cinterop 链接约束**：`libkn.so` 的 `skikobridge_*` 符号为 undefined，运行时依赖 `libskikobridge.so` 正确链接。若链接缺失会导致 `SIGSEGV(SEGV_ACCERR)`。

4. **导入约束**：应用代码不能直接 import `libcompose_arkui_utils.so`，必须通过 `compose.har` 的 `Index.ets` re-export 后从 `'compose'` 导入。

## 来源

- [[src-ComposeUI与ArkUI混排原理]] — 互操作桥接的双层架构
- [[src-Compose_OHOS_手势事件处理剖析]] — 触摸事件的六阶段跨语言传递
- [[analysis-DragAndDrop在OHOS平台的实现]] — 拖拽场景的 Messenger + NAPI 组合使用
- [[analysis-两种渲染路径的混排机制对比]] — 三明治混排中的跨语言交互
