# OHOS 平台单元测试详细指导

## 一、环境准备

### 1.1 必需工具

```bash
# OHOS SDK（二选一，已配置可跳过）
export OHOS_SDK_HOME=/path/to/openharmony
# 或
export DEVECO_STUDIO_HOME=/path/to/DevEco-Studio

# hdc（HarmonyOS Device Connector）—— 确认可用
hdc list targets
# 应输出设备序列号，如：0123456789ABCDEF

# Kotlin/Native OHOS 工具链（自动下载到 ~/.konan/）
# 版本：2.2.21-OH.0.1.0-02，构建时自动拉取
```

### 1.2 设备要求

- OHOS 真机或模拟器，已通过 USB 连接并授权调试
- 设备需支持 `hdc shell` 命令执行
- 设备 `/system/lib64/` 下需有标准 OHOS 动态库（`platformsdk/`、`ndk/`、`module/` 子目录）

### 1.3 验证环境

```bash
# 确认 Gradle 可正常配置 OHOS 目标
cd compose_multiplatform_core
./gradlew :collection:collection:ohosArm64MainKlibrary --dry-run
```

---

## 二、测试源集架构

OHOS 测试代码遵循 Kotlin Multiplatform 的源集层级：

```
commonTest                    # 所有平台共享的测试
  ↓ dependsOn
nonJvmTest                    # 非 JVM 平台共享（部分模块有此中间层）
  ↓ dependsOn
nativeTest                    # 所有 Kotlin/Native 平台共享（iOS + OHOS）
  ↓ dependsOn
ohosTest                      # OHOS 平台共享（arm64 + x64）
  ↓ dependsOn
ohosArm64Test                 # OHOS ARM64 专用（真机）
  ↓ dependsOn
ohosX64Test                   # OHOS X64 专用（模拟器/x64 设备）
```

> 注意：此层级由 `buildSrc/private/src/main/kotlin/androidx/build/AndroidXComposeMultiplatformExtensionImpl.kt` 中的 `configureOhosSourceSets()` 方法自动配置，模块启用 `ohos()` 后无需手动声明。

### 2.1 源集放置策略

| 测试代码特征                    | 应放在                                                  | 示例                                                             |
| ------------------------- | ---------------------------------------------------- | -------------------------------------------------------------- |
| 所有平台通用                    | `src/commonTest/kotlin/`                             | `ScatterMapTest.kt`、`SavedStateTest.kt`                        |
| 所有 Native 平台通用（不含 JVM/JS） | `src/nativeTest/kotlin/`                             | `SynchronizedTest.kt`、`DefaultViewModelProviderFactoryTest.kt` |
| OHOS 专用逻辑                 | `src/ohosArm64Test/kotlin/` 或 `src/ohosTest/kotlin/` | OHOS 特有 API 的测试                                                |

**关键约束：** `commonTest` 中的测试会自动被 OHOS 目标继承，无需额外操作。但需确保模块的 `build.gradle` 中源集依赖链正确配置（见 2.2 节）。

### 2.2 模块 build.gradle 配置

**测试依赖声明**（以典型 KMP 模块为例）：

```groovy
kotlin {
    sourceSets {
        commonTest {
            dependencies {
	            // kotlin.test 框架
                implementation(libs.kotlinTest)      
                // @Test 等注解
                implementation(libs.kotlinTestAnnotationsCommon)
                // 协程测试支持
                implementation(libs.kotlinCoroutinesTest) 
            }
        }

        nativeTest {
            dependsOn(commonTest)  // 确保继承 commonTest
        }

        // OHOS 源集由 buildSrc 的 configureOhosSourceSets() 自动配置
        // 无需手动声明 ohosTest / ohosArm64Test 的 dependsOn
    }
}
```

**注意：** 模块必须启用了 OHOS 目标（通过 `ohos()` 扩展），才会生成 OHOS 测试编译任务。检查模块 build.gradle 中是否有 `ohos()` 调用。

---

## 三、用例编写

### 3.1 基本测试结构

```kotlin
// src/commonTest/kotlin/androidx/mypackage/MyClassTest.kt
package androidx.mypackage

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import kotlin.test.assertFailsWith

class MyClassTest {

    @Test
    fun basicAssertion() {
        val result = MyClass.compute(1, 2)
        assertEquals(3, result)
    }

    @Test
    fun testWithNullables() {
        val value: String? = getValue()
        assertTrue(value != null)
        assertEquals("expected", value)
    }

    @Test
    fun testExceptionThrown() {
        assertFailsWith<IllegalArgumentException> {
            MyClass.invalidOperation()
        }
    }
}
```

