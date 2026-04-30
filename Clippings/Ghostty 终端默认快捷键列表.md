---
title: "Ghostty 终端默认快捷键列表"
source: "https://juejin.cn/post/7467618287381397567"
author:
  - "[[demo007x]]"
published: 2025-02-05
created: 2026-04-29
description: "Ghostty是一款兼具速度、丰富功能和原生特性的终端模拟器，由Mitchell Hashimoto利用业余时间开发。 原生特性：针对macOS和Linux设计，在macOS上使用Swift、AppK"
tags:
  - "clippings"
---
![image.png](https://p3-xtjj-sign.byteimg.com/tos-cn-i-73owjymdk6/389381a5e7304f928fa11f00a9ab7059~tplv-73owjymdk6-jj-mark-v1:0:0:0:0:5o6Y6YeR5oqA5pyv56S-5Yy6IEAgZGVtbzAwN3g=:q75.awebp?rk3s=f64ab15b&x-expires=1778033925&x-signature=YTVjSKTli304hakmm20eX8nPbio%3D)

Ghostty是一款兼具速度、丰富功能和原生特性的终端模拟器，由Mitchell Hashimoto利用业余时间开发。

1. **原生特性** ：针对macOS和Linux设计，在macOS上使用Swift、AppKit和SwiftUI编写GUI，Linux上则用Zig和GTK4 C API 。它使用原生UI组件，匹配各平台的标准键盘和鼠标快捷键，还能集成特定系统功能，如macOS上的Quick Look等。
2. **丰富功能** ：涵盖终端功能和应用程序功能。终端功能支持Kitty图形协议、通知模式切换、超链接等；应用程序功能包括原生标签页、分屏、macOS上的下拉式终端、主题切换等。
3. **速度表现** ：目标是与最快的终端模拟器处于同一水平，虽在不同基准测试中表现有差异，但整体不慢。“速度”包含启动时间、滚动速度等多方面。
4. **独特架构** ：核心是跨平台、C-ABI兼容的libghostty库，提供终端仿真、字体处理和渲染功能。macOS和Linux的GUI应用程序基于该库开发，这种架构实现了终端仿真和GUI的分离，未来还计划将libghostty作为独立稳定库发布，以支持其他终端模拟器项目。

Ghostty 提供了丰富的默认快捷键，用户可以通过这些快捷键快速执行各种操作。以下是 Ghostty 的默认快捷键列表，这些快捷键可以通过 `keybind` 配置进行自定义。

### 基本操作

- **`super+page_up`**: 向上滚动页面。
- **`super+page_down`**: 向下滚动页面。
- **`super+home`**: 滚动到顶部。
- **`super+end`**: 滚动到底部。
- **`super+t`**: 新建标签页。
- **`super+n`**: 新建窗口。
- **`super+w`**: 关闭当前终端界面（标签页或分割窗口）。
- **`super+shift+w`**: 关闭当前窗口。
- **`super+shift+enter`**: 切换分割窗口缩放。
- **`super+alt+shift+w`**: 关闭所有窗口。
- **`super+q`**: 退出 Ghostty。
- **`super+enter`**: 切换全屏模式。
- **`super+ctrl+f`**: 切换全屏模式。
- **`super+shift+left_bracket`**: 切换到上一个标签页。
- **`super+shift+right_bracket`**: 切换到下一个标签页。
- **`ctrl+tab`**: 切换到下一个标签页。
- **`ctrl+shift+tab`**: 切换到上一个标签页。
- **`super+equal`** 或 **`super+plus`**: 增加字体大小。
- **`super+minus`**: 减小字体大小。
- **`super+zero`**: 重置字体大小。
- **`super+c`**: 复制到剪贴板。
- **`super+v`**: 从剪贴板粘贴。
- **`super+a`**: 全选。
- **`super+k`**: 清空屏幕。
- **`super+comma`**: 打开配置文件。
- **`super+shift+comma`**: 重新加载配置文件。
- **`super+alt+i`**: 切换检查器。

### 分屏操作

- **`super+d`**: 在右侧新建分割窗口。
- **`super+shift+d`**: 在下方新建分割窗口。
- **`super+alt+right`**: 切换到右侧分割窗口。
- **`super+alt+left`**: 切换到左侧分割窗口。
- **`super+alt+up`**: 切换到上方分割窗口。
- **`super+alt+down`**: 切换到下方分割窗口。
- **`super+left_bracket`**: 切换到上一个分割窗口。
- **`super+right_bracket`**: 切换到下一个分割窗口。
- **`super+ctrl+left`**: 向左调整分割窗口大小。
- **`super+ctrl+right`**: 向右调整分割窗口大小。
- **`super+ctrl+up`**: 向上调整分割窗口大小。
- **`super+ctrl+down`**: 向下调整分割窗口大小。
- **`super+ctrl+equal`**: 使分割窗口大小相等。

### 光标和选择操作

- **`super+up`**: 跳到上一个提示符位置。
- **`super+down`**: 跳到下一个提示符位置。
- **`super+shift+up`**: 跳到上一个提示符位置。
- **`super+shift+down`**: 跳到下一个提示符位置。
- **`shift+up`**: 向上调整选择范围。
- **`shift+down`**: 向下调整选择范围。
- **`shift+left`**: 向左调整选择范围。
- **`shift+right`**: 向右调整选择范围。
- **`shift+page_up`**: 向上调整选择范围（翻页）。
- **`shift+page_down`**: 向下调整选择范围（翻页）。
- **`shift+home`**: 调整选择范围到行首。
- **`shift+end`**: 调整选择范围到行尾。

### 其他操作

- **`alt+left`**: 发送 `esc:b` 序列 (通常是向左移动一个单词)。
- **`alt+right`**: 发送 `esc:f` 序列 (通常是向右移动一个单词)。
- **`super+left`**: 发送 `text:\x01` (通常是移动到行首)。
- **`super+right`**: 发送 `text:\x05` (通常是移动到行尾)。
- **`super+alt+shift+j`**: `write_scrollback_file:open` 。
- **`super+shift+j`**: `write_scrollback_file:paste` 。

### 物理按键绑定

- `super+physical:one`: 跳转到标签页 1。
- `super+physical:two`: 跳转到标签页 2。
- `super+physical:three`: 跳转到标签页 3。
- `super+physical:four`: 跳转到标签页 4。
- `super+physical:five`: 跳转到标签页 5。
- `super+physical:six`: 跳转到标签页 6。
- `super+physical:seven`: 跳转到标签页 7。
- `super+physical:eight`: 跳转到标签页 8。
- `super+physical:nine`: 跳转到标签页 9。
- `super+physical:zero`: 跳转到最后一个标签页。

## 特殊按键说明

- **`super` 键**:
	- 在 macOS 系统上，通常是 **Command 键** ⌘。
		- 在 Windows 和 Linux 系统上，通常是 **Windows 键** 或 **Super 键** 。
- **`equal` 键**: 通常是键盘上的 **等号键** `=` 。
- **`plus` 键**: 通常是键盘上的 **加号键** `+` 。
- **`minus` 键**: 通常是键盘上的 **减号键** `-` 。
- **`comma` 键**: 通常是键盘上的 **逗号键** `,`。
- **`left_bracket` 键**: 通常是键盘上的 **左方括号键** `[`。
- **`right_bracket` 键**: 通常是键盘上的 **右方括号键** `]` 。
- **`zero` 键**: 通常是键盘上的 **数字键 0** 。
- **`alt` 键**:
	- 在 macOS 系统上，通常是 **Option 键** ⌥。
		- 在 Windows 和 Linux 系统上，通常是 **Alt 键** 。
- **`page_up` 键**: 通常是键盘上的 **翻页向上键** 。
- **`page_down` 键**: 通常是键盘上的 **翻页向下键** 。
- **`home` 键**: 通常是键盘上的 **Home 键** 。
- **`end` 键**: 通常是键盘上的 **End 键** 。

**关于物理按键** ：物理按键指的是键盘上 **实际的硬件按键** ，而不是操作系统根据键盘布局映射的逻辑按键。Ghostty 支持使用 `physical:` 前缀来指定 **物理按键码** ，例如 `super+physical:four` 表示绑定到键盘上物理位置为数字 4 的按键，而不是根据当前键盘布局映射的逻辑上的数字 4 键。使用物理按键绑定可以确保在不同键盘布局下，快捷键的行为保持一致。

## 注意事项

- **修饰键** ： 修饰键包括 `shift` 、 `ctrl` 、 `alt` 和 `super` ，可以与其它按键组合使用。
- **组合键序列** ： 可以使用 `>` 分隔多个按键，形成组合键序列。
- **物理按键码**: 使用 `physical:` 前缀可以指定物理按键码，而不是逻辑按键码。
- **自定义** ： 这些默认快捷键都可以通过 `keybind` 配置进行自定义，并且可以使用 `global:` 或 `all:` 前缀来调整快捷键的作用范围。