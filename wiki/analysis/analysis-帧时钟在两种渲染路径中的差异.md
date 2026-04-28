---
type: analysis
created: 2026-04-27
updated: 2026-04-27
tags:
  - 帧时钟
  - BroadcastFrameClock
  - VSync
  - FusionRenderer
  - SkiaRenderer
  - 帧循环
  - 对比分析
related:
  - "[[帧时钟协作机制]]"
  - "[[融合渲染架构]]"
  - "[[SkiaRenderer渲染管线]]"
sources:
  - raw/CMP帧时钟协作机制.md
  - raw/OHOS SkiaRenderer渲染管线设计.md
  - raw/融合渲染整体方案总结.md
---

# 帧时钟在两种渲染路径中的差异

## 研究问题

两种渲染路径共用同一套帧时钟调度系统（BaseComposeScene.render() 六阶段），但帧的触发方式、后台行为、绘制前后处理完全不同。这些差异如何影响帧时钟系统的行为？

## 结论

帧时钟的"内核"——两级 BroadcastFrameClock 级联、FlushCoroutineDispatcher 双路径、render() 六阶段——在两种路径中完全相同。差异全部集中在帧的"外壳"：谁来触发 render()、绘制前后需要什么额外操作、后台空闲时如何维持帧脉冲。

## 按需 VSync 机制

两条路径都有独立的"按需 VSync"系统，避免空闲时持续消耗资源。

### FusionRenderer：UIContext.postFrameCallback（one-shot）+ DisplaySync（持续）

FusionRenderer 有两种 VSync 注册方式，服务于不同场景：

**1. One-shot 帧请求（postFrameCallback）**

```
invalidate()
  → FusionRendererFrameDispatcher.invalidate()
    → container.fusionRendererInvalid = true  // 防重复标志
    → context.frameMgr?.postFrameCallback()
      → RenderFrameManager (ArkTS)
        → UIContext.postFrameCallback(RenderFrameCallback)  // 一次性回调
          → 下一个 VSync 到达
            → RenderFrameCallback.onFrame(nanos)
              → ... → onFrame → notifyRedraw → RenderNode draw 回调 → onDraw → render()
```

- `UIContext.postFrameCallback()` 是 one-shot API：注册一次，触发一次后自动移除
- `fusionRendererInvalid` 标志防止同帧内多次 `postFrameCallback`：只有从 false→true 时才请求
- 每次 `onFrame` 执行后将 `fusionRendererInvalid` 重置为 false，允许下一次请求

**2. 持续帧回调（DisplaySync enable/disable）**

```
enableFrameCallback(id)
  → RenderFrameManager.enableFrameCallback(id)
    → nodeIdSet.add(id)
    → if (!isSyncStart) { sync.start(); isSyncStart = true }

disableFrameCallback(id)
  → RenderFrameManager.disableFrameCallback(id)
    → nodeIdSet.delete(id)
    → if (nodeIdSet.size == 0) { sync.stop(); isSyncStart = false }
```

- `RenderFrameManager` 持有 `DisplaySync` 实例（`displaySync.create()`），期望帧率 120fps
- `enableFrameCallback(id)` 启动 DisplaySync 持续回调；`disableFrameCallback(id)` 在所有节点注销后停止
- 引用计数设计：多个 RenderNode 共享同一个 DisplaySync，全部注销后才停止

### SkiaRenderer：FrameController（require/release + 50ms 延迟释放）

SkiaRenderer 通过 `FrameController` 管理底层 `OH_NativeXComponent` 帧回调的注册/注销：

```
requireFrameCallback(reason)
  → if (delayStarted.compareAndSet(1, 0))  // 取消待执行的延迟释放
      → delayJob?.cancel()
  → if (frameCallbackRegistered.compareAndSet(false, true))  // 未注册才注册
      → registerFrameCallback()
        → OH_NativeXComponent_RegisterOnFrameCallback(render, OnFrameCallbackCB)

releaseFrameCallback()
  → if (delayStarted.compareAndSet(0, 1))  // 启动延迟释放
      → delayJob = postDelayed(50ms) {
          → OH_NativeXComponent_UnregisterOnFrameCallback(render)
        }
```

关键设计：
- **50ms 延迟释放**：`releaseFrameCallback` 不立即注销，而是延迟 50ms。这段时间内如果有新的 `requireFrameCallback`（如动画连续帧），会取消延迟任务，避免注册/注销抖动
- **原子状态机**：`frameCallbackRegistered`（是否已注册）+ `delayStarted`（是否在延迟释放中）两个原子变量保证线程安全
- **多实例稳定性**：多实例场景下（`controllerId.contains("_")`）总是使用延迟释放，单实例也可能延迟
- 帧回调在 `OnSurfaceCreatedCB` 时首次注册（`OH_NativeXComponent_RegisterOnFrameCallback`），`OnSurfaceDestroyedCB` 时注销

