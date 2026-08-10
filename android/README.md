# Rhine-Lore 全内嵌安卓版

把整个 Rhine-Lore（演化引擎、存档、项目备份、AI 配置）打包进手机：

- Chaquopy 在 App 内运行现有 Python 代码（`src/rhine_lore` 纯标准库，无需
  Rhine-Vault）；
- Android WebView 加载打包进来的 `ui/dist`；
- 数据（演化存档 / 项目备份 / AI 配置）保存在 App 私有目录
  `filesDir/data`；
- AI 调用由手机直接请求 OpenAI 兼容接口（默认 DeepSeek），密钥只存本机；
- 完全离线于电脑：手机本身就是服务器，不需要 PC 或局域网。

## 架构

```text
Android App
├─ MainActivity        WebView -> http://127.0.0.1:8796/
├─ rhine_lore_launcher 设置环境变量并在线程里启动 serve()
└─ rhine_lore.server   内嵌模式（RHINE_LORE_EMBEDDED=1）：
   - 不启动/不依赖 Rhine-Vault
   - /lore-api/llm/* 直连 OpenAI 兼容 chat/completions
   - 数据目录由 RHINE_LORE_DATA_DIR 指向 filesDir/data
```

## 构建（本机环境已全部迁到 D 盘）

本机 Android 构建环境位于 D 盘：

- Android SDK：`D:\Android\Sdk`（platform-tools、android-34、build-tools 34.0.0）
- Gradle 8.7：`D:\Gradle\gradle-8.7`
- Gradle 缓存：`D:\GradleHome\.gradle`（`GRADLE_USER_HOME=D:\GradleHome`）
- Python 3.11：Chaquopy 构建用
  `C:/Users/BaiOS/AppData/Local/Programs/Python/Python311/python.exe`
  （见 `app/build.gradle` 的 `chaquopy.defaultConfig.buildPython`）

命令行构建（PowerShell）：

```powershell
$env:ANDROID_HOME = "D:\Android\Sdk"
$env:ANDROID_SDK_ROOT = "D:\Android\Sdk"
$env:GRADLE_USER_HOME = "D:\GradleHome"
cd E:\Project\Python\Rhine-Lore\android
.\gradlew.bat assembleDebug --no-daemon
```

产物：`android/app/build/outputs/apk/debug/app-debug.apk`

> `ui/dist` 会在构建时由 `copyWebAssets` 任务自动拷贝进 APK 资源，无需手动
> 处理；本机已验证可产出约 35 MB 的 debug APK（arm64-v8a + x86_64）。

## 已知边界（内嵌版）

- 资料库（Rhine-Vault）功能在手机上不可用：知识检索、提案/入库等页面会显示
  离线状态，写作与演化不受影响。
- 首次进入需在首页配置 AI 通道（DeepSeek/OpenAI 兼容），密钥保存在 App 内。
- 本版绑定 `127.0.0.1:8796`，仅 App 自身可访问；如需手机对外提供服务，
  把 `rhine_lore_launcher.py` 的 host 改为 `0.0.0.0` 并加防火墙放行。
- 当前状态：引擎、存储、直连模型在 PC 内嵌模式已跑通，APK 已在本机构建
  成功（内容含 Python 引擎与 Web 前端），真机安装验收仍待进行。
