---
type: source
created: 2026-04-27
updated: 2026-04-27
source_file: 工程规范整理.xlsx + 合作对齐硬规范_名称基线_最终版.xlsx + 鸿蒙化关键模块分析.xlsx + 源码分析
ingested: 2026-04-27
tags:
  - 规范对齐
  - 支付宝协作
  - 鸿蒙化
  - 工程规范
related:
  - "[[analysis-FusionRenderer与SkiaRenderer渲染路径对比]]"
  - "[[融合渲染架构]]"
  - "[[三明治混排结构]]"
---

# CMP 鸿蒙化工程规范对齐模板

> **文档目的**：作为我方（华为 CMP 团队）与支付宝 CMP/KMP 定制化版本之间的鸿蒙化规范对齐基线文档。目标是确保双方在核心路径上的工程规范一致，降低代码合入成本，保证开发者体验一致。
>
> **使用方式**：每个规范点包含「规范定义」「我方实现」和「对齐状态」三部分。支付宝侧需在「对齐状态」列填写对齐情况。

---

## 一、对齐原则

### 1.1 核心目标

| 目标 | 说明 |
|------|------|
| **代码互收** | 双方性能优化方案可低成本互相合入 |
| **开发者体验一致** | 应用层 API、构建流程、配置方式最大程度统一 |
| **版本演进可控** | 上游（JetBrains）版本升级时双方可同步跟进 |

### 1.2 对齐层级

| 层级             | 含义                  | 要求          |
| -------------- | ------------------- | ----------- |
| **硬规范（必须对齐）**  | 影响构建、发布、互操作的核心名称和接口 | 建议对齐，允许合理差异 |
| **软规范（建议对齐）**  | 影响开发者体验的约定和模式       | 建议对齐，允许合理差异 |
| **参考规范（信息共享）** | 模块内部实现细节            | 仅作参考，不强求对齐  |

---

## 二、命名基线对齐

### 2.1 配置参数名

| 规范名称                        | 名称来源         | 说明                        | 我方工程锚点                      | 支付宝实现 | 对齐状态 |
| --------------------------- | ------------ | ------------------------- | --------------------------- | ----- | ---- |
| `compose.platforms`         | JetBrains 已有 | 全仓平台选择参数，控制是否进入 OHOS 编译链路 | `build.gradle`              |       |      |
| `skikoOhos`                 | 鸿蒙化新增        | Core 侧 OHOS Skiko 版本单一来源，定义在 libs.versions.toml | `gradle/libs.versions.toml`  |       |      |
| `ignoreOhosSdkVersionCheck` | 鸿蒙化新增        | SDK 版本校验开关                | `ui-arkui/build.gradle.kts` |       |      |
| `minimalOhosSdkVersion`     | 鸿蒙化新增        | 最低 SDK 版本门槛               | `ui-arkui/build.gradle.kts` |       |      |
| `deploy.version`            | JetBrains 已有 | Skiko 发布版本号               | `skiko/gradle.properties`   |       |      |
| `deploy.release`            | JetBrains 已有 | Skiko 发布模式（正式/快照）         | `skiko/gradle.properties`   |       |      |

### 2.2 源集名（Source Set）

| 规范名称            | 说明                      | 我方用途             | 支付宝实现 | 对齐状态 |
| --------------- | ----------------------- | ---------------- | ----- | ---- |
| `ohosMain`      | OHOS 公共源集（ARM64/X64 共用） | 策略接口、渲染后端注册等共享代码 |       |      |
| `ohosArm64Main` | ARM64 主源集               | 设备端核心实现主要落点      |       |      |
| `ohosX64Main`   | X64 主源集                 | 模拟器、IDE Sync     |       |      |
| `ohosArm64Test` | ARM64 测试源集              | 设备端测试            |       |      |
| `ohosX64Test`   | X64 测试源集                | 补齐测试变体           |       |      |
|                 |                         |                  |       |      |

### 2.3 平台与 Target 名

| 规范名称 | 说明 | 我方工程锚点 | 支付宝实现 | 对齐状态 |
|----------|------|------------|----------|---------|
| `ohos` | 平台聚合名（`compose.platforms` 取值） | `build.gradle` | | |
| `ohosArm64` | ARM64 KMP target 名 | `ui-arkui/build.gradle.kts` | | |
| `ohosX64` | X64 KMP target 名 | `ui-arkui/build.gradle.kts` | | |

