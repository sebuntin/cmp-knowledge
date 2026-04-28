---
title: "带着问题学，Compose附带效应(Side Effect)一探究竟"
source: "https://juejin.cn/post/7464050299616755775?searchId=20260428000012A06E9047DFA3FEFC1843"
author:
  - "[[RainyJiang]]"
published: 2025-01-26
created: 2026-04-28
description: "前言 各位同学，好久不见，因为工作和身体的原因导致很久都没写文。趁着春节即将到来之际才有时间放松下，这里笔者提前祝大家2025新年快乐，愿君在蛇年里，似灵蛇灵动，事业如藤蔓攀升，生活若繁花盛绽，好运常"
tags:
  - "clippings"
---
### 前言

各位同学，好久不见，因为工作和身体的原因导致很久都没写文。趁着春节即将到来之际才有时间放松下，这里笔者提前祝大家2025新年快乐，愿君在蛇年里，似灵蛇灵动，事业如藤蔓攀升，生活若繁花盛绽，好运常伴不歇。

OK, 那么我们进入主题吧

使用 *Jetpack Compose* 开发已经有挺长一段时间了，随着对它的不断深入学习，笔者逐渐体会到了它作为声明式 *UI* 框架的独特魅力。与传统的命令式编程不同，声明式编程通过描述 *UI* 的状态来定义界面。然而，在实际开发过程中，我们经常需要执行一些操作，这些操作会对 *UI* 状态之外的系统产生影响。这种操作在 *Jetpack Compose* 中被称为 **Side Effects** ，直译过来是“副作用”。

当初看到这个词时，笔者的第一反应是它可能带有负面的含义，毕竟“副作用”在日常生活中通常意味着不良影响。然而，随着学习的深入， *Compose* 中的“副作用”并不是负面的。相反，它们指的是一些额外的效果或行为，帮助我们在特定的上下文中完成必要的任务。因此，官方更倾向于将它们称为“附带效应”（ **Side Effects** ）。然而，出于个人习惯，笔者还是更喜欢称之为“副作用”，文章内容也都以“副作用”来描述，毕竟这对于本人来说更顺口，也更贴近日常的技术讨论，只是叫法而已，大家不用太过纠结哈。

当然，可以看看笔者之前的 *Compose* 系列相关文章，非常期待各位大佬的宝贵建议，帮助笔者继续提升和完善这段探索之旅。

