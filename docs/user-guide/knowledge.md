# 资料库与 Rhine-Vault

## 默认模式

Lore 启动时会自动准备一个供自己使用的 Vault Core。桌面版默认使用本地 SQLite Core；Android 或内嵌模式可使用本地 JSON 存储。用户无需先理解或部署知识库后端，就可以保存、送审、入库和检索资料。

资料生命周期：

```text
对话/手动创建 -> 工作区草稿 -> 送审 -> 批准入库 -> 创作检索与引用
```

“保存到资料库”工具当前保存的是工作区草稿，不等于已审核知识。重要世界规则和事实应经过审核后再用于强约束创作。

## 独立 Rhine-Vault

需要更完整的资料管理界面或复用已有知识库时，可在设置中：

1. 查看内置 Vault 的连接状态。
2. 启动或停止本机 Vault Core。
3. 填写其他 Rhine-Vault 服务地址并测试连接。
4. 安装可选的 Vault Web 管理界面。
5. 安装完成后从 Lore 跳转到 Vault Web。

Lore 不复制 Vault 的审核、工作区和知识搜索逻辑。两者职责边界参见 [Rhine-Vault 边界](../architecture/RHINE_VAULT_BOUNDARY.md)。

## 选择哪种模式

| 需求 | 推荐模式 |
| --- | --- |
| 第一次使用、单机写作 | 自动内置 Core |
| Android 离线使用 | App 私有目录中的内嵌 Vault |
| 需要完整知识管理界面 | 内置 Core + 可选 Vault Web |
| 已有团队或个人 Vault | 连接独立 Rhine-Vault |

## 数据与隐私

- Vault 数据随完整备份导出；模型 API Key 不随备份导出。
- 切换 Vault 前先备份，并确认新端点中的 workspace 与资料状态。
- 独立 Vault 地址应使用可信网络。Lore 当前没有为远程 Vault 凭据提供完整的多用户权限模型。
- 对话引用知识时仍可能把相关片段发送给已配置的在线模型。