### 按需 VSync 对比

| 维度 | FusionRenderer | SkiaRenderer |
|------|---------------|-------------|
| 底层 VSync 源 | UIContext.postFrameCallback + DisplaySync | OH_NativeXComponent FrameCallback |
| 一次性请求 | postFrameCallback（one-shot） | 无对应机制（VSync 到达后自然触发） |
| 持续回调 | DisplaySync enable/disable（引用计数） | FrameController require/release（延迟释放） |
| 防重复 | fusionRendererInvalid 布尔标志 | frameCallbackRegistered 原子标志 |
| 释放策略 | 显式 disable（引用计数归零） | 延迟 50ms 释放（防抖动） |
| 注册时机 | invalidate 时按需注册 | Surface 创建时注册，按需 require/release |

## 帧触发对比

### FusionRenderer 帧触发链

FusionRenderer 使用 **UIContext.postFrameCallback + DisplaySync** 驱动帧循环。

```
invalidate()
  → FusionRendererFrameDispatcher.invalidate()
    → container.fusionRendererInvalid = true
    → context.frameMgr?.postFrameCallback()
      → RenderFrameManager (ArkTS)
        → UIContext.postFrameCallback(RenderFrameCallback)
          → VSync 到达
            → RenderFrameCallback.onFrame(nanos)
              → InternalArkUIViewController.onFrame(nanos)
                → ComposeArkUIViewContainer.onFrame()
                  → FusionRendererFrameDispatcher.onFrame()
                    → container.fusionRendererInvalid = false
                    → container.fusionRendererVsyncTimeStamp = timestamp
                    → context.notifyRedraw()
                      → renderNode.notifyRedraw()
                        → RenderNode draw 回调
                          → fusionRendererNodeDrawCallback(id, canvas)
                            → ComposeArkUIViewContainer.onDraw()
                              → FusionRendererDrawPipeline.onDraw()
                                → mediator.onDraw()
                                  → FusionRendererMediatorDelegate.draw()
                                    → scene.render(canvas, timestamp)
                                      → BaseComposeScene.render() 六阶段
```

触发源：
- Compose 状态变化 → updateInvalidations → invalidate → postFrameCallback
- 触摸事件 → invalidate
- 尺寸变化 → onSurfaceChanged

关键设计：
- `RenderFrameManager` 持有 `DisplaySync` 实例（`displaySync.create()`），设置期望帧率 120fps
- `enableFrameCallback(id)` 注册 DisplaySync 持续回调；`disableFrameCallback(id)` 注销
- `fusionRendererInvalid` 标志防止重复请求帧：同一帧内多次 invalidate 只触发一次 postFrameCallback
- onFrame 通过 `notifyRedraw()` → `renderNode.notifyRedraw()` **间接**触发 onDraw，不是直接调用

### SkiaRenderer 帧触发链

```
OH_NativeXComponent VSync
  → OnFrameCallbackCB(component, timestamp, targetTimestamp)
    → controller->onFrame(timestamp, targetTimestamp)
      → BasicArkUIViewController.onFrame()
        → onComposeVsync(timestamp)           → ChoreographerManager.onVsync
          → onBackgroundVsyncPulse (if !active)
        → frameDispatcher.onFrame()
          → SkiaRendererFrameDispatcher.onFrame()
            → EglPrepareDraw()                ← eglMakeCurrent
            → drawPipeline.onDraw()
              → ComposeArkUIViewContainer.onDraw()
                → mediator.onDraw()
                  → SkiaRendererMediatorDelegate.draw()
                    → ComposeSceneRender.draw(targetTimestamp)
                      → ensureSurface → clear → onDraw → flush
                        → scene.render(canvas, timestamp)
                          → BaseComposeScene.render() 六阶段
            → EglFinishDraw()                 ← eglSwapBuffers
```

触发源：
- XComponent VSync 回调（持续触发，不受应用控制）
- 触摸事件（XComponent onTouch）
- 尺寸变化（ComposeSizeProxy → onSurfaceChanged）

## 关键差异

### 1. 帧驱动模型

| 维度 | FusionRenderer | SkiaRenderer |
|------|---------------|-------------|
| VSync 来源 | UIContext.postFrameCallback (DisplaySync) | XComponent OH_NativeXSync 回调 |
| 帧请求方式 | 按需：invalidate → postFrameCallback | 持续：XComponent VSync 自动到达 |
| 空闲时帧回调 | 无（不请求就不触发） | 有（XComponent VSync 持续触发） |
| 帧到达保证 | 需要显式 invalidate | VSync 自动到达 |
| 绘制触发方式 | onFrame → notifyRedraw → RenderNode draw 回调 → onDraw（间接） | onFrame → EglPrepare → onDraw → EglFinish（直接） |

