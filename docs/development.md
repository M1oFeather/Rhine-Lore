# 开发与部署

## 仓库结构

```text
src/rhine_lore/       Python 服务、存储、演化和 Vault 集成
ui/                   Vue 3 + TypeScript 前端
android/              Chaquopy + WebView Android 外壳
tests/                Python API、存储和领域测试
docs/                 MkDocs 文档
.github/workflows/    构建、发布与文档部署
```

## 开发命令

后端测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

前端检查与构建：

```powershell
cd ui
npm install
npm run build
```

文档严格构建：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-docs.txt
.\.venv\Scripts\python.exe -m mkdocs build --strict
```

本地运行：

```powershell
.\.venv\Scripts\python.exe main.py --host 127.0.0.1 --port 8786
```

## 提交前检查

1. 运行全部 Python 测试。
2. 运行 `npm run build`，确保 TypeScript 和 Vite 均通过。
3. 运行 `mkdocs build --strict`，确保导航、链接和 Markdown 无警告。
4. 涉及页面布局时，用桌面和手机视口检查首页、对话、阅读器、工作台和设置。
5. 涉及数据结构时，用真实大小的副本验证迁移、备份和恢复。
6. 涉及 Agent 工具时，同时更新工具 Schema/文档、确认 UI、快照策略和契约测试。

## 部署边界

源码服务默认应绑定 `127.0.0.1`。`--host 0.0.0.0` 仅用于受信局域网调试，不代表服务已经具备公网安全能力。

GitHub Actions 会使用 `requirements-docs.txt` 执行 `mkdocs build --strict`。仓库启用 GitHub Pages 且来源选择 GitHub Actions 后，文档工作流会上传并发布 `site/`。

## 版本管理

版本号至少出现在 `pyproject.toml`、`src/rhine_lore/__init__.py`、`ui/package.json`、Android `versionName`、README 徽章和发布文档中。发布前应统一更新，并在 CI 中增加一致性检查。当前统一版本为 `0.2.1`。

软件尚未正式发布时，数据结构不需要兼容性包袱，但任何破坏性变更仍必须通过一次性迁移保护本地测试数据。不要默默忽略未知字段或损坏文件。