### 2.4 关键任务名

| 规范名称 | 类型 | 说明 | 支付宝实现 | 对齐状态 |
|----------|------|------|----------|---------|
| `publishComposeJb` | 全局任务 | Compose 公版发布入口 | | |
| `publishComposeJbToMavenLocal` | 全局任务 | 本地 Maven 发布（联调关键入口） | | |
| `compileKotlinOhosArm64` | 派生任务 | ARM64 Kotlin 编译 | | |
| `compileKotlinOhosX64` | 派生任务 | X64 Kotlin 编译 | | |
| `ohosArm64MainKlibrary` | 派生任务 | ARM64 KLIB 打包 | | |
| `ohosX64MainKlibrary` | 派生任务 | X64 KLIB 打包 | | |

### 2.5 产物名

| 规范名称 | 说明 | 我方用途 | 支付宝实现 | 对齐状态 |
|----------|------|---------|----------|---------|
| `compose.har` | OHOS 侧框架最终交付产物 | 合作方交付、应用侧接入 | | |
| `compose_arkui_utils` | ui-arkui Native/CInterop 产物 | KN 与 ArkUI 桥接 | | |
| `arkui` | ArkUI cinterop 导入名 | ArkUI 原生头互操作 | | |
| `skiko-ohosarm64` | Skiko ARM64 发布坐标后缀 | 依赖解析与发布识别 | | |
| `skiko-ohosarm64-fusionrenderer` | Skiko ARM64 融合渲染坐标后缀 | 区分渲染路径产物 | | |

---

## 三、编译参数基线对齐

### 3.1 环境变量

| 参数名 | 说明 | 我方默认值 | 对齐要求 | 支付宝实现 | 对齐状态 |
|--------|------|----------|---------|----------|---------|
| `OHOS_SDK_HOME` | OpenHarmony SDK 根目录 | 优先于 DEVECO_STUDIO_HOME | 必须对齐 | | |
| `DEVECO_STUDIO_HOME` | DevEco Studio 安装目录 | 推导默认 SDK 路径的备选 | 必须对齐 | | |

### 3.2 Gradle 参数

| 参数名 | 形态 | 说明 | 对齐要求 | 支付宝实现 | 对齐状态 |
|--------|------|------|---------|----------|---------|
| `-Pcompose.platforms` | 命令行 | 平台过滤（`ohos`, `android,ohos` 等） | 必须对齐 | | |
| `-PohosSkikoVersion` | 命令行 | 临时覆盖 OHOS Skiko 版本（默认取 `libs.versions.toml` 中 `skikoOhos` 值） | 必须对齐 | | |
| `ignoreOhosSdkVersionCheck` | gradle.properties | 跳过 SDK 版本检查 | 必须对齐 | | |
| `minimalOhosSdkVersion` | gradle.properties | 最低 SDK 版本（我方默认 15） | 必须对齐 | | |
| `-Pdeploy.version` | 命令行 | Skiko 发布版本号 | 必须对齐 | | |
| `-Pdeploy.release` | 命令行 | Skiko 正式版/快照版切换 | 必须对齐 | | |

### 3.3 调试参数

| 参数名 | 说明 | 对齐要求 | 支付宝实现 | 对齐状态 |
|--------|------|---------|----------|---------|
| `-Pandroidx.kLogLevel` | KLog 日志级别 | 建议对齐 | | |
| `-Pandroidx.kLogEnabled` | KLog 开关 | 建议对齐 | | |
| `-Pandroidx.ohosTraceEnabled` | OHOS 侧 Trace 开关 | 建议对齐 | | |

---

## 四、源码目录结构规范

### 4.1 OHOS 源码分层约定

