# 系统架构总览

## 组件

```text
Vue 3 Web / Android WebView
          |
          | /lore-api/*
          v
Python ThreadingHTTPServer
  |       |         |          |
项目 JSON  书籍分章   版本快照    长篇分析任务
  |       |         |          |
  +-------+---------+----------+
          |
          | /api/* 或 Vault 适配器
          v
内置 Vault Core / 独立 Rhine-Vault
          |
          v
OpenAI 兼容模型服务（可选）
```

前端使用 Vue 3、TypeScript、Element Plus 与 Lucide 图标。后端运行时仅使用 Python 标准库，以便桌面发行包和 Chaquopy Android 内嵌。Android App 在私有目录启动同一 Python 服务，再由 WebView 加载界面。

## API 命名空间

- `/lore-api/*`：Lore 产品能力，包括项目、书籍、分支、分析、版本、模型配置与 Agent。
- `/api/*`：Vault 能力，由内置适配器提供或代理到独立 Rhine-Vault。

`GET /api/health` 表示 Vault 端健康，不等同于 Lore 全系统健康。当前尚无统一的 `/lore-api/health` 和版本化能力清单，这是下一阶段接口治理任务。

## 主要链路

### 原创项目

```text
项目 -> 人物/世界/地图 -> 对话或手动编辑 -> 正文 -> 版本快照
```

### 导入小说

```text
TXT -> 编码检测 -> 拆卷/拆章 -> 按章存储 -> 阅读
                                  -> 长篇分析 -> 工作台
                                  -> 任意位置分支 -> 分支树
```

### Agent 写操作

```text
消息 -> 模型提出工具调用 -> 只读工具自动执行
                         -> 写工具形成待确认动作
                         -> 用户确认 -> 快照 -> 执行 -> 刷新
```

## 设计优势

- 本地优先，离线时保留阅读和手动创作能力。
- 项目、导入书籍、资料库之间有明确边界。
- 长篇正文按章延迟加载，分析支持内容哈希缓存和恢复。
- AI 写入默认经过用户确认，项目和书籍修改有恢复路径。
- Web 与 Android 共用产品 API 和大部分界面逻辑。

## 当前约束

- HTTP API 尚未版本化，也没有 OpenAPI 或 JSON Schema 契约。
- 服务端没有用户鉴权；CORS 当前允许任意来源。
- Python 路由和 Vue 主界面规模较大，后续修改的回归面偏宽。
- 长篇任务使用进程内线程，不支持跨进程调度或资源配额。
- 前端缺少系统化单元测试和提交到仓库的端到端回归套件。

完整风险和优先级见 [系统评估](../assessment/system-evaluation.md)。