### 3.2 Native 平台专用测试

当测试涉及 Kotlin/Native 特有 API（如 `Worker`、`AtomicInt`、`freeze`）时，放在 `nativeTest`：

```kotlin
// src/nativeTest/kotlin/androidx/mypackage/MyConcurrencyTest.kt
package androidx.mypackage

import kotlin.concurrent.AtomicInt
import kotlin.native.concurrent.Worker
import kotlin.native.concurrent.TransferMode
import kotlin.test.Test
import kotlin.test.assertEquals

class MyConcurrencyTest {
    @Test
    fun stressTest() {
        val workers = Array(4) { Worker.start() }
        val counter = AtomicInt(0)
        workers.forEach { worker ->
            worker.execute(TransferMode.SAFE, { counter }) { cnt ->
                repeat(100) {
                    cnt.value = cnt.value + 1
                }
            }
        }
        workers.forEach { it.requestTermination().result }
        // 注意：这不是原子操作，实际测试应使用 synchronized
    }
}
```

### 3.3 expect/actual 模式

当 `commonTest` 使用了 `expect` 声明时，需在 `nativeTest` 提供 `actual`：

```kotlin
// src/commonTest/kotlin/androidx/mypackage/TestUtils.kt
internal expect suspend fun testWithTimeout(
    timeoutMs: Long,
    block: suspend CoroutineScope.() -> Unit
)

// src/nativeTest/kotlin/androidx/mypackage/TestUtils.native.kt
internal actual suspend fun testWithTimeout(
    timeoutMs: Long,
    block: suspend CoroutineScope.() -> Unit
) = runBlocking {
    // KN debug 模式较慢，乘以 10 倍超时
    withTimeout(timeoutMs * 10, block)
}
```

### 3.4 平台排除注解

如需排除特定平台的测试（如不适用于 Web），使用 expect/actual 注解：

```kotlin
// src/commonTest/kotlin/IgnoreTargets.kt
internal expect annotation class IgnoreWebTarget()

// src/nativeTest/kotlin/IgnoreTargets.native.kt
internal actual annotation class IgnoreWebTarget  // Native 上为空注解，不排除

// 使用
@Test
@IgnoreWebTarget
fun testOnlyForNativeAndJvm() { ... }
```

### 3.5 OHOS 专用测试

针对 OHOS 特有逻辑（如 NAPI 桥接、ArkUI 互操作）的测试，放在 `ohosTest` 或 `ohosArm64Test`：

```kotlin
// src/ohosTest/kotlin/androidx/mypackage/OhosSpecificTest.kt
// 或 src/ohosArm64Test/kotlin/...  （仅 ARM64）
package androidx.mypackage

import kotlin.test.Test
import kotlin.test.assertNotNull

class OhosPlatformTest {
    @Test
    fun testOhosSpecificBehavior() {
        // 测试 OHOS 平台特有逻辑
    }
}
```

### 3.6 可用的测试工具库

| 库 | 用途 | 示例 |
|----|------|------|
| `kotlin.test` | 核心断言和 `@Test` | `assertEquals`, `assertTrue`, `assertFailsWith` |
| `kotlin.test.annotations-common` | 平台无关注解 | `@Test`, `@Ignore`, `@BeforeTest`, `@AfterTest` |
| `kotlinx-coroutines-test` | 协程测试 | `runTest { }`, `TestDispatcher` |
| `androidx.kruth:kruth` | Truth 风格断言（部分模块） | `assertThat(value).isEqualTo(expected)` |

---

## 四、用例编译

### 4.1 编译测试二进制

```bash
cd compose_multiplatform_core

# 编译指定模块的 OHOS 测试二进制
./gradlew :<module-path>:linkDebugTestOhosArm64

# 示例
./gradlew :collection:collection:linkDebugTestOhosArm64
./gradlew :compose:runtime:runtime:linkDebugTestOhosArm64
./gradlew :lifecycle:lifecycle-viewmodel:linkDebugTestOhosArm64
./gradlew :savedstate:savedstate:linkDebugTestOhosArm64
```

### 4.2 编译产物位置

```
out/androidx/<module-path>/build/bin/ohosArm64/debugTest/test.kexe
```

示例：

```
out/androidx/collection/collection/build/bin/ohosArm64/debugTest/test.kexe
out/androidx/compose/runtime/runtime/build/bin/ohosArm64/debugTest/test.kexe
```

### 4.3 检查二进制是否包含测试