| 规范点                                      | 说明                                   | 我方实现                                                                  | 支付宝实现 | 对齐状态 |
| ---------------------------------------- | ------------------------------------ | --------------------------------------------------------------------- | ----- | ---- |
| **平台公共代码 → `ohosMain`**                  | ARM64/X64 共用的 OHOS 代码优先放在 `ohosMain` | 策略接口 `RenderBackend.kt`、渲染后端注册、平台枚举等放在此处                              |       |      |
| **设备端实现 → `ohosArm64Main`**              | 真实设备主架构实现                            | 场景中介器、ArkUIViewController、平台 actual 实现等放在此处                           |       |      |
| **文件后缀 → `.ohos.kt`**                    | OHOS 平台特定实现文件使用 `.ohos.kt` 后缀        | `Synchronization.ohos.kt`, `Actuals.ohos.kt`, `DragAndDrop.ohos.kt` 等 |       |      |
| **渲染策略目录 → `fusionRenderer/` + `skia/`** | 两种渲染路径的策略实现分别放在独立目录                  | `ohosMain/fusionRenderer/kotlin/` 和 `ohosMain/skia/kotlin/`           |       |      |

### 4.2 渲染路径源码隔离

```
我方实现（参考）：
compose/ui/ui/src/ohosMain/
├── fusionRenderer/kotlin/.../platform/
│   ├── FusionRendererStrategyImpl.kt    ← OHRender 策略实现
│   ├── FusionRendererRegistration.kt    ← OHRender 策略注册
│   └── FusionRendererContext.kt         ← OHRender 上下文
└── skia/kotlin/.../platform/
    └── SkiaRendererStrategyImpl.kt      ← SkiaRender 策略实现
```

| 规范点 | 我方实现 | 支付宝实现 | 对齐状态 |
|--------|---------|----------|---------|
| 策略接口定义位置 | `ohosMain` 公共源集 | | |
| FusionRenderer 策略实现目录 | `ohosMain/fusionRenderer/kotlin/` | | |
| SkiaRender 策略实现目录 | `ohosMain/skia/kotlin/` | | |
| 策略注册机制 | `StrategyFactories` + `registerXxxFactories()` | | |
| 运行时选择机制 | `rendererBackendId` + `isOHRender()` | | |

### 4.3 ArkTS 侧隔离

```
我方实现（参考）：
ui-arkui/src/.../ets/
├── compose/
│   └── Compose.ets              ← 薄分发器，根据 backendId 路由
├── ohrender/
│   ├── Compose.ets              ← FusionRenderer 专用
│   ├── CanvasNode.ets           ← NodeController/FrameNode/CRenderNode
│   └── ...
└── skiarender/
    ├── Compose.ets              ← SkiaRender 专用
    └── ...
```

| 规范点 | 我方实现 | 支付宝实现 | 对齐状态 |
|--------|---------|----------|---------|
| 分发器模式 | `Compose.ets` 薄分发器，不透传内部参数 | | |
| 分发器路由逻辑 | 根据 `backendId` 路由到 `ohrender/` 或 `skiarender/` | | |
| 模式特定逻辑位置 | 仅在对应模式目录内实现，不添加到分发器 | | |

---

## 五、渲染路径架构规范

### 5.1 双渲染路径对齐

| 维度 | 规范点 | 我方实现 | 支付宝实现 | 对齐状态 |
|------|--------|---------|----------|---------|
| **backendId 编码** | FusionRenderer=1, SkiaRender=0 | `FUSION_RENDERER_BACKEND_ID=1`, `SKIA_BACKEND_ID=0` | | |
| **gradle.properties 名** | 渲染后端选择参数名 | `rendererBackend=fusion-renderer` / `skia` | | |
| **策略模式接口** | 统一的策略抽象 | 6 个策略接口（见 5.2） | | |
| **运行时切换** | 通过 `isOHRender()` / `rendererBackendId` 选择 | 运行时根据 `backendId` 选择策略工厂 | | |
| **共享 klib** | 两种路径编译到同一个 klib | 通过策略模式在运行时选择 | | |

### 5.2 策略接口定义（硬规范）

以下策略接口是渲染路径隔离的核心契约，双方必须对齐：

