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

## 构建（需要 Android Studio 或 Android SDK）

1. 安装 [Android Studio](https://developer.android.com/studio)（自带 SDK），
   或安装 Android SDK 并设置 `ANDROID_HOME`。
2. 打开本项目目录 `android/`（Android Studio 会自动同步 Gradle 与 Chaquopy）。
3. 首次构建会下载 Gradle、Android 依赖和 Chaquopy Python 运行时（需网络）。
4. 构建 APK：菜单 Build -> Build Bundle(s) / APK(s) -> Build APK(s)，
   或命令行：

```powershell
cd android
.\gradlew.bat assembleDebug
```

产物：`android/app/build/outputs/apk/debug/app-debug.apk`

> `gradle-wrapper.jar` 已随仓库提供；`ui/dist` 会在构建时由
> `copyWebAssets` 任务自动拷贝进 APK 资源，无需手动处理。

## 已知边界（内嵌版）

- 资料库（Rhine-Vault）功能在手机上不可用：知识检索、提案/入库等页面会显示
  离线状态，写作与演化不受影响。
- 首次进入需在首页配置 AI 通道（DeepSeek/OpenAI 兼容），密钥保存在 App 内。
- 本版绑定 `127.0.0.1:8796`，仅 App 自身可访问；如需手机对外提供服务，
  把 `rhine_lore_launcher.py` 的 host 改为 `0.0.0.0` 并加防火墙放行。
- 当前工程为“后端已本地验证、APK 构建待你机器验证”状态：引擎、存储、直连
  模型在 PC 上以内嵌模式跑通，Android 侧需在装有 SDK 的机器上构建后再做真机
  验收。
