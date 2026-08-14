# 快速开始

## 环境要求

- Python 3.10 或更高版本。
- 直接运行后端与已构建前端时，不需要第三方 Python 运行时依赖。
- 修改 Web 前端时，需要 Node.js 与 npm。
- 构建 Android 时，需要 Android SDK、JDK 和 Gradle 环境；参见仓库中的 `android/README.md`。

## 启动桌面 Web 版

Windows：

```powershell
.\start.bat
```

或直接运行：

```powershell
python main.py --host 127.0.0.1 --port 8786
```

Linux/macOS：

```bash
python3 main.py --host 127.0.0.1 --port 8786
```

浏览器打开 `http://127.0.0.1:8786/`。需要同一局域网设备访问时，可改为 `--host 0.0.0.0`，但请先阅读 [Agent 安全边界](agent/security.md)。

## 第一次使用

首次在空数据目录中启动时，工作台会创建原创哥特奇幻演示《灰烬月冠》。演示包含三章正文、五名角色、八项世界设定、故事地图、文风约束和待处理伏笔，可以直接用于阅读、编辑、演化与分支测试；已有项目不会被替换或重复初始化。

1. 在首页选择演示故事、“创建故事”或“导入小说”。
2. 新建故事时可选择“空白故事”或“奇幻演示”；两种起点都可以修改名称、类型和概要。
3. 创作原创项目时，先建立最少量的人物和世界资料，然后进入正文或对话页。
4. 导入 TXT 时，先检查编码检测结果和章节预览；发现标题切分异常时返回调整，不要直接覆盖原文件。
5. 点击顶栏 AI 状态，从右侧配置 DeepSeek、OpenAI 或自定义兼容模型；DeepSeek 默认使用 V4，并提供快速、均衡、深度三级。需要时可展开“生成精调”调整推理强度、随机性、候选范围与最大输出。没有模型配置时，阅读和手动编辑仍可使用。
6. 在对话中接受写入操作前，检查目标项目、章节和参数。执行后可从版本记录恢复。

## 构建前端

```bash
cd ui
npm install
npm run build
```

构建产物位于 `ui/dist/`，后端会将其作为 Web 界面提供。

## 构建文档

```bash
python -m pip install -r requirements-docs.txt
python -m mkdocs serve
```

本地文档默认位于 `http://127.0.0.1:8000/`。提交前执行严格构建：

```bash
python -m mkdocs build --strict
```

## 数据位置

源码运行时数据默认位于仓库的 `data/`。Android 版本使用 App 私有目录。备份不会包含模型 API Key；迁移设备后需要重新配置密钥。

!!! tip "先做一次备份"
    导入长篇小说或开始大规模 AI 分析前，建议在设置中导出完整备份。项目与书籍的 Agent 写操作会生成版本快照，但完整备份覆盖范围更广。
