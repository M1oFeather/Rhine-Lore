# 发布管理

## 版本号

采用 `v<主>.<次>.<修订>` 语义化版本：

- 主版本：不兼容的架构或数据格式变化；
- 次版本：新增功能（演化、书架、AI 能力等）；
- 修订：修复与细节改进。

## 发布流程

1. 更新 `android/app/build.gradle` 的 `versionCode` / `versionName`；
2. 在 `docs/releases/` 新建版本 Release Notes，并更新 `changelog.md`；
3. 构建产物：
   - Android：`assembleRelease`（签名 APK）
   - Windows / Linux：源码发行包（含 `ui/dist`）
4. 打标签并创建 GitHub Release，附上 APK 与发行包；
5. 文档站（MkDocs）由 `.github/workflows/docs.yml` 自动部署到 GitHub Pages。

## 产物清单

| 平台 | 文件名 |
| --- | --- |
| Android | `app-release.apk` |
| Windows x64 | `Rhine-Lore-<版本>-win-x64.zip` |
| Linux x64 | `Rhine-Lore-<版本>-linux-x64.tar.gz` |