```bash
# 使用 OHOS SDK 中的 llvm-nm 检查测试符号
LLVM_NM=/Users/shiqi1007/Library/OpenHarmony/Sdk/20/native/llvm/bin/llvm-nm
$LLVM_NM out/androidx/<module>/build/bin/ohosArm64/debugTest/test.kexe 2>/dev/null | \
  grep "kclass:.*Test\b" | head -10
```

如果输出为空，说明没有测试被编译进去，需检查源集依赖链是否正确。

### 4.4 常见编译问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `ohosArm64Test` task 不存在 | 模块未启用 `ohos()` 目标 | 在模块 build.gradle 中添加 `ohos()` |
| GC overhead limit exceeded | Gradle 内存不足 | 添加 `-Dorg.gradle.jvmargs="-Xmx4g"` |
| 测试二进制无测试符号 | `commonTest` 未连接到 `nativeTest` | 检查 `nativeTest.dependsOn(commonTest)` |
| 链接失败缺符号 | 测试依赖的模块未编译 | 先编译依赖模块 |

---

## 五、用例运行

### 5.1 推送测试二进制到设备

```bash
BINARY=out/androidx/<module>/build/bin/ohosArm64/debugTest/test.kexe
hdc file send "$BINARY" /data/local/tmp/test.kexe
hdc shell "chmod +x /data/local/tmp/test.kexe"
```

### 5.2 执行测试

```bash
hdc shell "export LD_LIBRARY_PATH=/system/lib64/platformsdk:/system/lib64/ndk:/system/lib64/module:/system/lib64 && \
  /data/local/tmp/test.kexe"
```

**关键点：** OHOS 上 Kotlin/Native 测试运行器的输出写入 **hilog**（OHOS 日志系统）而非 stdout，因此直接运行看不到输出。这是 OHOS KN 工具链的特殊行为，与 Linux/macOS 上的 KN 测试运行器不同。

### 5.3 查看测试结果

```bash
# 清空 hilog → 运行测试 → 获取结果
hdc shell "hilog -r"
hdc shell "export LD_LIBRARY_PATH=/system/lib64/platformsdk:/system/lib64/ndk:/system/lib64/module:/system/lib64 && /data/local/tmp/test.kexe"
sleep 1
hdc shell "hilog -x | grep 'test.kexe/Konan_main'"
```

输出格式为 GTest 风格：

```
[==========] Running 22 tests from 2 test cases.
[----------] 20 tests from FloatingPointEqualityTest
[ RUN      ] FloatingPointEqualityTest.testFloat_arbitraryValueEquality
[       OK ] FloatingPointEqualityTest.testFloat_arbitraryValueEquality (0 ms)
...
[==========] 22 tests from 2 test cases ran. (4477 ms total)
[  PASSED  ] 22 tests.
```

### 5.4 一键运行脚本

可创建辅助脚本简化流程：

```bash
#!/bin/bash
# run_ohos_test.sh <module-path>
# 例如: ./run_ohos_test.sh collection:collection

set -e

MODULE=$1
if [ -z "$MODULE" ]; then
    echo "Usage: $0 <module-path>"
    echo "Example: $0 collection:collection"
    exit 1
fi

MODULE_DIR=$(echo "$MODULE" | tr ':' '/')
BINARY="out/androidx/${MODULE_DIR}/build/bin/ohosArm64/debugTest/test.kexe"

echo ">>> Building $MODULE ..."
./gradlew ":${MODULE}:linkDebugTestOhosArm64" -Dorg.gradle.jvmargs="-Xmx4g"

echo ">>> Deploying to device ..."
hdc file send "$BINARY" /data/local/tmp/test.kexe
hdc shell "chmod +x /data/local/tmp/test.kexe"

echo ">>> Running tests ..."
hdc shell "hilog -r"
hdc shell "export LD_LIBRARY_PATH=/system/lib64/platformsdk:/system/lib64/ndk:/system/lib64/module:/system/lib64 && /data/local/tmp/test.kexe"

sleep 1
echo ""
echo ">>> Results:"
hdc shell "hilog -x | grep 'test.kexe/Konan_main'" | grep -E '\[ *PASSED *\]|\[ *FAILED *\]|test cases ran'
```

### 5.5 Kotlin/Native 测试运行器支持的参数

| 参数 | 说明 |
|------|------|
| `--ktest.filter=<glob>` | 过滤执行的测试，如 `--ktest.filter='*Synchronized*'` |
| `--ktest.verbose` | 详细输出（注意：在当前 OHOS KN 工具链上可能触发 Signal 6） |
| `--list-tests` | 列出所有测试用例（注意：在当前 OHOS KN 工具链上可能无输出） |