| 策略接口 | 核心方法 | 职责说明 | 支付宝对齐状态 |
|----------|---------|---------|--------------|
| **SurfaceLifecycleHandler** | `onSurfaceCreated`, `onSurfaceChanged`, `onSurfaceDestroyed` | Surface 生命周期管理 | |
| **FrameDispatcher** | `invalidate`, `onFrame`, `onIdle`, `dispose` | 帧调度与 VSync 管理 | |
| **DrawPipeline** | `onDraw` | 绘制管线回调 | |
| **InputStrategy** | `shouldDispatchTouch`, `onDispatchTouch` | 触摸事件分发策略 | |
| **ContentBindingStrategy** | `onMediatorCreated`, `onFirstSurfaceChanged` | Composable 内容绑定时机 | |
| **MediatorRenderDelegate** | `setRenderSize`, `draw`, `dispose`, `resetSurface`, `close` | 渲染委托 | |

### 5.3 FusionRenderer 关键行为约定

| 规范点 | 我方实现 | 对齐要求 | 支付宝实现 | 对齐状态 |
|--------|---------|---------|----------|---------|
| RenderNode 延迟创建 | `initOHRenderNode` 在 `aboutToAppear` 内调用 | 硬规范 | | |
| `enableCApi` 可变性 | `var`，由 `initOHRenderNode` 更新 | 硬规范 | | |
| CRenderNode 创建约束 | 必须在已挂载到 ArkUI 组件树的 `NodeContent` 上创建 | 硬规范 | | |
| 尺寸通知路径 | `onAreaChange` → `reSize` → `onSurfaceChanged`（直接路径） | 硬规范 | | |
| Content 绑定时机 | 延迟到首次 `onSurfaceChanged` | 硬规范 | | |
| RenderNode 类型选择 | 优先 `CRenderNode`（API 6.0.0.107+），`JsRenderNode` 回退 | 建议对齐 | | |

### 5.4 SkiaRender 关键行为约定

| 规范点 | 我方实现 | 对齐要求 | 支付宝实现 | 对齐状态 |
|--------|---------|---------|----------|---------|
| 渲染后端 | OpenGL ES / EGL（XComponent） | 硬规范 | | |
| 帧驱动 | XComponent vsync 回调 | 硬规范 | | |
| 尺寸通知 | `ComposeSizeProxy` 迂回路径 | 硬规范 | | |
| Content 绑定时机 | mediator 创建时立即调用 | 硬规范 | | |
| skikobridge 链接 | Sample CMake 必须链接 `skikobridge` | 硬规范 | | |

---

## 六、核心 API 规范

### 6.1 应用层入口 API

| 规范点 | 我方实现 | 对齐要求 | 支付宝实现 | 对齐状态 |
|--------|---------|---------|----------|---------|
| **统一 API（推荐）** | `ComposeArkUIViewController(env) { App() }` | 硬规范 | | |
| **Deprecated API（兼容）** | `ComposeArkUIViewController(env, frameMgr, enableCApi, rootContent) { App() }` | 建议保留 | | |
| **接口分离** | `ArkUIViewController`（公开） + `InternalArkUIViewController`（内部） | 建议对齐 | | |

### 6.2 ArkTS 侧入口 API

| 规范点 | 我方实现 | 对齐要求 | 支付宝实现 | 对齐状态 |
|--------|---------|---------|----------|---------|
| 组件名 | `Compose` struct | 硬规范 | | |
| 导入路径 | 从 `'compose'` 导入（通过 `compose.har` re-export） | 硬规范 | | |
| 禁止直接 import | 应用不能直接 import `libcompose_arkui_utils.so` | 硬规范 | | |
| `InternalArkUIViewController` 暴露 | 不出现在应用页面代码中 | 硬规范 | | |

---

## 七、构建系统规范

### 7.1 KMP Target 注册

| 规范点 | 我方实现 | 支付宝实现 | 对齐状态 |
|--------|---------|----------|---------|
| Target 注册方式 | `buildSrc` 中 `AndroidXComposeMultiplatformExtensionImpl.kt` 统一注册 | | |
| ARM64 target 配置 | `ohosArm64 { configureOhosArkuiTarget() }` | | |
| X64 target 配置 | `ohosX64 { configureOhosArkuiTarget() }` | | |
| 源集依赖关系 | `ohosArm64Main` / `ohosX64Main` dependsOn `nativeMain` | | |
| 测试源集 | `ohosArm64Test` / `ohosX64Test` dependsOn `nativeTest` | | |

### 7.2 CMake 集成

