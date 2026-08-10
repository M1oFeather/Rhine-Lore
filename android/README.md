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

## 本地模拟器验收（可选）

本机已装好：模拟器 37.1.11、android-34 x86_64 系统镜像
（均在 `D:\Android\Sdk`），以及 AEHD 加速驱动
（`D:\Android\Sdk\extras\google\Android_Emulator_Hypervisor_Driver`，
需管理员运行 `silent_install.bat` 安装一次）。

```powershell
$env:ANDROID_AVD_HOME = "D:\Android\avd"

# 首次创建 AVD
& "D:\Android\Sdk\cmdline-tools\latest\bin\avdmanager.bat" create avd `
    -n rhine_test -k "system-images;android-34;default;x86_64" -d pixel_5

# 无窗口启动
& "D:\Android\Sdk\emulator\emulator.exe" -avd rhine_test -no-window `
    -no-audio -no-boot-anim -gpu swiftshader_indirect -no-snapshot

# 安装并启动 App
& "D:\Android\Sdk\platform-tools\adb.exe" install -r app\build\outputs\apk\debug\app-debug.apk
& "D:\Android\Sdk\platform-tools\adb.exe" shell am start -n com.rhinelore.app/.MainActivity
```

本机模拟器验收已通过：WebView 正常加载首页，内嵌 Python 服务在
`127.0.0.1:8796` 返回 200，前端资源与 LLM 配置接口均正常。

## 已知边界（内嵌版）

- 资料库在手机端使用内嵌模式（`embedded-vault.json` 存于 App 私有目录）：
  草稿、送审、入库、检索、设定文档生成全部可用，无需外部 Rhine-Vault；
  顶部资料库状态显示“资料库可用”。
- “书架”支持导入 TXT 长篇小说：后端按章节分文件存储
  （`files/data/books/<book_id>/chapters/*.txt`），百万字级小说按章加载，
  并提供 AI 续写 / 改写 / 扩写，以及全书角色 / 设定 / 事实 / 伏笔分析
  （需配置 AI 通道；未配置时提供离线高频角色提取与模板回复）。
- 内嵌服务监听 `0.0.0.0:8796`：同一份数据可直接在局域网浏览器打开
  （`http://<手机IP>:8796/`），即手机端与网页版共用同一个后端与书库。
- AI 面板内置 **DeepSeek 登录助手**：WebView 打开 DeepSeek 控制台，登录后
  复制 API Key 会被自动捕获并写入本机 AI 配置。
- 首次进入需在首页配置 AI 通道（DeepSeek/OpenAI 兼容），密钥保存在 App 内。
- 本版绑定 `127.0.0.1:8796`，仅 App 自身可访问；如需手机对外提供服务，
  把 `rhine_lore_launcher.py` 的 host 改为 `0.0.0.0` 并加防火墙放行。
- 当前状态：引擎、存储、直连模型在 PC 内嵌模式已跑通，APK 已在本机构建
  成功（内容含 Python 引擎与 Web 前端），真机安装验收仍待进行。
