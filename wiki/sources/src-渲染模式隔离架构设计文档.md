---
type: source
created: 2026-04-19
updated: 2026-04-19
source_file: raw/渲染模式隔离架构设计文档.md
ingested: 2026-04-19
tags:
  - CMP
  - 渲染模式
  - 架构隔离
  - 策略模式
  - OHOS
---

# 渲染模式隔离架构设计文档（源文档摘要）

## 摘要

本文档系统阐述了 CMP 如何通过三层隔离机制（构建层、运行时策略层、ArkTS 分发层）实现 FusionRenderer 与 SkiaRender 两种渲染路径的完全解耦。核心设计采用策略模式，定义六个策略接口（SurfaceLifecycleHandler、FrameDispatcher、DrawPipeline、InputStrategy、ContentBindingStrategy、MediatorRenderDelegate），由通用壳层 `ComposeArkUIViewContainer` 通过 lazy 注入按 backendId 分发。文档同时涵盖 BackendId 全链路传递、Gradle 构建任务链、逃生通道机制、多仓库构建流水线，以及框架开发者和应用开发者的完整操作指南。

## 关键发现

- **三层隔离架构**：构建层（`compose.ohos.rendererbackend` 控制源码编译范围）→ 运行时策略层（`RenderBackendProvider` 按 backendId 分发六类策略工厂）→ ArkTS 分发层（`compose/Compose.ets` 薄分发器路由到模式专用组件）
- **BackendId 全链路传递**：Gradle 配置期生成 `@CName("kn_get_render_backend_id")` 符号 → Kotlin/Native 编译入 libcompose_arkui_utils.so → native 层 weak symbol / dlsym 查询 → `setRendererBackendId(id)` → Kotlin 策略工厂 + ArkTS `getRenderBackendId()` 路由
- **六个策略接口覆盖全部行为差异**：SurfaceLifecycleHandler（表面生命周期）、FrameDispatcher（帧驱动，行为差异最大）、DrawPipeline（绘制分发）、InputStrategy（输入分发）、ContentBindingStrategy（Content 绑定时序，时序差异最大）、MediatorRenderDelegate（渲染输出路由）
- **Content 绑定时序差异**：FusionRenderer 延迟到首次 `onSurfaceChanged`（尺寸就绪后）才调用 `setContent()`；SkiaRender 在 mediator 创建时立即调用 `setContent()`，无需等待 surface
- **逃生通道（Escape Hatch）机制**：`-Pcompose.ohos.rendererbackend=skia|fusion-renderer` 允许团队绕过另一团队的编译错误进行自验证；`both`（默认）为正式发布标准，单模式产物不应发布到公共仓库
- **klib Metadata 自描述**：产物内嵌 `ohos-render-backends.properties` 声明支持的 backend 集合，应用配置期校验不匹配则直接 GradleException，避免运行时白屏

## 重要细节

### 策略模式架构

`ComposeArkUIViewContainer` 继承 `BasicArkUIViewController`，通过 `lazy` 属性注入策略实现，自身不包含任何 `isFusionRenderer()` 分支：

```
ComposeArkUIViewContainer
    ├── surfaceHandler: SurfaceLifecycleHandler    (lazy)
    ├── frameDispatcher: FrameDispatcher           (lazy)
    ├── drawPipeline: DrawPipeline                 (lazy)
    ├── inputStrategy: InputStrategy               (lazy)
    ├── contentBinding: ContentBindingStrategy     (lazy)
    └── mediatorDelegate → createMediatorRenderDelegateFactory 注入
```

`RenderBackendProvider` 是进程级唯一 backend 控制点，`StrategyFactories` 数据类持有六类工厂函数。`StrategyRegistrationConfig`（Gradle 模板生成）在 `ensureInitialized()` 中注册 `registerFusionRendererStrategies()` / `registerSkiaStrategies()`。

### 两条路径关键差异对比

| 维度 | FusionRenderer (id=1) | SkiaRender (id=0) |
|------|----------------------|-------------------|
| 渲染后端 | OHOS RenderService (RenderNode) | OpenGL ES / EGL (XComponent) |
| 帧驱动 | RenderFrameManager + postFrameCallback | XComponent vsync 回调 |
| 后台 VSync 心跳 | 关闭（`shouldRunBackgroundHeartbeat=false`） | 保持（`shouldRunBackgroundHeartbeat=true`） |
| 尺寸感知 | `onAreaChange` 直接传递 | EGL surface → ComposeSizeProxy 迂回 |
| Content 绑定 | `onFirstSurfaceChanged` 后 `setContent()` | `onMediatorCreated` 立即 `setContent()` |
| EGL flush | 不需要 (`requiresPostDrawFlush=false`) | 需要 finishDraw (`requiresPostDrawFlush=true`) |
| RenderNode 类型 | CRenderNode（优先）/ JsRenderNode（回退） | 无 |