> **稳定性注意：** 部分 `--ktest_*` 参数在当前 OHOS KN 工具链（2.2.21-OH.0.1.0-02）上可能不稳定。`--ktest.filter` 在需要单独运行特定测试时最实用。

### 5.6 测试二进制的动态库依赖

测试二进制（ELF ARM aarch64）链接了以下 OHOS 系统动态库：

| 库 | 设备路径 |
|----|---------|
| `libace_napi.z.so` | `/system/lib64/platformsdk/` |
| `libc++_shared.so` | `/system/lib64/` |
| `libc.so` | `/system/lib64/` |
| `libqos.so` | `/system/lib64/ndk/` |
| `libhitrace_ndk.z.so` | `/system/lib64/ndk/` |
| `libhilog_ndk.z.so` | `/system/lib64/ndk/` |

这些库不在 `/system/lib64/` 默认搜索路径中，因此必须设置 `LD_LIBRARY_PATH` 包含 `platformsdk`、`ndk`、`module` 子目录。

---

## 六、测试报告与覆盖率

### 6.1 测试报告

当前 Kotlin/Native 测试运行器输出 GTest 格式文本到 hilog，不直接生成 JUnit XML 报告。可通过以下方式获取结构化结果：

**方式一：解析 hilog 输出**

```bash
# 保存 hilog 输出到文件
hdc shell "hilog -x | grep 'test.kexe/Konan_main'" > test_output.txt

# 统计通过/失败
grep -c "\[       OK \]" test_output.txt   # 通过数
grep -c "\[  FAILED  \]" test_output.txt   # 失败数
grep "test cases ran" test_output.txt      # 汇总行
```

**方式二：转换为 JUnit XML（CI 集成）**

可通过脚本将 GTest 格式输出转换为标准 JUnit XML：

```python
#!/usr/bin/env python3
"""将 hilog GTest 输出转换为 JUnit XML"""
import sys, re
from xml.etree.ElementTree import Element, SubElement, ElementTree

def parse_gtest_output(lines):
    testsuite = Element('testsuite')
    current_class = None
    total = failed = 0
    time_total = 0.0

    for line in lines:
        m = re.search(r'(\d+) tests from (\S+)', line)
        if m:
            current_class = m.group(2)
        m = re.search(r'\[ RUN      \] (\S+)\.(\S+)', line)
        if m:
            classname, name = m.group(1), m.group(2)
            tc = SubElement(testsuite, 'testcase',
                          classname=classname, name=name)
            total += 1
        m = re.search(r'\[       OK \] \S+\.\S+ \((\d+) ms\)', line)
        if m:
            time_total += int(m.group(1))
        m = re.search(r'\[  FAILED  \] (\S+\.\S+)', line)
        if m:
            failed += 1
            # 标记最后一个 testcase 为失败
            cases = testsuite.findall('testcase')
            if cases:
                failure = SubElement(cases[-1], 'failure')
                failure.text = 'FAILED'

    testsuite.set('tests', str(total))
    testsuite.set('failures', str(failed))
    testsuite.set('time', f'{time_total/1000:.3f}')
    return testsuite

# 使用：hilog_output 的 grep 结果通过 stdin 传入
tree = ElementTree(parse_gtest_output(sys.stdin))
tree.write('test-report.xml', encoding='unicode', xml_declaration=True)
```

### 6.2 覆盖率

当前项目**未配置覆盖率工具**。Kotlin/Native 的覆盖率采集方案有以下选项：

| 方案 | 原理 | 可行性 | 限制 |
|------|------|--------|------|
| **编译器插桩 + llvm-profdata** | KN 支持 `-Xcoverage` 编译选项，生成 `.profraw` 文件 | 需确认 OHOS KN fork 是否支持 | 需从设备回传 profraw 文件 |
| **llvm-cov** | 对编译产物使用 llvm 工具链分析 | 可行，但需要源码编译信息 | 需要配合 `-Xcoverage` 使用 |
| **Kover（JVM only）** | Kotlin Coverage 工具 | **不适用** | 仅支持 JVM/Android |
| **自定义插桩** | 在关键路径手动埋点统计 | 可行但成本高 | 维护成本高 |

**推荐路线（待建设）：**