| 规范点 | 我方实现 | 支付宝实现 | 对齐状态 |
|--------|---------|----------|---------|
| OHOS 架构映射 | `ohosArm64` → `arm64-v8a`, `ohosX64` → `x86_64` | | |
| Skiko 产物链接 | Skiko 以 `skiko-native-bridges-ohos-arm64.a` 静态库链入 `libkn.so` | | |
| 原生库链接约束 | SkiaRender 路径必须 `target_link_libraries(entry skikobridge)` | | |

### 7.3 Skiko 构建约定

| 规范点 | 我方实现 | 支付宝实现 | 对齐状态 |
|--------|---------|----------|---------|
| 渲染模式产物区分 | `skiko-ohosarm64`（自渲染）vs `skiko-ohosarm64-fusionrenderer`（融合渲染） | | |
| 版本号来源 | `gradle/libs.versions.toml` 中 `skikoOhos` | | |
| 版本临时覆盖 | `-PohosSkikoVersion=<version>` | | |

---

## 八、代码风格规范

### 8.1 Region 标记约定

| 规范点 | 我方实现 | 支付宝实现 | 对齐状态 |
|--------|---------|----------|---------|
| OHOS 代码区域标记 | `//region Ohos ... //endregion` 成对包裹 | | |
| 标记范围 | 所有新增或修改 JetBrains 上游源码的 OHOS 代码区域 | | |

### 8.2 Kotlin 代码规范

| 规范点 | 我方实现 | 支付宝实现 | 对齐状态 |
|--------|---------|----------|---------|
| 文件命名 | OHOS 特定：`ClassName.ohos.kt`；通用：`ClassName.kt` | | |
| 类名 | PascalCase | | |
| 函数/变量 | camelCase | | |
| 常量 | UPPER_SNAKE_CASE | | |
| 可见性 | `@InternalComposeUiApi` / `internal` / `private` | | |
| JVM 注解兼容 | OHOS K/N 不支持 `@JvmInline`、`@file:JvmName` 等，需注释或去除 | | |

### 8.3 C/C++ 代码规范

| 规范点 | 我方实现 | 支付宝实现 | 对齐状态 |
|--------|---------|----------|---------|
| 成员变量前缀 | `f` 前缀（Skia 风格）：`fNowFrame`, `fNoLimitSize` | | |
| 静态/全局变量前缀 | `g` 前缀：`gNodeConstructorRef` | | |
| 类名 | PascalCase | | |
| Getter/Setter | `get`/`set` 前缀 | | |
| 布尔判断方法 | `is`/`has`/`can`/`need` 前缀 | | |
| OH_Drawing API | 创建/销毁成对使用 | | |

### 8.4 ArkTS 代码规范

| 规范点 | 我方实现 | 支付宝实现 | 对齐状态 |
|--------|---------|----------|---------|
| 组件装饰器 | `@Component` / `@Builder` | | |
| 状态管理 | `@State` / `@Prop` | | |
| Native 导入 | `import { func } from 'libentry.so'` | | |

### 8.5 版权头

| 文件类型 | 我方规范 | 支付宝实现 | 对齐状态 |
|----------|---------|----------|---------|
| **华为新增文件** | `Copyright 2025-2025 Huawei Technologies Co., Ltd. and Kotlin Programming Language contributors.` + Apache 2.0 | | |
| **已有 Tencent 文件** | 保留原有 Tencent 头，不修改 | | |
| **Skia 源文件** | 保留原有 Google/BSD 头 | | |

---

## 九、关键模块清单

> 以下为我方认定的鸿蒙化关键模块，基于 Y1（关键适配代码）至 Y5（历史问题多）评判标准筛选。双方应对照确认各自的关键模块范围。

### 9.1 Compose UI 层关键模块