### 核心文件位置

| 职责 | 文件路径 |
|------|----------|
| 策略接口定义 | `compose/ui/ui/src/ohosMain/.../RenderBackend.kt` |
| 通用壳层 | `compose/ui/ui/src/ohosMain/.../ComposeArkUIViewContainer.kt` |
| 策略工厂 | `compose/ui/ui/src/ohosMain/.../RenderBackendProvider.kt` |
| 注册配置模板 | `compose/ui/ui/src/ohosMain/templates/StrategyRegistrationConfig.kt.template` |
| FusionRenderer 策略实现 | `compose/ui/ui/src/ohosMain/fusionRenderer/kotlin/` |
| SkiaRender 策略实现 | `compose/ui/ui/src/ohosMain/skia/kotlin/` |
| ArkTS 薄分发器 | `compose/Compose.ets` |
| FusionRenderer ArkTS | `fusionRenderer/Compose.ets` |
| SkiaRender ArkTS | `skiarender/Compose.ets` |
| BackendId native 查询 | `arkui_view_controller_wrapper.cpp` → `QueryRenderBackendIdUncached` |
| Metadata 解析（应用侧） | `OhosRenderBackendMetadataResolver.kt`（gradle-plugins） |

### 构建层三种模式行为

| 维度 | `both`（默认） | `fusion-renderer` | `skia` |
|------|------|------|------|
| arm64 编译源码 | 两个目录均加入 | 仅 fusionRenderer/ | 仅 skia/ |
| `StrategyRegistrationConfig` | 两者均注册 | 仅 FusionRenderer | 仅 Skia |
| Skiko artifactId 选择 | `*-fusionrenderer`（优先） | `*-fusionrenderer` | `skiko-ohosarm64` |
| 用途 | 正式发布 | 逃生通道 / 单模式开发 | 逃生通道 / 单模式开发 |

### 多仓库构建顺序

**Skiko → Core → Plugin → Sample**（严格顺序，产物通过本地 Maven 传递）。Skiko 版本号三处必须对齐：`skiko/gradle.properties` 的 `deploy.version`、`core/gradle/libs.versions.toml` 的 `skikoOhos`、`gradle-plugins/gradle.properties` 的 `compose.ohos.skiko.version`。

### 框架开发者红线

- `ComposeArkUIViewContainer` 不含 `isFusionRenderer()` 分支
- `compose/Compose.ets` 只做路由，不承载模式专用逻辑
- FusionRenderer 模式私有状态（`FusionRendererContext`）不上浮到通用层
- 禁止 silent fallback，校验失败必须抛异常
- 新增差异代码优先归入现有六个策略接口，不新增策略接口除非差异类型长期稳定

## 与已有知识的关联

- [[融合渲染架构]] — 本文档是其渲染模式隔离架构的完整展开，详细描述了 FusionRenderer 路径内部如何通过策略模式与 SkiaRender 路径解耦
- [[ContentModifier挂载机制]] — FusionRenderer 路径中 RenderNode 通过 ContentModifier 挂载到 ArkUI 节点树，本文档描述了 `FusionRendererBackend` 接口如何管理这一过程
- [[OHRenderNode]] — 本文档描述的 CRenderNode / JsRenderNode 选择逻辑与 `FusionRendererContext` 的模式私有状态管理，直接关联 OHRenderNode 的生命周期管理
- [[SkPictureRecorder]] — FusionRenderer 的 `DrawPipeline` 通过 `mediator.onDraw(canvas)` 驱动 SkPictureRecorder 录制，本源文档提供了策略层如何触发这一流程的上下文
- [[RenderNode生命周期]] — `FusionRendererSurfaceLifecycleHandler.onSurfaceDestroyed` 释放 context 并 dispose mediator，对应 RenderNode 的销毁阶段

## 来源

- 源文档：`raw/渲染模式隔离架构设计文档.md`（~63KB，8 章，涵盖概览、顶层架构、详细设计、构建层、逃生通道、框架开发者指导、应用开发者指导、架构约束红线）