```bash
# 1. 编译时启用覆盖率（如果 OHOS KN 工具链支持）
./gradlew :<module>:linkDebugTestOhosArm64 \
  -Pkotlin.native.binary.enableCoverage=true

# 2. 运行后从设备拉取覆盖率数据
hdc file recv /data/local/tmp/default.profraw ./coverage.profraw

# 3. 使用 llvm 工具生成报告
LLVM_DIR=/Users/shiqi1007/Library/OpenHarmony/Sdk/20/native/llvm/bin
$LLVM_DIR/llvm-profdata merge -sparse coverage.profraw -o coverage.profdata
$LLVM_DIR/llvm-cov report test.kexe -instr-profile=coverage.profdata
$LLVM_DIR/llvm-cov show test.kexe -instr-profile=coverage.profdata -format=html > coverage.html
```

> **现状：** 覆盖率采集是待建设的能力。建议与 Kotlin/Native OHOS 工具链团队确认 `-Xcoverage` 的支持情况，再决定实施方案。

---

## 七、完整示例：新增一个 OHOS 测试

以在 `compose/ui/ui-text` 模块中新增 OHOS 原生测试为例：

```bash
# 1. 确认模块有 nativeTest 目录
ls compose/ui/ui-text/src/nativeTest/kotlin/
# 已有：androidx/compose/ui/text/WeakKeysCacheTest.kt

# 2. 新增测试文件（放在 nativeTest，OHOS 和 iOS 共享）
```

```kotlin
// compose/ui/ui-text/src/nativeTest/kotlin/androidx/compose/ui/text/MyNewTest.kt
package androidx.compose.ui.text

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class MyNewTest {
    @Test
    fun testNativeBehavior() {
        val result = someNativeOperation()
        assertTrue(result.isNotEmpty())
    }

    private fun someNativeOperation(): String {
        return "ohos-native"
    }
}
```

```bash
# 3. 编译
./gradlew :compose:ui:ui-text:linkDebugTestOhosArm64 -Dorg.gradle.jvmargs="-Xmx4g"

# 4. 部署运行
hdc file send out/androidx/compose/ui/ui-text/build/bin/ohosArm64/debugTest/test.kexe \
  /data/local/tmp/test.kexe
hdc shell "chmod +x /data/local/tmp/test.kexe"
hdc shell "hilog -r"
hdc shell "export LD_LIBRARY_PATH=/system/lib64/platformsdk:/system/lib64/ndk:/system/lib64/module:/system/lib64 && /data/local/tmp/test.kexe"
sleep 1
hdc shell "hilog -x | grep 'test.kexe/Konan_main'"
```

---

## 八、已验证通过的模块

以下模块已在 OHOS 真机上验证通过（2026-05-06）：

| 模块 | 测试数 | 通过 | 失败 | 耗时 |
|------|--------|------|------|------|
| `compose/runtime/runtime` | 22 | 22 | 0 | ~4.5s |
| `lifecycle/lifecycle-viewmodel` | 31 | 31 | 0 | ~6ms |
| `savedstate/savedstate` | 338 | 338 | 0 | ~110ms |
| `collection/collection` | 1844 | 1844 | 0 | ~60s |

测试用例全部来自上游 AndroidX 官方的 `commonTest` / `nativeTest`，非 OHOS 适配新增。`ohosArm64Test` 目录目前为空，OHOS 专属测试待建设。

---

## 九、快速参考卡

```
┌──────────────────────────────────────────────────────┐
│              OHOS 单元测试速查                         │
├──────────────────────────────────────────────────────┤
│ 测试代码位置                                          │
│   跨平台    → src/commonTest/kotlin/                  │
│   Native   → src/nativeTest/kotlin/                  │
│   OHOS专用  → src/ohosArm64Test/kotlin/               │
├──────────────────────────────────────────────────────┤
│ 编译                                                  │
│   ./gradlew :<module>:linkDebugTestOhosArm64          │
├──────────────────────────────────────────────────────┤
│ 产物                                                  │
│   out/androidx/<m>/build/bin/ohosArm64/debugTest/     │
│   test.kexe (ELF ARM aarch64)                        │
├──────────────────────────────────────────────────────┤
│ 运行                                                  │
│   hdc file send test.kexe /data/local/tmp/            │
│   hdc shell "LD_LIBRARY_PATH=... test.kexe"           │
├──────────────────────────────────────────────────────┤
│ 查看结果                                              │
│   hdc shell "hilog -x | grep Konan_main"              │
│   ⚠ 输出在 hilog，不在 stdout                         │
├──────────────────────────────────────────────────────┤
│ 依赖                                                  │
│   kotlin("test") + kotlinx-coroutines-test            │
├──────────────────────────────────────────────────────┤
│ 覆盖率                                                │
│   暂无配置，待 OHOS KN 工具链支持                      │
└──────────────────────────────────────────────────────┘
```
