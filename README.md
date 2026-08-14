<h1 align="center">🌊 Rhine-Lore</h1>

<p align="center">
  <em>本地优先的中文写作工作室 · 演化沙盘 · TXT 书架 · AI 续写</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Web-Vue%203%20%2B%20Element%20Plus-42b883?style=flat-square" alt="Vue 3 + Element Plus">
  <img src="https://img.shields.io/badge/Android-API%2026%2B-brightgreen?style=flat-square" alt="Android API 26+">
  <img src="https://img.shields.io/badge/Version-0.2.1-purple?style=flat-square" alt="Version 0.2.1">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Android-lightgrey?style=flat-square" alt="Platforms">
</p>

---

## 📖 简介

**Rhine-Lore** 是一个本地优先的中文写作工作室。它把“写正文”、“让故事自己演化”、
“像读小说一样追更”、“导入并续写长篇小说”放进同一个工具里：

- **正文**：章节阅读/编辑、字号/行距/护眼主题、章节目录、自动保存与磁盘备份；
- **演化沙盘**：回合制自动推进故事，角色相遇、冲突、结盟、背叛，分支可手动选择
  或交给命运骰子，同一颗种子得到同一个故事；
- **小说阅读**：像追更一样读演化正文，读到末尾一键生成下一章，支持引导与重写；
- **TXT 书架**：导入百万字级 TXT，自动按“第X章 / Chapter”拆章，按章加载，
  支持 AI 续写 / 改写 / 扩写，并建立全书角色 / 设定 / 事实 / 伏笔档案；
- **资料库**：本机内嵌知识库，草稿 → 送审 → 入库 → 检索全流程可用；
- **全内嵌安卓版**：Chaquopy 在 App 内运行 Python 引擎，手机离线可用。

> 数据默认全部保存在本地（`data/` 目录或 App 私有目录），不依赖云端。

---

## ✨ 核心特性

| 模块 | 说明 |
| --- | --- |
| 故事项目 | 章节、世界观、角色卡、故事地图、对话创作、待处理问题 |
| 正文阅读/编辑 | 阅读/编辑双模式、字号/行距/白/米黄/夜间主题、章节导航、字数统计 |
| 演化沙盘 | 确定性随机种子、回合推进、分支选择、自动播放、沙盘观演 |
| 小说阅读 | 有限视角（只看主角亲历）、章节条、生成下一章、重新生成本章、全局引导 |
| TXT 书架 | 自动拆章（无标题按字数分节）、百万字级按章存储与加载、阅读进度记忆 |
| AI 创作 | 续写 / 改写 / 扩写、全书角色/设定/事实/伏笔分析、文风与一致性约束 |
| AI 助手 | 工具式对话：可导入 TXT、新建项目、追加章节、添加角色/设定、保存资料，支持附件 |
| 版本管理 | 项目与 TXT 书支持 Git 式快照/回滚，AI 写操作前自动备份，恢复前再备份当前状态 |
| 资料库 | 内嵌知识库（workspace / 草稿 / 送审 / 入库 / 检索 / 设定文档） |
| AI 通道 | DeepSeek V4 / OpenAI 兼容，支持快速、均衡、深度等级；未配置时使用离线模板 |

---

## 🚀 运行（源码）

要求：Python 3.10+（仅使用标准库，无需安装依赖）。

```bash
# Windows
start.bat
# 或手动
python main.py --host 0.0.0.0 --port 8786

# Linux / macOS
python3 main.py --host 0.0.0.0 --port 8786
```

浏览器打开 `http://127.0.0.1:8786/`；同一局域网设备访问
`http://<本机IP>:8786/`。

## 📦 发行包

| 平台 | 包 | 说明 |
| --- | --- | --- |
| Windows x64 | `Rhine-Lore-v0.2.1-win-x64.zip` | 解压后运行 `start.bat` |
| Linux x64 | `Rhine-Lore-v0.2.1-linux-x64.tar.gz` | 解压后运行 `./start.sh` |
| Android | `app-release.apk` | 全内嵌版，安装即用 |

