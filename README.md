> [English](https://github.com/SpectrumQT/XXMI-Launcher/blob/main/README.md) | 简体中文
>
> 这是 XXMI Launcher 的中文版本。如果您需要英文版本，请点击上方的 English 链接。

<h1 align="center">XXMI 启动器</h1>

<h4 align="center">XXMI 的启动工具</h4>

<p align="center">
  <a href="#features">功能特点</a> •
  <a href="#installation">安装说明</a> •
  <a href="#included-model-importers">包含的模型导入器</a> •
  <a href="#support-this-project">支持项目</a> •
  <a href="#license">许可证</a>
</p>

## 免责声明

- **安全警告** — 某些敏感的杀毒软件可能会对 XXMI 的 **.exe** 或 **.dll** 文件触发[误报](https://learn.microsoft.com/en-us/defender-endpoint/defender-endpoint-false-positives-negatives)。由于项目没有资金来[满足](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control) 微软的[无尽贪婪](https://www.reddit.com/r/electronjs/comments/17sizjf/a_guide_to_code_signing_certificates_for_the/)，因此您可以选择直接使用、自行编译或放弃使用。

## 功能特点

- **一键管理** — 以统一且便捷的方式启动和管理所有支持的模型导入器
- **即插即用** — 自动配置任何支持的游戏并安装其 XXMI 实例
- **自定义启动** — 可以通过高级设置以几乎任何可能的方式配置游戏启动
- **自动更新** — 始终保持 XXMI 实例和启动器本身为最新版本
- **使用安全** — 验证 XXMI 库文件和自身下载内容的真实性

![xxmi-launcher](https://github.com/SpectrumQT/XXMI-Launcher/blob/main/public-media/XXMI%20Launcher.jpg)

## 安装说明

* **原生 Windows 应用程序**（仅适用于 **Windows**）
  1. 下载[最新版本](https://github.com/SpectrumQT/XXMI-Launcher/releases/latest)的 **XXMI-Launcher-Installer-Online-vX.X.X.msi**
  2. 双击运行 **XXMI-Launcher-Installer-Online-vX.X.X.msi**
  3. 点击**[快速安装]**将 **XXMI 启动器**安装到默认位置（`%AppData%\XXMI Launcher`），或使用**[自定义安装]**设置其他文件夹
  4. 在 **XXMI 启动器窗口**的游戏选择页面，点击所需的**游戏图标**将**模型导入器图标**添加到左上角
  5. 点击**模型导入器图标**打开模型导入器页面，然后按**[安装]**按钮下载并安装所选的模型导入器

* **便携版**（适用于 **Windows** 和通过 **WINE 9.22+** 运行的 **Linux**）
  1. 下载并安装[最新的 Microsoft Visual C++ 可再发行组件](https://aka.ms/vs/17/release/vc_redist.x64.exe)
  2. 下载[最新版本](https://github.com/SpectrumQT/XXMI-Launcher/releases/latest)的 **XXMI-Launcher-Portable-vX.X.X.zip**
  3. 将压缩包解压到所需位置（避免解压到 Program Files 文件夹！）
  4. 为方便使用，为 `Resources\Bin\XXMI Launcher.exe` 创建快捷方式并运行
  5. 在 **XXMI 启动器窗口**的游戏选择页面，点击所需的**游戏图标**将**模型导入器图标**添加到左上角
  6. 点击**模型导入器图标**打开模型导入器页面，然后按**[安装]**按钮下载并安装所选的模型导入器

## 包含的模型导入器

- [WWMI - 鸣潮模型导入器 GitHub](https://github.com/SpectrumQT/WWMI-Package)
- [ZZMI - 绝区零模型导入器 GitHub](https://github.com/leotorrez/ZZMI-Package)
- [SRMI - 崩坏：星穹铁道模型导入器 GitHub](https://github.com/SilentNightSound/SR-Model-Importer)
- [GIMI - 原神模型导入器 GitHub](https://github.com/SilentNightSound/GI-Model-Importer)
  
## 支持项目

**XXMI 项目**是合作的成果。请考虑支持相关开发者：

### XXMI 启动器：
- **创建者和维护者**：[SpectrumQT](https://github.com/SpectrumQT) ([Patreon](https://patreon.com/SpectrumQT))
### GIMI：
- **创建者**：[SilentNightSound](https://github.com/SilentNightSound) ([Ko-Fi](https://ko-fi.com/silentnightsound))
- **维护者**：[LeoTorrez](https://github.com/leotorrez) ([Ko-Fi](https://ko-fi.com/leotorrez)), [SinsOfSeven](https://github.com/SinsOfSeven) ([Ko-Fi](https://ko-fi.com/sinsofseven)), [Gustav0](https://github.com/Seris0) ([Ko-Fi](https://ko-fi.com/gustav0_)), [Nurarihyon](https://github.com/NurarihyonMaou) ([Ko-Fi](https://ko-fi.com/nurarihyonmaou))
### SRMI：
- **创建者**：[SilentNightSound](https://github.com/SilentNightSound) ([Ko-Fi](https://ko-fi.com/silentnightsound))
- **维护者**：[SinsOfSeven](https://github.com/SinsOfSeven) ([Ko-Fi](https://ko-fi.com/sinsofseven)), [LeoTorrez](https://github.com/leotorrez) ([Ko-Fi](https://ko-fi.com/leotorrez)), [Scyll](https://gamebanana.com/members/2644630) ([Ripe](https://gamebanana.com/members/2644630)), [Gustav0](https://github.com/Seris0) ([Ko-Fi](https://ko-fi.com/gustav0_))
### WWMI：
- **创建者和维护者**：[SpectrumQT](https://github.com/SpectrumQT) ([Patreon](https://patreon.com/SpectrumQT))
### ZZMI：
- **创建者**：[LeoTorrez](https://github.com/leotorrez) ([Ko-Fi](https://ko-fi.com/leotorrez)), [Scyll](https://gamebanana.com/members/2644630) ([Ripe](https://gamebanana.com/members/2644630)), [SilentNightSound](https://github.com/SilentNightSound) ([Ko-Fi](https://ko-fi.com/silentnightsound))
- **维护者**：[SinsOfSeven](https://github.com/SinsOfSeven) ([Ko-Fi](https://ko-fi.com/sinsofseven)), [LeoTorrez](https://github.com/leotorrez) ([Ko-Fi](https://ko-fi.com/leotorrez)), [Gustav0](https://github.com/Seris0) ([Ko-Fi](https://ko-fi.com/gustav0_)), [Scyll](https://gamebanana.com/members/2644630) ([Ripe](https://gamebanana.com/members/2644630)), [Satan1c](https://gamebanana.com/members/2789093) ([Patreon](https://patreon.com/Satan1cL))

## 许可证

XXMI 启动器基于 [GPLv3 许可证](https://github.com/SpectrumQT/WWMI-Launcher/blob/main/LICENSE) 开源。