| 序号 | 模块 | 文件 | 语言 | 关键原因 | 支付宝对等模块 |
|------|------|------|------|---------|-------------|
| 1 | `:compose:ui:ui` | `ArkUIViewController.kt` | Kotlin | 核心 API 入口，渲染后端选择逻辑 | |
| 2 | `:compose:ui:ui` | `ComposeSceneMediator.ohos.kt` | Kotlin | 渲染委托分发，9 处 region | |
| 3 | `:compose:ui:ui` | `ComposeArkUIViewContainer.kt` | Kotlin | 策略容器，全新鸿蒙适配 | |
| 4 | `:compose:ui:ui` | `RenderBackend.kt` + 策略实现 | Kotlin | 渲染模式隔离核心接口 | |
| 5 | `:compose:ui:ui` | `RenderNodeLayer.skiko.kt` | Kotlin | OHRender Picture 录制/脏区 | |
| 6 | `:compose:ui:ui` | `PlatformLayersComposeScene.skiko.kt` | Kotlin | 场景管理核心 | |
| 7 | `:compose:ui:ui-graphics` | `SkiaBackedCanvas.skiko.kt` | Kotlin | 所有绘制操作经过此类 | |

### 9.2 ui-arkui 模块关键文件

| 序号 | 文件 | 语言 | 关键原因 | 支付宝对等模块 |
|------|------|------|---------|-------------|
| 8 | `compose/Compose.ets` + `ohrender/` + `skiarender/` | ArkTS | ArkTS 入口分发器 | |
| 9 | `CanvasNode.ets` + `ArkUIView.ets` 等 | ArkTS | CRenderNode 生命周期管理 | |
| 10 | `xcomponent_render.cpp` 等 | C++ | XComponent EGL/GL 渲染 | |
| 11 | `Messenger.ets` + `ComposeSizeProxy.ets` | ArkTS | SkiaRender 尺寸通知迂回路径 | |

### 9.3 Foundation 层关键模块

| 序号 | 文件 | 关键原因 | 支付宝对等模块 |
|------|------|---------|-------------|
| 12 | `Pager.kt` 等（17 处 region） | commonMain 改动，影响全平台 | |
| 13 | `Scrollable.ohos.kt` | OHOS 滚动适配 | |
| 14 | `Overscroll.ohos.kt` | OHOS 过滚效果 | |
| 15 | `PointerInputWorkaround.ohos.kt` | OHOS 触控 bug 临时规避 | |
| 16 | `TextFieldPointerModifier.ohos.kt` | 文本输入适配 | |

### 9.4 Animation 层关键模块

| 序号 | 文件 | 关键原因 | 支付宝对等模块 |
|------|------|---------|-------------|
| 17 | `SuspendAnimation.kt`（2 处 region） | 动画强制停止能力，影响全平台 | |

### 9.5 构建系统关键文件

| 序号 | 文件 | 关键原因 | 支付宝对等模块 |
|------|------|---------|-------------|
| 18 | `AndroidXComposeMultiplatformExtensionImpl.kt`（27 处 region） | 构建系统 OHOS 核心配置 | |
| 19 | `KmpPlatforms.kt`（6 处 region） | KMP 平台枚举定义 | |
| 20 | `ComposePlatforms.kt`（3 处 region） | Compose 平台组合配置 | |
| 21 | `ComposePlugin.kt`（3 处 region） | Gradle 插件渲染后端支持 | |
| 22 | `skiko/build.gradle.kts` | Skiko 构建系统 OHOS 核心 | |

---

## 十、开发者体验对齐

### 10.1 应用层接入流程

| 步骤                 | 我方实现                                                             | 支付宝实现 | 对齐状态 |
| ------------------ | ---------------------------------------------------------------- | ----- | ---- |
| 1. harmonyApp 添加依赖 | 依赖 `compose.har`                                                 |       |      |
| 2. 创建 Controller   | `ComposeArkUIViewController(env) { App() }`                      |       |      |
| 3. 页面集成            | `Compose({ controller: this.controller })`                       |       |      |
| 4. 渲染模式切换          | `gradle.properties` 中 `rendererBackend=fusion-renderer` / `skia` |       |      |

### 10.2 框架层完整构建流程

> 以下为我方从源码构建到部署运行的全链路命令，按正确顺序排列。

**阶段一：环境准备**

```bash
# 设置 OHOS SDK 路径（二选一）
export OHOS_SDK_HOME=/path/to/openharmony
# 或
export DEVECO_STUDIO_HOME=/Applications/DevEco-Studio.app

# 可选：绕过 SDK 版本检查
export ignoreOhosSdkVersionCheck=true

# 可选：设置最小 SDK 版本
export minimalOhosSdkVersion=15
```