> 发布包见仓库 GitHub Releases 或本地 `dist/` 目录。

## 🤖 AI 配置

首页右上角 **AI 面板**：选择 DeepSeek / OpenAI / 自定义，填写 API Key。DeepSeek 使用
V4 API，可选择快速、均衡、深度等级，应用会自动配置 Flash/Pro 模型与推理强度。
密钥只保存在本机（`data/llm-config.json` 或 App 私有目录）。

安卓端 AI 面板提供 **DeepSeek 登录取 Key**：内置浏览器打开 DeepSeek 控制台，
登录后复制 API Key 会被自动捕获并写入配置；网页版提供“打开控制台 + 从剪贴板读取”。

未配置时：对话创作与演化使用离线模板，书架 AI 返回离线提示，写作功能不受影响。

## 🏗️ 构建

### Web 前端

```bash
cd ui
npm install
npm run build   # 产物在 ui/dist
```

### Android APK

完整说明见 [android/README.md](android/README.md)。本机构建环境：

```powershell
$env:ANDROID_HOME = "D:\Android\Sdk"
$env:ANDROID_SDK_ROOT = "D:\Android\Sdk"
$env:GRADLE_USER_HOME = "D:\GradleHome"
cd android
.\gradlew.bat assembleRelease --no-daemon
```

正式签名需要提供环境变量 `RHINE_STORE_FILE` / `RHINE_STORE_PASSWORD` /
`RHINE_KEY_ALIAS` / `RHINE_KEY_PASSWORD`（密钥库不随仓库分发）。

## 🗂️ 数据与存储结构

```text
data/
├─ projects/            # 故事项目备份与演化存档
├─ books/<book_id>/     # TXT 书库（百万字级）
│  ├─ book.json         # 元数据 + 章节摘要 + 全书档案（角色/设定/事实/伏笔）
│  ├─ chapters.json     # 章节索引
│  └─ chapters/*.txt    # 每章一个文件
├─ embedded-vault.json  # 内嵌资料库（Android / 内嵌模式）
├─ rhine-vault-core.db  # 桌面端自动拉起的默认 Rhine-Vault Core
└─ llm-config.json      # AI 通道配置（本机）
```

设置页导出的 ZIP 会包含项目、TXT 正文、版本记录，以及上述两种资料库数据；
为保护密钥，`llm-config.json` 不随备份导出。

## 📚 文档

- [文档首页](docs/index.md)
- [快速开始](docs/getting-started.md)
- [Agent 接入](docs/agent/index.md)
- [系统评估](docs/assessment/system-evaluation.md)
- [未来路线](docs/assessment/roadmap.md)
- [发布管理](docs/releases/index.md)
- [v0.2.1 Release Notes](docs/releases/v0.2.1.md)
- [v0.2.0 Release Notes](docs/releases/v0.2.0.md)
- [v0.1.0 Release Notes](docs/releases/v0.1.0.md)
- [更新日志](docs/releases/changelog.md)
- [Android 构建说明](android/README.md)

## 🧩 技术栈

- 后端：Python 标准库（`http.server` + `urllib`），无第三方运行时依赖
- 前端：Vue 3 + TypeScript + Element Plus + Vite
- 安卓：Chaquopy（App 内嵌 Python）+ Android WebView
- 文档：MkDocs（GitHub Pages 自动部署）

## 📜 版本

- **v0.2.1**（2026-08-15）：修复阅读器分页与移动端滑动，更新 APP 标志和版本显示，
  默认演示扩展为完整第一卷，并接入 DeepSeek V4 AI 等级。
- **v0.2.0**（2026-08-15）：产品化创作工作流更新，包含应用式界面、完整阅读器、长篇分析、
  视觉分支树、对话确认写入、Vault 接入、TXT 编码检测、移动端优化与默认奇幻演示。
- **v0.1.0**（2026-08-11）：首个公开发布，包含正文 / 演化 / 小说阅读 / TXT 书架 /
  AI 续写 / 内嵌资料库 / 安卓全内嵌版。