两条路径都是**按需请求帧**模型，但 SkiaRenderer 的 VSync 持续推送使其表现为推模型。

### 2. ChoreographerManager 角色

两种路径共用 `ChoreographerManager`（位于 `onComposeVsync` 中），但驱动方式不同：

- **FusionRenderer**：`ChoreographerManager` 通过 `BasicArkUIViewController.onFrame()` 驱动（由 RenderFrameCallback 触发）。后台时 `shouldRunBackgroundHeartbeat=false`，不启动心跳线程，因为 RenderNode 回调驱动 VSync 不安全。
- **SkiaRenderer**：`ChoreographerManager` 同样通过 `onFrame()` 驱动。后台时 `shouldRunBackgroundHeartbeat=true`，启动心跳线程维持 VSync。

### 3. 后台帧处理

| 维度 | FusionRenderer | SkiaRenderer |
|------|---------------|-------------|
| shouldRunBackgroundHeartbeat | false | true |
| 后台 VSync 驱动 | DisplaySync + RenderNode 回调 | 心跳线程 + ChoreographerManager |
| 后台帧脉冲 | onBackgroundVsyncPulse → sendFrameWithoutDraw | onComposeVsync → ChoreographerManager.onVsync + onBackgroundVsyncPulse |

FusionRenderer 后台时不启动心跳线程，因为 RenderNode 回调涉及 ArkUI 组件树操作，从后台线程驱动不安全（可能 SIGSEGV）。它依赖 DisplaySync 持续回调 + `onBackgroundVsyncPulse` 路径。

### 4. 绘制包装

| 维度 | FusionRenderer | SkiaRenderer |
|------|---------------|-------------|
| 绘制前 | 无需 EGL 操作 | EglPrepareDraw (eglMakeCurrent) |
| 绘制后 | 无需 flush（系统自动合成） | EglFinishDraw (eglSwapBuffers) |
| Canvas 来源 | RenderNode draw 回调参数 | ComposeSceneRender 自管理 Surface |
| requiresPostDrawFlush | false | true |

FusionRenderer 的 Canvas 由 RenderNode 的 draw 回调提供，系统负责合成。SkiaRenderer 需要自己管理 EGL 上下文和帧缓冲提交。

### 5. onFrame 与 onDraw 的关系

| 路径 | onFrame 行为 | onDraw 触发方式 |
|------|------------|---------------|
| FusionRenderer | 设置 invalid=false + timestamp，调用 notifyRedraw | RenderNode 异步 draw 回调触发 |
| SkiaRenderer | 在 onFrame 内直接调用 drawPipeline.onDraw | 同步直接调用 |

FusionRenderer 的 onFrame 和 onDraw 是**异步分离**的：onFrame 请求重绘，系统稍后调用 RenderNode draw 回调。SkiaRenderer 的 onFrame 和 onDraw 是**同步连续**的：在同一个 onFrame 调用中依次执行。

## 帧时钟系统的统一性

尽管触发方式不同，帧时钟系统的核心行为完全一致：

1. **两级 BroadcastFrameClock 级联** — 完全共用
2. **FlushCoroutineDispatcher 双路径** — 完全共用
3. **render() 六阶段** — 完全共用
4. **协程上下文组装** — 完全共用
5. **recomposer / effectDispatcher 分工** — 完全共用

策略模式确保了帧时钟"内核"与渲染"外壳"的解耦。添加新的渲染路径只需要实现 6 个策略接口，不需要修改帧时钟系统。

## 对开发者的意义

- Compose 内容代码在两种路径上行为一致（同一个 recomposer、同一套 effect 调度）
- 帧时钟相关的 bug 修复对两种路径同时生效
- FusionRenderer 的 onFrame/onDraw 异步分离意味着 invalidate 到实际绘制有延迟（RenderNode 回调调度）
- SkiaRenderer 的 XComponent VSync 持续触发会增加后台功耗（需要心跳线程维持）

## 来源

- [[src-CMP帧时钟协作机制]] — 帧时钟系统完整机制
- [[src-OHOS SkiaRenderer渲染管线设计]] — SkiaRenderer 帧循环
- [[src-融合渲染整体方案总结]] — FusionRenderer 帧循环
- 源码确认：FusionRendererFrameDispatcher、RenderFrameManager (ComposeNode.ets)、ArkUIViewController.kt