- [初学Compose：无缝衔接xml的神奇魔法](https://juejin.cn/post/7288151382533390395 "https://juejin.cn/post/7288151382533390395")
- [带着问题学，Compose中的State一网打尽](https://juejin.cn/post/7399530589987504128 "https://juejin.cn/post/7399530589987504128")

OK，话不多说，凭借网络上很多已有的文章博客分享了对 *Side Effects* 的看法，本文依旧是以问题的形式，带领大家探究 *Jetpack Compose* 中的 *Side Effects* 处理，以及分享笔者自己学习过程中遇到的一些疑问，从而加深自己对Compose的 *Side Effects* 的使用与理解。

![Side Effect大纲.png](https://p6-xtjj-sign.byteimg.com/tos-cn-i-73owjymdk6/e0c4df8645dc4f93855edbb6615e5d8e~tplv-73owjymdk6-jj-mark-v1:0:0:0:0:5o6Y6YeR5oqA5pyv56S-5Yy6IEAgUmFpbnlKaWFuZw==:q75.awebp?rk3s=f64ab15b&x-expires=1777509410&x-signature=F70W%2BglwMbh5YnwMdylaSGWriTo%3D)

### Q1.什么是 Jetpack Compose 中的副作用（Side Effect）？

我们每次去接触到新的知识的时候，总要知道这个到底是什么吧， **如何定义** ？

这样吧，我们先撇一眼官方的回答；在计算机科学中，副作用指的是一个函数或表达式在返回结果值的同时，还对其外部状态产生了影响。而在 Jetpack Compose 中， **副作用主要是指在组合函数（Composables）中执行的、对其输入和输出范围之外的状态或系统产生影响的操作** 。处理这些副作用可以确保我们的应用在面对各种状态变化时能够正常运行。

#### 那么此时问题来了，我相信大部分同学此时都会有这样的想法，什么样的操作被认为是副作用？

通过了解我们知道，副作用通常指的是那些会引起 UI 更新之外的变化，这些操作可能会影响应用的其他部分，如数据库、网络请求、文件系统操作、日志记录等。

![副作用定义.png](https://p6-xtjj-sign.byteimg.com/tos-cn-i-73owjymdk6/99d074812bf94f99b0d04f5cb87ff0fc~tplv-73owjymdk6-jj-mark-v1:0:0:0:0:5o6Y6YeR5oqA5pyv56S-5Yy6IEAgUmFpbnlKaWFuZw==:q75.awebp?rk3s=f64ab15b&x-expires=1777509410&x-signature=ILXZPtKX5S3H33UD2y5HuYtHHGI%3D)

- **外部状态改变：** 比如说我们调用网络 API、数据库操作、文件写入的时候，改变了外部系统的状态，这种操作通常会在界面上引发某些变化，但是它本身不属于 UI 的一部分。
- **日志记录：** 在 UI 组件中记录一些日志信息，可能会被认为是副作用。
- **动画/过渡的触发：** 通过 Compose 触发的动画可能会影响视图的状态或外部系统。
- **协程启动：** 启动后台协程进行异步操作，特别是当协程触发 UI 更新时。

#### 那么此时肯定又有同学要问了，不同于传统的 Android 开发，Jetpack Compose 中的副作用有何特别之处呢？

![副作用特别之处.png](https://p6-xtjj-sign.byteimg.com/tos-cn-i-73owjymdk6/8bad64d002ce41a990fbeaacedd48d74~tplv-73owjymdk6-jj-mark-v1:0:0:0:0:5o6Y6YeR5oqA5pyv56S-5Yy6IEAgUmFpbnlKaWFuZw==:q75.awebp?rk3s=f64ab15b&x-expires=1777509410&x-signature=HTIwqHEGCLPcVu6NedMC8GKHJPg%3D)

- **声明式UI与副作用解耦**:
	副作用和 UI 更新解耦，副作用操作通过特定的 API 来控制生命周期和执行时机。 *Jetpack Compose* 强调声明式 UI，即 UI 由状态驱动，而不再是通过命令式的代码操作视图。
	在传统 Android 中， **视图更新往往伴随副作用，如在 *Activity* 或 *Fragment* 中处理网络请求后更新 UI** 。而在 *Compose* 中，副作用（如网络请求、数据库操作等）与 UI 状态的管理是分开的，副作用通常通过特定的机制来管理，如 *LaunchedEffect* 等，当然这篇文章会对这些API下面会逐个分析。
- **生命周期和重组管理**:
	副作用由 *LaunchedEffect* 、 *SideEffect* 等函数自动与生命周期和重组绑定，避免了传统 Android 中的生命周期错误和副作用重复执行问题。
- **更简洁的异步操作管理**:
	副作用操作（如网络请求）与 UI 更新被清晰分开，避免了复杂的线程和 UI 更新同步问题。
- **可组合性**:
	*Compose* 中的副作用可以在多个层级的 *Composable* 中管理，并与状态紧密绑定。

### Q2. Compose 提供了哪些处理副作用的 API？

副作用在 *Compose* 中是不可避免的，不过别担心！ *Compose* 贴心地提供了一套 **Effect API** ，帮助开发者 **以可控且可预测的方式在 Composable 函数中处理副作用** 。为了让大家对这些 API 有个初步概念，笔者先整理了一张表格，大家可以先大概瞄一眼，心里有个大概印象。

接下来，我们就逐个拆解，简单聊聊它们的作用和使用场景

|  | 场景 | 用途示例 |
| --- | --- | --- |
| **SideEffect** | **每次成功重组后** 运行副作用，并且副作用与 UI 状态无关 | 日志记录、触发外部 API 调用 |
| **LaunchedEffect** | **组合阶段** 启动副作用，通常用于启动一次性任务或异步操作 | 执行协程中的异步任务，监听特定键的变化并重新执行副作用 |
| **DisposableEffect** | 当需要在组件 **进入或退出组合** 时执行逻辑，同时清理资源 | 注册或解绑监听器、关闭文件流、取消订阅 |
| **rememberUpdatedState** | 当副作用需要访问 **最新状态值** ，而状态可能随时间变化时 | 避免使用过时的 *lambda* 或状态值 |
| **produceState** | 当需要从 **外部异步源** 加载数据，并将结果存储为 *Compose* 的 *State* 时 | 在 UI 中展示网络或数据库加载的数据 |
| **rememberCoroutineScope** | 当需要启动协程，并希望其生命周期与当前组合保持一致时 | 在用户交互事件（如点击按钮）中启动协程任务 |
| **snapshotFlow** | 将 *Compose* 的状态（ *State* ）转换为 *Flow* ，便于与非 *Compose* 的代码交互 | 观察 *Compose* 状态变化并触发下游流处理 |

#### SideEffect

主要用于在 **每次成功的重组后** 执行一些与UI状态无关的逻辑，保证只会在 **主线程上运行** ，且只在组合成功完成时触发。啥意思呢？就是 **无论状态是否发生改变，只要重组完成， *SideEffect* 都会被调用一次** ；它通常用来将 *Compose* 的内部状态同步到非 *Compose* 的外部系统。

还不够清晰，没关系，下面我们举一个🌰来说明，通过 *SideEffect* 在每次重组后同步外部的调试日志，输出当前计数器的状态。

```kotlin
体验AI代码助手 代码解读复制代码//模拟下外部状态
val externalState =  mutableListOf<String>()
@Composable
fun CounterWithLogging() {
    var count by remember { mutableStateOf(0) }
​
    Column(modifier = Modifier.fillMaxSize()
        .padding(16.dp)) {
        Text("Counter:$count", modifier = Modifier.padding(8.dp))
        Button(onClick = { count ++ }) {
            Text("Increment")
        }
​
        // 使用 SideEffect 在每次重组后同步外部状态
        SideEffect {
            externalState.add("Count updated to $count")
            println("External State Synced: $externalState")
        }
    }
​
}
​
@Preview(showBackground = true)
@Composable
fun PreviewCounterWithLogging() {
    CounterWithLogging()
}
```

> 这里 *count* 是一个使用 *remember* 创建的可变状态，每次用户点击按钮， *count* 增加 1，此时UI 会进行重组，使用 *SideEffect* 将计数器的最新状态同步到外部的 *externalState* 列表中，并打印日志，每次用户点击按钮触发 *count* 的变化后， *SideEffect* 都会在重组完成后执行。

此时用户连续点击了按钮6次，日志输出如下:

![25B1B9CE-A863-48b0-B48F-38140120DB1B.png](https://p6-xtjj-sign.byteimg.com/tos-cn-i-73owjymdk6/13a46dc4529b4ea9890dbb83be7e54d4~tplv-73owjymdk6-jj-mark-v1:0:0:0:0:5o6Y6YeR5oqA5pyv56S-5Yy6IEAgUmFpbnlKaWFuZw==:q75.awebp?rk3s=f64ab15b&x-expires=1777509410&x-signature=uC5xxX8EwhIvG9P%2BzlUa28sXChw%3D)

可以看到 *SideEffect* 会在每次重组后同步最新的 *count* 到外部的 *externalState* 。

通过这个例子，不难发现， *SideEffect* 非常适合以下场景:

- **日志记录** ：在每次状态更新时记录调试日志，方便排查问题。
- **调试信息同步** ：将最新的 Compose 状态同步到外部工具、分析平台，或非 Compose 系统。
- **轻量级任务** ：处理与 UI 状态无关的简单任务，例如统计点击次数等等。

此外，我们再思考一个问题， **为什么不要在 *SideEffect* 中处理大量繁重或耗时的操作？**

- **阻塞主线程** ： *SideEffect* 始终在主线程上运行，如果在其中执行耗时的操作（如网络请求、文件读写、大量计算等），会阻塞 UI 更新，导致界面卡顿或掉帧，直接影响用户体验
- **违反职责单一原则** ： *SideEffect* 的职责是执行副作用操作，而繁重任务应交由其他专用 API（如 *LaunchedEffect* 或后台线程）处理。滥用 *SideEffect* 会导致代码难以维护，甚至可能引入线程安全问题
- **触发重组的潜在问题** ：如果繁重操作间接修改了 *Compose* 状态（例如改变一个 *mutableState* ），可能触发额外的重组，甚至造成无限循环或性能问题

![SideEffect处理大量耗时操作.png](https://p6-xtjj-sign.byteimg.com/tos-cn-i-73owjymdk6/85d5f8e468a8415aa86fa2978b07a647~tplv-73owjymdk6-jj-mark-v1:0:0:0:0:5o6Y6YeR5oqA5pyv56S-5Yy6IEAgUmFpbnlKaWFuZw==:q75.awebp?rk3s=f64ab15b&x-expires=1777509410&x-signature=yIlFvkkdWJmG8AFzAe85Z0jDLn8%3D)

#### LaunchedEffect

既然 *SideEffect* 无法处理繁重的操作，那有没有那种可以执行耗时任务操作的副作用API呢？有，这不 *LaunchedEffect* 它来了，它是一个挂载在 *Compose* 生命周期的可组合函数，启动协程任务， **用于在界面组件的生命周期中执行一些只需运行一次或基于特定条件触发的操作** 。这样解释可能过于官方了，简单来说，就是在Compose中处理协程相关的任务，比如说我们需要异步加载网络数据，比如说执行初始化的一些操作。它的核心功能如下:

![LaunchedEffect.png](https://p6-xtjj-sign.byteimg.com/tos-cn-i-73owjymdk6/28a806971cc540f2ac575c845460ba20~tplv-73owjymdk6-jj-mark-v1:0:0:0:0:5o6Y6YeR5oqA5pyv56S-5Yy6IEAgUmFpbnlKaWFuZw==:q75.awebp?rk3s=f64ab15b&x-expires=1777509410&x-signature=xnFSmVMkWk%2BeDsFEwtEyPFtQwMs%3D)

- **只执行一次** ： 当 *Composable* 组件首次进入组合（ *Composition* ）时， *LaunchedEffect* 中的代码块会被触发执行
- **响应依赖参数key变化** ： 如果传递的 *key* 依赖发生变化， *LaunchedEffect* 会重新启动。也就是说，它的执行是依赖于 *key* 的变化
- **生命周期感知** ： 当组件退出组合时， *LaunchedEffect* 中的协程会自动取消，以避免资源泄漏
- **协程支持** ： 它运行在协程上下文中，因此特别适合处理异步任务，比如网络请求、数据库查询等

下面还是用个🌰来实践下， 我们模拟下 *LaunchedEffect* 在组件首次启动时异步加载数据，并将结果显示在界面上

```kotlin
体验AI代码助手 代码解读复制代码@Composable
fun DataLoaderScreen() {
    // 用于保存加载的数据
    var data by remember { mutableStateOf("Loading...") }
​
    // 用于记录加载状态
    var isLoading by remember { mutableStateOf(true) }
​
    // 使用 LaunchedEffect 加载数据
    LaunchedEffect(Unit) {
        try {
            // 模拟网络请求
            data = fetchDataFromNetwork()
        } catch (e: Exception) {
            data = "Failed to load data: ${e.message}"
        } finally {
            isLoading = false
        }
    }
​
    // 展示加载状态或数据
    if (isLoading) {
        Text(text = "Loading...", style = MaterialTheme.typography.bodyMedium)
    } else {
        Text(text = data, style = MaterialTheme.typography.bodyLarge)
    }
}
​
suspend fun fetchDataFromNetwork(): String {
    // 模拟延迟2秒，例如网络请求或数据库查询
    delay(2000)
    return "Fetched data from server"
}
```

这里小小总结下，如果我们在 *Compose* 中需要处理网络数据，或着从数据库加载信息，都可以使用 *LaunchedEffect* ；在组件初始化时预加载一些数据，也可以使用 *LaunchedEffect* 。这里笔者做了一个表格， *LaunchedEffect* 主要适用于如下场景

| 场景 | 描述 |
| --- | --- |
| **异步任务的触发** | 处理需要运行在后台线程的任务，比如从网络获取数据或从数据库加载信息 |
| **初始化操作** | 在组件加载时执行必要的初始化逻辑，比如设置监听器、预加载数据等 |
| **事件响应** | 根据某些依赖（例如状态或参数）的变化，触发某种业务逻辑 |

#### DisposableEffect

*DisposableEffect* 作为另一个与生命周期相关的 API，它和 *LaunchedEffect* 类似，而 *LaunchedEffect* 大家可以理解为协程版的 *DisposableEffect* 。 *DispoableEffect* 主要用于在组件的生命周期执行一些需要清理的操作。比如说，注册监听器、打开文件、连接数据库等操作，需要在组件销毁时关闭或者释放资源，以防止内存泄漏。原理也很好理解，当组件首次进入界面时， *DisposableEffect* 会执行一些操作（比如打开摄像头或监听事件)；当组件离开界面（销毁时）， *DisposableEffect* 会自动执行清理代码（如关闭摄像头、注销监听器等）

还是举个简单的🌰，如果我们需要在 *Composeable* 销毁的时候清理一些资源，卸载监听器或者传感器， *DisposableEffect* 提供了一个便捷的方式，确保我们的代码不会因为资源未释放而造成内存泄漏

```kotlin
体验AI代码助手 代码解读复制代码@Composable
fun NetworkStateListener() {
    val context = LocalContext.current
    val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
​
    DisposableEffect(Unit) {
        val networkCallback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                Log.d("NetworkState", "网络已连接")
            }
​
            override fun onLost(network: Network) {
                Log.d("NetworkState", "网络已断开")
            }
        }
​
        connectivityManager.registerDefaultNetworkCallback(networkCallback)
​
        onDispose {
            Log.d("NetworkState", "注销网络监听器")
            connectivityManager.unregisterNetworkCallback(networkCallback)
        }
    }
    Text("监听网络状态变化")
}
​
```

写起来也非常简单，通过 *onDisposable* 注销监听器，防止内存泄漏

#### rememberCoroutineScope

如果说 *LaunchedEffect* 是用于执行那些短期一次性的协程任务，那么 *rememberCoroutineScope* 适用于需要启动协程并在 Composable 生命周期内持续存在的场景。简单来说， *rememberCoroutineScope* 在 *Composable* 组件中创建和管理一个协程作用域，使得我们能够启动协程并在组件生命周期内保持该协程的有效性。

它适用于在 UI 事件（比如按钮点击）触发时启动异步任务，或者在需要与 UI 状态相关的地方使用协程，可以看看下面的🌰

```kotlin
体验AI代码助手 代码解读复制代码@Composable
fun ButtonWithCoroutine() {
    val coroutineScope = rememberCoroutineScope()
​
    Button(onClick = {
        coroutineScope.launch {
            // 假设这是一个网络请求或耗时操作
            delay(2000L)
            Log.d("Coroutine", "操作完成")
        }
    }) {
        Text("点击开始任务")
    }
}
```

值得注意的是，我们使用 *rememberCoroutineScope* ，返回一个协程作用域，它会和 *Composeable* 生命周期绑定，本质上是与 *LifecycleOwner* 相关联的，也就是说，它会在组件离开界面的时自动取消，所以我们要 **确保 *UI* 不会因为协程未结束而引发异常或资源泄露** 。

#### rememberUpdatedState

关于 *rememberUpdateState* ，初看这个 *API* 的时候,你会觉得怎么写的那么简单，就两行代码，只创建了个 *mutableState* 对象，并且每次去更新值，相当于存储并更新某个值的当前最新状态。这有啥用，恰恰相反，这个API非常实用，它解决了在长时间运行的任务中访问 UI 状态时常见的“旧值问题”。

```kotlin
体验AI代码助手 代码解读复制代码@Composable
fun <T> rememberUpdatedState(newValue: T): State<T> = remember {
    mutableStateOf(newValue)
}.apply { value = newValue }
```

啥，这是啥意思呢？通过学习我们都知道，如果某些状态发生变化的时候， *Compose* 会进行重组来更新UI。但是， **状态的变化并不总是立即反映在长时间运行的操作或任务中** ，比如协程、后台线程、或者事件监听器等等。假设你在 *Composable* 中启动了一个协程来执行某个操作（例如加载数据），如果你在协程启动后改变了某个 UI 状态，直接访问这个状态可能会导致你拿到的是 **旧的状态值** 。这就可能出现状态更新和实际操作不同步的情况，从而引发一些不可预期的问题。 *rememberUpdatedState* 正是为了解决这个问题，它可以帮助我们确保在长时间运行的任务中，始终获取到 **最新的状态值** 。

所以在实际开发中，当我们遇到异步任务与 UI 状态变更不同步的问题时，不妨尝试使用 *rememberUpdatedState* 来解决这个问题，一写一个不吱声🙋。

#### produceState

这是 *Compose* 提供的一个状态管理 *API*,用来在 *Composable* 内部创建并管理异步状态，它可以监听外部数据源（比如网络请求、数据库、传感器等），当数据更新时，UI 也会自动刷新。其实说白了，就是可以 **将外部非 *Compose* 状态转换成 *Compose* 状态**

![produceState.png](https://p6-xtjj-sign.byteimg.com/tos-cn-i-73owjymdk6/4c5121ba64a7463b80ebbb8899f1329d~tplv-73owjymdk6-jj-mark-v1:0:0:0:0:5o6Y6YeR5oqA5pyv56S-5Yy6IEAgUmFpbnlKaWFuZw==:q75.awebp?rk3s=f64ab15b&x-expires=1777509410&x-signature=tW7LP2QJzlJ0rstBOygosAXUU5I%3D)

*produceState* 的作用就是 **启动一个协程，监听数据变化，并更新状态** ，这让我们可以直接在 *Composeble* 中管理状态。

比如说我想监听下系统时间，每秒刷新一次，可以使用 *produceState*

```kotlin
体验AI代码助手 代码解读复制代码@Composable
fun ClockScreen() {
    val currentTime by produceState(initialValue = "Loading...") {
        while (true) {
            value = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
// 每秒更新一次

        }
    }
​
    Text(text = "Current Time: $currentTime")
}
```

这段代码 **不需要ViewModel** ，但依然能自动更新 UI，非常适合那些 **需要实时变化的状态** ！

总的来说， *produceState* 让 **异步数据管理更简单** ，在某些场景下可以替代 *ViewModel* ，不过如果数据需要在多个 *Composable* 共享， *ViewModel* 还是更合适！

#### snapshotFlow

*snapshotFlow* 是 *Compose* 提供的 ***State* -> *Flow*** 的转换工具，等等，那有同学就会说，这不是和 *produceState* 类似嘛，非也非也， *produceState* 可以将任意非 *Compose* 状态转换为 *Compose* 状态，而 *snapshotFlow* 只能将 *Compose* 状态转换为 *Flow*, 其次它是转换成了协程，所以不能直接用于UI绑定，需要和 *collect* 配合使用， **和 *Flow* 生态兼容** ，可以轻松结合 *debounce()* 、 *map()* 、 *flatMapLatest()* 等操作

这样以来，可以做到自动去重，防止 UI 频繁重组导致的无意义触发。实际在Compose开发中，可以用于做防抖操作，比如说，我们要监听输入框变化，但不希望每次输入的触发搜索请求API接口，而是等用户停止输入500ms再请求的，代码如下：

```kotlin
体验AI代码助手 代码解读复制代码@FlowPreview
@Composable
fun SearchBox() {
    var query by remember { mutableStateOf("") }
​
    LaunchedEffect(Unit) {
        snapshotFlow { query }
// 500ms 防抖，避免频繁请求

            .collectLatest { searchText ->
                searchApi(searchText) // 触发网络请求
            }
    }
​
    TextField(
        value = query,
        onValueChange = { query = it }
    )
}
​
suspend fun searchApi(query: String) {
    Log.d("SearchBox", "搜索: $query")
}
```

> 这里 *debounce(500)* 确保只有在用户停止输入 500ms 后才会触发搜索，避免频繁请求API

### Q3.SideEffect 如何确保在重组时，应用状态与外部系统始终保持一致？

通过前文，相信我们已经了解到， *SideEffect* 提供了一种简单、安全的方式，将 *Compose* 的内部状态与外部系统连接起来，这在调试和状态同步中非常实用。然而，由于 *SideEffect* 会在每次重组时被调用，确实可能导致数据重复等等问题。针对这一点，笔者有一个小小的思考： **如何确保在重组过程中，状态与外部系统始终保持一致，而不会引发重复或错误更新呢？**

当然，为了要确保 *Compose* 的应用状态与外部系统的一致性，笔者总结了以下几个原则

#### 1\. 幂等设计

每次重组都会调用 *SideEffect* ，这可能会导致外部状态被重复写入。所以既然如此，确保外部操作是 **幂等** 的非常重要。当然有同学会问， **幂等** 是啥东西？这里小小解释下， **幂等操作** 是指相同的输入多次执行，不会对结果造成重复影响。比方说：

- 写日志时，每次写入相同内容应覆盖之前的内容，或者确保不重复写入
- 数据库更新时，确保同样的更新语句不会多次改变状态
	此时，我们对前面的代码进行一波小小的改动：
```
体验AI代码助手 代码解读复制代码var lastLoggedValue by remember { mutableStateOf(-1) }
       SideEffect {
           if (lastLoggedValue != count) {
               println("Count updated to $count")
               lastLoggedValue = count
           }
       }
```

> 只有 *count* 值发生实际变化的时候，才会更新日志

#### 2.确保线程安全

*SideEffect* 总是在主线程上运行，但外部系统可能涉及多线程交互（例如网络请求、数据库操作）。因此，需要确保外部操作的线程安全性。

**这里是笔者推荐的做法，当然具体的做法以实际项目开发情况为主：**

- 我们可以使用线程安全的容器（如 *ConcurrentLinkedQueue* 等）
- 或者将复杂的逻辑交给协程，比如说通过 *LaunchedEffect* 执行

#### 3\. 可以使用 remember 保存外部状态

外部状态容器（如列表、队列等）应通过 *remember* 管理，以确保它在重组中保持一致。这里再小小的改下代码：

```kotlin
体验AI代码助手 代码解读复制代码val externalState = remember { mutableStateListOf<String>() }
SideEffect {
    externalState.add("Count updated to $count")
    println("External State: $externalState")
}
```

这样的话 *externalState* 的内容会随着 *count* 的变化更新，但不会因重组丢失。

#### 避免递归问题

如果我们在 *SideEffect* 里面引起状态的再次变化，可能导致无限重组循环。

```arduino
体验AI代码助手 代码解读复制代码SideEffect {
    count++ // 修改状态会触发重组，从而再次调用 SideEffect，导致循环
}
```

所以一定要确保 *SideEffect* 里的逻辑是 **只读的** ，或者只影响 *Compose* 外部系统。

好了，总结下， **我们可以通过幂等操作、线程安全的设计和状态检查，来确保外部系统与应用状态的一致性** 。

### Q4. 如果我的操作依赖于一个动态变化的参数,LaunchedEffect会如何响应？

通过上文我们都已经知道 *LaunchedEffect* 通常可以用来执行一次性的异步耗时任务，但是，我们思考下，如果 **我的操作是依赖于动态变化的参数，就是需要传递不同的参数去执行对应的任务， *LaunchedEffect* 如何响应** ？下面我们一起来探讨一下

*LaunchedEffect* 是一个将代码块与 *Composable* 生命周期绑定的可组合函数，当它首次执行时， *LaunchedEffect* 会启动一个协程，并运行代码块中的内容，此时如果依赖项发生变化， *LaunchedEffect* 会重新启动协程并重新执行相应的任务。简单来说， *LaunchedEffect* 会在 *Composable* 被组合时执行，或者在其依赖的键（ *key* ）发生变化时重新执行，并且它与 *Compose* 的生命周期管理密切集成，确保在组件离开组合时，协程会自动取消，避免内存泄漏

此外， *LaunchedEffect* 可以接受一个或多个依赖项作为参数，当这些依赖项发生变化时， *LaunchedEffect* 会重新启动其协程。与 *remember* 一样， *LaunchedEffect* 的执行是受其依赖项的控制的。这意味着，如果我们希望某些操作依赖于动态变化的参数，例如用户输入、外部事件或者网络状态等，只需要将这些参数作为 *LaunchedEffect* 的键传递即可

这么一大段话解释，不配个🌰是不是说不过去。下面我们稍微改下上文中 *LaunchedEffect* 的代码，假设我们需要根据一个动态变化的参数(例如 *userId*)从网络中获取用户数据，当用户id发生变化的时候，我们希望重新发起请求并刷新UI

```kotlin
体验AI代码助手 代码解读复制代码@Composable
fun UserDetailScreen(userId: String) {
    // 保存用户数据的状态
    var userData by remember { mutableStateOf<User?>(null) }
    // 加载状态
    var isLoading by remember { mutableStateOf(true) }
    // 错误信息
    var errorMessage by remember { mutableStateOf<String?>(null) }
​
    // 使用 LaunchedEffect，监听 userId 的变化
    LaunchedEffect(userId) {
        try {
            // 模拟异步加载用户数据
            userData = fetchUserData(userId)
        } catch (e: Exception) {
            errorMessage = "Failed to load user data: ${e.message}"
        } finally {
            isLoading = false
        }
    }
​
    // UI
    if (isLoading) {
        CircularProgressIndicator()
    } else if (errorMessage != null) {
        Text(text = errorMessage ?: "Unknown error", color = MaterialTheme.colorScheme.error)
    } else {
        userData?.let {
            Text("User Name: ${it.name}")
            Text("User Email: ${it.email}")
        }
    }
}
​
// 模拟网络请求获取用户数据
suspend fun fetchUserData(userId: String): User {
// 模拟网络请求延时

    return User(userId, "Rainy Jiang", "jiangshiyuxs@gamil.com")
} 
data class User(val id: String, val name: String, val email: String)
```

上面的代码中， *LaunchedEffect(userId)* 用来监听 *userId* 的变化。当 *userId* 变化时， *LaunchedEffect* 会重新启动协程并发起新的异步请求，从而加载新的用户数据并更新 UI。

可能有同学这个时候就会说了，实际开发中，可能有多个动态变化的参数，既然 *LaunchedEffect* 可以添加多个依赖项，它会响应任意依赖项的变化么？答案是毋庸置疑的，还是刚刚的例子，此时假设我们不仅需要根据 *userId* 加载用户数据，还需要根据 *sessionToken* 来验证用户的身份。

```kotlin
体验AI代码助手 代码解读复制代码// 监听 userId 和 sessionToken 的变化
   LaunchedEffect(userId, sessionToken) {
       try {
           userData = fetchUserProfile(userId, sessionToken)
       } catch (e: Exception) {
           errorMessage = "Error: ${e.message}"
       } finally {
           isLoading = false
       }
   }
```

此时，如果这两个参数中的任何一个发生变化， *LaunchedEffect* 会取消当前的协程并启动一个新的协程来重新加载数据。 当然需要注意的，在依赖项频繁变化时， **如果异步任务比较耗时，可能会导致协程启动和取消的频繁切换，从而带来性能开销** 。因此，在设计时要小心高频变化的参数。

合理使用 *LaunchedEffect* ，我们能够以更简洁和声明式的方式处理动态变化的参数，并确保 UI 和异步任务的同步管理，减少了手动生命周期管理的复杂性

### Q5. rememberCoroutineScope 和 LaunchedEffect有何不同？

首先他们都是 *Compose* 中启动协程的 *Side Effect API* ，但它们的作用机制不同，这里笔者给一个表格来简单对比下

| API | **适用场景** | **作用** | **生命周期** |
| --- | --- | --- | --- |
| *rememberCoroutineScope* | **用户交互（按钮点击、滑动等）触发的协程** | 提供一个 *CoroutineScope* ，可以在 UI 事件中手动启动协程 | **不会随重组重启，作用域与 Composable 绑定** |
| *LaunchedEffect* | **基于 Compose 状态变化或生命周期触发的协程** | 监听 *key* 变化，并在变化时自动启动协程 | **绑定到 *Composable* 生命周期， `key` 变化时重启** |

他们最大的不同，就跟车一样， *rememberCoroutineScope* 作为手动挡，需要我们自己手动启动协程， **不会随重组销毁或重启** ，可以在 *Composable* 内持续使用；而 *LaunchedEffect* 就如自动挡一样，会在变化时自动启动协程，并绑定到 *Composable* 生命周期中。

**那我们什么时候使用 *rememberCoroutineScope* 而不是 *LaunchedEffect* ？**

一句话概括，如果你需要 **用户交互触发的异步任务** ，用 *rememberCoroutineScope* ，如果你希望 **UI 状态变化时自动执行任务** ，用 *LaunchedEffect* 。是不是有点抽象，没关系，下面笔者还是给个表格，各位同学看一眼大致就明白了

| **场景** | **使用 *rememberCoroutineScope*** | **使用 *LaunchedEffect*** |
| --- | --- | --- |
| **按钮点击触发任务** | ✅ **手动启动协程** | ❌ 不适合 |
| **滚动、滑动事件触发** | ✅ **与用户交互相关** | ❌ |
| **组件初始化时执行一次性任务** | ❌ | ✅ **自动触发** |
| **状态 (`state`) 变化时触发任务** | ❌ | ✅ **依赖 `key` 变化** |
| **定时任务、监听状态更新** | ❌ | ✅ |
| **不同点击事件共享一个协程作用域** | ✅ | ❌ |

小小总结下， *rememberCoroutineScope* 适用于响应用户交互（点击、滚动）并手动启动协程，它不会因重组而重启。 *LaunchedEffect* 适用于在 *Composable* 生命周期或 *key* 变化时执行任务，它会随 *key* 变化重启。

### Q6. 有什么场景是ProduceState特别适用的？

很多人听说， **“只要把非 Compose 状态转换成 Compose 状态，就用 *produceState* ”** ，结果遇到具体需求时还是一头雾水，没错说的就是本人，不知道该不该上。其实， *produceState* 主要用在 **“外部数据源驱动 UI”** 的场景，比如网络请求、数据库监听、实时数据流等。为了更直观，下面举几个实际开发中常见的例子，帮大家理清思路。

#### 社交应用：获取用户个人资料

在社交应用(如微博，朋友圈，聊天软件之类的)，用户界面需要从服务器获取用户信息

**需求如下** ：

- 当 *userId* 变化时，自动重新加载用户信息
- 确保 UI 始终显示最新数据
- 处理加载状态，防止 UI 闪烁
```kotlin
体验AI代码助手 代码解读复制代码@Composable
fun UserProfileScreen(userId: String) {
    val userInfo by produceState(initialValue = "加载中...", userId) {
        value = fetchUserInfo(userId) ?: "用户不存在"
    }
​
    Column {
        Text(text = userInfo)
    }
}
​
// 模拟一下API 请求
suspend fun fetchUserInfo(userId: String): String? {
// 模拟网络延迟

    return if (userId == "123") "用户：张三" else null
}
```

✅ **为什么**

- *userId* 变化时，自动重新加载，不需要手动触发
- 防止不必要的重组，避免 UI 卡顿
- 更清晰的状态管理，相比 *remember + LaunchedEffect* 组合更直观

#### 直播/股票 App：实时更新数据

在直播平台、股票交易或新闻推送类应用中，我们经常需要去 **订阅 WebSocket 或流数据**

**需求如下** ：

- 订阅股票价格流，并在 UI 中实时更新
- 避免因 *Composable* 重组导致订阅失效
- 组件销毁时自动清理订阅，防止内存泄漏
```kotlin
体验AI代码助手 代码解读复制代码@Composable
fun StockPriceScreen(stockSymbol: String) {
    val stockPrice by produceState(initialValue = "加载中...", stockSymbol) {
        stockPriceFlow(stockSymbol).collect { newPrice ->
            value = "当前股价：$newPrice"
        }
    }
​
    Text(text = stockPrice)
}
​
// 模拟股票价格流
fun stockPriceFlow(stockSymbol: String): Flow<Double> = flow {
    while (true) {
        if (stockSymbol == "300750") {
            emit(Random.nextDouble(100.0, 500.0)) // 生成随机股价
        } else {
            emit(Random.nextDouble(200.0,1000.0))
        }
// 每秒更新一次

    }
}
```

✅ **为什么**

- 保证 *WebSocket* 订阅在 *Composable* 生命周期内可控
- 自动管理数据流变化， *UI* 绑定状态更清晰
- 避免重复创建 *Flow* 订阅，节省资源

#### 位置服务 App：实时获取 GPS 坐标

在外卖、打车、地图应用中，我们需要 **实时获取用户的 GPS 位置** ，并在 UI 中更新。

**需求如下：**

- 实时获取用户位置，且 *Composable* 重新组合时不会丢失数据
- 位置变化时，自动触发 UI 更新
- 避免内存泄漏（监听器应该在 *Composable* 销毁时清理）
```kotlin
体验AI代码助手 代码解读复制代码@Composable
fun LocationTrackerScreen() {
    val location by produceState(initialValue = "定位中...") {
        locationFlow().collect { newLocation ->
            value = "当前位置：$newLocation"
        }
    }
​
    Text(text = location)
}
​
// 模拟 GPS 位置流
fun locationFlow(): Flow<String> = flow {
    while (true) {
        emit("纬度: ${Random.nextDouble(20.0, 50.0)}, 经度: ${Random.nextDouble(100.0, 150.0)}")
// 每 2 秒更新一次

    }
}
```

✅ **为什么**

- 适合持续性数据流，保证 UI 数据始终最新
- 避免生命周期问题， *produceState* 作用域结束时自动停止 *Flow*
- 比 *LaunchedEffect + remember* 更简洁，数据绑定直观

#### 聊天应用：监听最新消息

在即时通讯应用（如 WhatsApp、微信）中，需要监听并显示 **最新的聊天消息** 。

**需求如下：**

- 用户进入聊天界面后，实时接收消息更新
- 组件销毁时自动取消监听，防止泄漏
- 避免不必要的重复请求
```kotlin
体验AI代码助手 代码解读复制代码@Composable
fun ChatScreen(chatId: String) {
    val latestMessage by produceState(initialValue = "暂无消息", chatId) {
        chatMessagesFlow(chatId).collect { newMessage ->
            value = "最新消息：$newMessage"
        }
    }
​
    Text(text = latestMessage)
}
​
// 模拟聊天消息流
fun chatMessagesFlow(chatId: String): Flow<String> = flow {
    //聊天灵魂3连问
    val messages = listOf("你好！", "在吗？", "今晚有空一起吃饭吗？")
    for (msg in messages) {
        emit(msg)
// 每 3 秒推送一条消息

    }
}
​
​
```

✅ **为什么**

- 只需要传入 *chatId* ，即可监听最新消息，无需手动管理 *Flow*
- 避免 *Composable* 重组时重复订阅，节省资源
- 当 *chatId* 变化时，自动切换到新的聊天会话

### Q7. 谈谈副作用 API 的最佳实践？

好了，前面说了这么多关于学习副作用中遇到的疑惑，而且副作用这块作为 *Compose* 学习至关重要的一环，在实际开发中如何更好的去使用它，当然笔者在这过程中也遇到了各种各样奇奇怪怪的问题，这些问题不仅帮助笔者加深了对副作用的理解，也促使笔者不断优化代码和总结经验，能为各位同学提供一些启发。

#### 在实际开发中，如何避免滥用副作用 API？

- **需要清晰的职责分工**
	每个副作用 API 都有特定的使用场景，确保选择正确的 API。例如：
	- 使用 *LaunchedEffect* 启动首次异步任务，而不是 *SideEffect* 。
		- 对于绑定生命周期，退出需要清理的逻辑，优先使用 *DisposableEffect* 。
- **最小化副作用逻辑** ： 副作用中应该只包含必要的逻辑，避免在副作用内做复杂计算或更新多个状态。
- **避免多余的 API 嵌套** ： 不要将多个副作用 API 无意义地嵌套。例如，避免在 *LaunchedEffect* 中启动新的协程，这种行为会导致逻辑混乱。
	```kotlin
	体验AI代码助手 代码解读复制代码// 不推荐
	LaunchedEffect(Unit) {
	    launch { 
	       //你的逻辑 do something
	    }
	}
	// 推荐
	LaunchedEffect(Unit) {
	    //你的逻辑 do something
	}
	```

#### 如何确保副作用仅在预期的范围内影响状态或系统？

- **限制副作用的作用范围** ： 避免副作用不必要地影响其他外部系统。尽量将副作用与特定的组合树节点绑定，减少全局影响。
- **明确 `key` 参数 的设计** ： 对于 *LaunchedEffect* 和 *DisposableEffect* 等依赖 需要依赖 *key* 的 API，确保 *key* 的选择准确。如果 *key* 不准确，会导致意外的重新启动或无效的执行。
```kotlin
体验AI代码助手 代码解读复制代码//错误示例：可能导致每次重组都重新执行
LaunchedEffect(true) { 
    fetchData() 
}
//正确示例：将 \`key\` 绑定到正确的状态
LaunchedEffect(userId) { 
    fetchDataForUser(userId) 
}
```
- **避免直接更新外部状态** ： 副作用中不要直接修改外部不可变的状态，应通过 *State* 或其他响应式方式更新 UI。

#### 有哪些常见的陷阱或误区是我们在处理副作用时需要注意的？

**误区 1：滥用 *rememberCoroutineScope***

在组合中使用 *rememberCoroutineScope* 时，需要确保手动管理协程的生命周期。否则容易导致内存泄漏。解决方案如下：

- 只在与用户交互相关的场景使用，如点击事件。
- 对于生命周期管理明确的场景，优先使用 *LaunchedEffect* 。

**误区 2：副作用频繁触发**

如果 *key* 的依赖频繁变化，可能导致 *LaunchedEffect* 或 *DisposableEffect* 反复重启，影响性能。解决方案如下：

- 谨慎选择 *key* 的依赖，避免在不必要的重组中重新执行。
- 使用 *rememberUpdatedState* 确保获取最新值，而不重新启动副作用。
	```kotlin
	体验AI代码助手 代码解读复制代码val latestValue = rememberUpdatedState(value)
	LaunchedEffect(Unit) {
	    while (isActive) {
	        println(latestValue.value) // 始终是最新值
	    }
	}
	```

**误区 3：忽略副作用的清理**

如果副作用创建了资源（如监听器或协程），未正确清理会导致内存泄漏。解决方案如下：

- 使用 *DisposableEffect* 并确保 *onDispose* 完成清理工作。
```kotlin
体验AI代码助手 代码解读复制代码DisposableEffect(Unit) {
    val listener = SomeListener()
    listener.register()
    onDispose {
        listener.unregister() // 确保清理掉
    }
}
```

**误区 4：在副作用中直接修改 Compose 状态**

副作用中直接修改 *Compose* 状态（如 *mutableStateOf* ）可能引发死循环。解决方案如下：

- 确保状态的更新与副作用的触发互相独立，避免循环依赖。

### 总结

好了，说了这么多，我们在实际开发中，想用好 *Compose* 的副作用 API，其实就是几个关键点。首先，别让副作用掺和太多事儿，它就应该专心干自己的活， *UI* 的事情让 *UI* 管，逻辑清楚了，后续调试才不崩溃。其次，副作用也讲究“分工对口”：短期跑完就结束的用 *LaunchedEffect* ，那种常驻型的就交给 *rememberCoroutineScope* ，需要清理资源的，记得 *DisposableEffect* ，异步任务里，状态要用 *rememberUpdatedState* ，防止拿到旧值，别用错了工具。

再就是多试试，别怕折腾，尤其在状态和组合频繁变化的时候，跑一跑看副作用稳不稳。最后，还是那句话，如果你的代码比较复杂，自己都觉得绕，就一定要写点注释，解释清楚“为啥这么写”，不然时间长了，连自己都看不懂，后续同事看了更得抓狂！

#### 相关文章

- [(官方)Compose中的附带效应](https://link.juejin.cn/?target=https%3A%2F%2Fdeveloper.android.google.cn%2Fdevelop%2Fui%2Fcompose%2Fside-effects%3Fhl%3Dzh-cn "https://developer.android.google.cn/develop/ui/compose/side-effects?hl=zh-cn")
- [Compose编程思想 -- Compose中的附带效应以及协程使用](https://juejin.cn/post/7353464483233316902?searchId=202408201006246A931639DCDCB990C392 "https://juejin.cn/post/7353464483233316902?searchId=202408201006246A931639DCDCB990C392")
- [Jetpack Compose Side Effect：如何处理副作用](https://juejin.cn/post/6930785944580653070?searchId=20240820100203C56579E997AB9F988493 "https://juejin.cn/post/6930785944580653070?searchId=20240820100203C56579E997AB9F988493")
- [Jetpack Compose 中的副作用（side effects）](https://juejin.cn/post/7338645701658804261?searchId=2024081918482273A5AE27531FC3375E26#heading-11 "https://juejin.cn/post/7338645701658804261?searchId=2024081918482273A5AE27531FC3375E26#heading-11")