**阶段二：构建 Skiko（含 OHRender C++ 库）**

```bash
cd third_party/skiko/skiko

# 标准构建（以 OHRender 为源码依赖）
./build-with-local-skia.sh -Pskia.dir=../../compose_multiplatform_core/OHRender

# 正式版构建
./build-with-local-skia.sh -Pskia.dir=../../compose_multiplatform_core/OHRender -Pdeploy.release=true

# 覆盖版本号
./build-with-local-skia.sh -Pskia.dir=../../compose_multiplatform_core/OHRender -Pdeploy.version=x.x.x
```

**阶段三：构建 Compose Multiplatform 依赖层**

```bash
cd compose_multiplatform

# 本地构建 + 发布（含清理）
./eazytec-build.sh --local --clean

# 本地构建（无清理）
./eazytec-build.sh --local
```

**阶段四：构建 Compose Core 并发布到本地 Maven**

```bash
cd compose_multiplatform_core

# 仅构建 OHOS 平台并发布到本地 Maven
./gradlew :mpp:publishComposeJbToMavenLocal -Pcompose.platforms=ohos

# 多平台发布
./gradlew :mpp:publishComposeJbToMavenLocal -Pcompose.platforms=android,ohos,uikit

# 仅编译特定模块验证
./gradlew :compose:ui:ui-arkui:compileKotlinOhosarm64
./gradlew :compose:ui:ui-arkui:build

# 临时覆盖 Skiko 版本
./gradlew :mpp:publishComposeJbToMavenLocal -Pcompose.platforms=ohos -PohosSkikoVersion=0.9.22.2-OH.0.1.2-17
```

**阶段五：构建 Sample 应用 Klib 并发布到 harmonyApp**

```bash
cd compose_sample

# Debug 构建：编译 KMP 共享库并拷贝到 harmonyApp
./gradlew :composeApp:publishDebugBinariesToHarmonyApp

# Release 构建
./gradlew :composeApp:publishReleaseBinariesToHarmonyApp

# 指定外部 OHOS 工程路径
./gradlew :composeApp:publishDebugBinariesToHarmonyApp -PharmonyAppPath="/path/to/external/ohos/project"
```

**阶段六：构建 HAP 包并部署到设备**

```bash
cd compose_sample

# 自动化一键部署（推荐）
./runscript/runOhosApp-Mac.sh ohosArm64 127.0.0.1:5555

# Release 模式部署
./runscript/runOhosApp-Mac.sh ohosArm64 127.0.0.1:5555 -m release

# 自定义 bundle/ability
./runscript/runOhosApp-Mac.sh -b com.test.app -a MainAbility

# 指定外部工程路径
./runscript/runOhosApp-Mac.sh -p /path/to/external/ohos/project

# 手动分步执行（等价于上述脚本）：
# 1) 安装依赖
cd harmonyApp && ohpm install --all
# 2) Hvigor 同步
node "$DEVECO_HOME/tools/hvigor/bin/hvigorw.js" --sync -p product=default -p buildMode=debug
# 3) 构建 HAP
node "$DEVECO_HOME/tools/hvigor/bin/hvigorw.js" --mode module -p module=entry@default -p product=default -p buildMode=debug assembleHap
# 4) 安装到设备
hdc -t 127.0.0.1:5555 shell bm install -p /data/local/tmp/entry-default-signed.hap
# 5) 启动应用
hdc -t 127.0.0.1:5555 shell aa start -a EntryAbility -b com.example.harmonyapp
```

**阶段七：清理（可选）**

```bash
# 停止 Gradle Daemon
cd compose_multiplatform_core && ./killGradle.sh

# 清理临时文件
cd compose_multiplatform_core && ./cleanTempFiles.sh

# Gradle clean
cd compose_sample && ./gradlew clean
```

### 10.3 调试与诊断

| 能力 | 我方支持情况 | 支付宝实现 | 对齐状态 |
|------|------------|----------|---------|
| KLog 日志控制 | `-Pandroidx.kLogEnabled` + `-Pandroidx.kLogLevel` | | |
| OHOS Trace | `-Pandroidx.ohosTraceEnabled` | | |
| C++ 性能追踪 | `TRACE_EVENT0/1` 宏 | | |
| SDK 版本校验跳过 | `ignoreOhosSdkVersionCheck=true` | | |

