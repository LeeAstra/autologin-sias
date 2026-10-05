# 仓库管理检查（2026-10-05）

检查对象：`LeeAstra/autologin-sias` 和本地项目目录。GitHub 默认分支为 `main`，仓库公开，既有 5 个 PR 均已合并，最近 Windows CI 成功；稳定 Release 为 v1.2.0，历史候选有独立标签。许可证、版本单一来源、构建脚本、安装回滚测试和日志忽略规则已具备。

## 发现与处理

| 项目 | 现状 | 处理或建议 |
|---|---|---|
| PR / CI / Release | 已使用，基本符合小型开源项目流程 | 本次继续用短期分支、PR、CI、预发布标签 |
| 历史分支 | 4 个远端功能分支对应已合并 PR | 分支数量本身不是问题；建议确认无独有工作后删除，保留历史 PR 和标签。本次不批量删除旧分支 |
| 自动删除分支 | `delete_branch_on_merge=false` | 建议开启，减少今后已合并分支积累；本次未更改设置 |
| main 保护 | 无 branch protection 或 ruleset | 建议要求 PR、`test-and-build` 检查通过、解决讨论，禁强推和删除；个人项目可设 0 个强制审批，避免作者无法自审导致堵塞。本次仅检查，不更改权限策略 |
| 实验代码 | 原为本地零散目录 | 提交可维护源码到 `tools/experiments/`；真实结果和对话交接不提交，原有本地实验版保留 |
| 贡献指南与 PR 模板 | 缺少 | 增加 `CONTRIBUTING.md` 和 PR 模板，明确验证和版本流程 |
| 本地主目录 | 干净，但停留在已完成的文档分支 | 更新完成后回到 `main`，避免继续在旧功能分支上开发 |
| 发布验收 | 自动测试完善，实机场景未完全验证 | 新功能先发布 rc，不替代稳定下载；记录验证边界 |
| OneDrive | 本地仓库位于同步目录 | Git 提交和远端才是版本依据；避免多台机器同时修改同一个同步的 `.git`，更稳妥的是每台机器独立 clone |

GitHub Flow 推荐合并后删除功能分支，删除分支不会删除 PR 或提交历史：[GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)。主分支可用状态检查和强推限制保护：[Protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)。版本规则参考 [Semantic Versioning](https://semver.org/)。

以上是流程检查，不代表完整历史敏感信息审计。当前上传只选择源码和合成测试，不上传个人记录。