---

## 十一、已知约束与常见陷阱

> 以下为我方已知的工程约束和常见陷阱，建议双方共享此类信息以避免重复踩坑。

| 约束/陷阱 | 影响范围 | 详细说明 | 支付宝是否有类似约束 |
|----------|---------|---------|-------------------|
| RenderNode 延迟创建 | FusionRenderer | `renderNode` 必须在 `initOHRenderNode` 中延迟创建，eager 创建会导致页面跳转崩溃 | |
| CRenderNode 创建位置 | FusionRenderer | 必须在已挂载到 ArkUI 组件树的 `NodeContent` 上创建，否则 `GetNodeContentFromNapiValue failed: 401` | |
| 分发器禁止透传参数 | ArkTS | `Compose.ets` 不能透传 FusionRenderer 内部参数 | |
| FusionRenderer 不使用 ComposeSizeProxy | FusionRenderer | 尺寸通过 `onAreaChange` 直接传递 | |
| skikobridge 链接缺失 | SkiaRender | 遗漏链接会导致 `SIGSEGV(SEGV_ACCERR)` | |
| `@JvmInline` K/N 不兼容 | 编译 | OHOS K/N 不支持 JVM 注解，需去除 | |
| IDE Sync ohos_x64 变体缺失 | 构建 | 新增 `ohos()` 目标时测试库也需要 X64 变体 | |
| `enableCApi` 可变性 | FusionRenderer | 必须为 `var`，由 `initOHRenderNode` 更新 | |

---

## 十二、对齐状态汇总

> 在双方完成逐项填写后，在此汇总对齐情况。

| 规范域 | 总项数 | 完全对齐 | 部分对齐 | 未对齐 | 待讨论 |
|--------|--------|---------|---------|-------|-------|
| 命名基线 | 28 | | | | |
| 编译参数 | 11 | | | | |
| 源码目录结构 | 12 | | | | |
| 渲染路径架构 | 18 | | | | |
| 核心 API | 8 | | | | |
| 构建系统 | 9 | | | | |
| 代码风格 | 18 | | | | |
| 关键模块 | 22 | | | | |
| 开发者体验 | 11 | | | | |
| 约束与陷阱 | 8 | | | | |
| **合计** | **~145** | | | | |

---

## 附录 A：我方渲染路径策略工厂注册机制

```kotlin
// 策略工厂定义
internal data class StrategyFactories(
    val surfaceHandler: (ComposeArkUIViewContainer) -> SurfaceLifecycleHandler,
    val frameDispatcher: (ComposeArkUIViewContainer) -> FrameDispatcher,
    val drawPipeline: (ComposeArkUIViewContainer) -> DrawPipeline,
    val inputStrategy: (ComposeArkUIViewContainer) -> InputStrategy,
    val contentBinding: () -> ContentBindingStrategy,
    val mediatorDelegate: (InternalArkUIViewController) -> ((() -> ComposeScene) -> MediatorRenderDelegate)
)

// 运行时选择
// rendererBackendId: SKIA_BACKEND_ID=0, FUSION_RENDERER_BACKEND_ID=1
// activeFactories() 根据当前 backendId 返回对应工厂
```

## 附录 B：我方 ArkTS 分发器核心逻辑

```typescript
// Compose.ets — 薄分发器
@Component
export struct Compose {
  @State private backendId: number = 1  // 默认 FusionRenderer
  @Require public controller: ArkUIViewController | undefined = undefined

  aboutToAppear(): void {
    if (this.controller !== undefined) {
      this.backendId = (this.controller as InternalArkUIViewController).getRenderBackendId()
    }
  }

  build() {
    if (this.backendId === 1) {
      // FusionRendererCompose({...})
    } else {
      // SkiaRenderCompose({...})
    }
  }
}
```

## 附录 C：我方统一 API 使用示例

```kotlin
// 推荐方式（统一 API）
ComposeArkUIViewController(env) { App() }
// 框架内部自动管理 enableCApi、rootContent、frameMgr

// 兼容方式（Deprecated API）
ComposeArkUIViewController(env, frameMgr, enableCApi, rootContent) { App() }
// 开发者手动传参
```
