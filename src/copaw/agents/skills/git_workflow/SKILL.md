---
name: git_workflow
description: Git 工作流：同步远端、分支策略、Conventional Commits、PR/MR 前整理与安全推送
metadata:
  {
    "builtin_skill_version": "1.0",
    "copaw": { "emoji": "🌿" },
  }
---

# Git 工作流

在**已绑定的仓库本地路径**下操作（见 `REPO.md`），不要用 agent 工作区根目录代替仓库路径。

## 凭据与 SSH（首次使用前）

控制台 **凭据** 页可绑定 Git 档案（仅保存引用：`auth_method` + `secret_ref`）。运行时会在 `execute_shell_command` 中合并常见环境变量（例如 SSH 私钥路径 → `GIT_SSH_COMMAND`；Token 类 → `GITHUB_TOKEN`），**仍依赖**主机上已配置的环境变量或密钥文件可读。

建议在仓库目录下自检（将路径换成 `REPO.md` 中的本地路径）：

```bash
cd <repo-local-path>
git config user.name
git config user.email
ssh -T git@github.com
# 或你们 Git 托管商的 SSH 欢迎语 / 权限探测
```

若 `user.name` / `user.email` 为空，引导用户执行 `git config --global user.name "..."` 等；若 SSH 失败，检查 `~/.ssh/`、公钥是否加入托管商、以及凭据档案中的 `secret_ref` 是否指向正确私钥或环境变量。

## 开始改代码前

```bash
cd <repo-local-path>
git fetch origin
git status
# 必要时：git pull --rebase origin <default-branch>
```

## 分支策略（按改动规模）

| 情况 | 建议 |
|------|------|
| 小修复、单文件、低风险 | 在当前约定分支上直接提交 |
| 跨模块、多文件、需长时间验证 | 新建 `feat/` 或 `fix/` 分支，完成后提 MR/PR |

```bash
git checkout -b feat/short-description origin/main   # 示例
```

## 控制台提交卡片（CoPaw Console）

在 **Web 控制台**对话中修改代码或使用工具改动仓库后：

1. **在答复收尾处调用 `propose_git_commit`**，传入 `summary`（建议的提交说明）和可选的 `files`（本次相关文件路径，仓库相对路径）。不传 `files` 时表示当前工作区全部未提交变更（适用于「查看都有哪些改动并提交」）。
2. 控制台会渲染**可交互提交卡片**（放弃 / 提交、展开文件列表与 diff）。用户点击提交后再由前端调用服务完成 `git add` / `commit` / `push`，**不要**在用户未确认前自行 `git commit`。
3. 在飞书等 IM 渠道，同一工具会输出 Markdown 摘要；用户可用文字回复「提交」等，你再按本 SKILL 用 `execute_shell_command` 完成提交（遵守分支与安全推送约定）。

## 提交信息（Conventional Commits）

使用前缀：`feat:`、`fix:`、`docs:`、`refactor:`、`test:`、`chore:` 等，英文或团队约定语言均可，保持**一条提交一件事**。

## PR / MR 前整理

```bash
git fetch origin
git rebase -i origin/<target-branch>   # 按需整理提交信息或 squash fixup
# 仅在自己的分支上需要强制推送时：
git push --force-with-lease
```

**禁止**对共享主分支做普通 `force push`。

## PR / MR 描述（可套用）

- **What**：改了什么
- **Why**：动机 / 关联 issue
- **How**：要点（非逐行）
- **Risk / rollback**：风险与回滚方式
- **Testing**：如何验证（命令、场景）

## MR 与「待审核队列」（本机 CoPaw 门禁）

若团队约定：**先在 CoPaw 待审核队列里通过，再到 GitHub/GitLab 上 approve/merge MR**，则顺序必须是：

1. 代码已推送，MR 已创建（或即将创建），准备好摘要、关键 diff、MR 链接。
2. **`git push` 成功后，你应主动帮用户把条目推进待审核队列**：在控制台 **待审核队列** 提交一条类型为 `merge_request` 的条目；或调用 `POST /insights/review-queue`（需携带当前 agent 的上下文，与对话同源），JSON 至少包含：唯一 `id`（可用 UUID）、`item_type`=`merge_request`、`title`、`summary`（变更与风险）、`source_agent`（当前 agent 名或 id）、`action_payload.mr_url`（若已有 MR 链接）。工作区根目录的 `review_queue.json` 由服务写入，**不要手改 JSON** 除非你知道格式。
3. 用户在队列里 **批准** 该条后，才在远端平台上 **Approve / Merge** MR（或按你们流程让维护者操作）。
4. **禁止**在队列尚未批准时，代用户宣称「可以合并」或执行等价于合并主干的操作。

若用户明确说跳过本机队列（例如纯开源协作、MR 只在平台上审），按其指示，但仍应在对话中说明风险。

## 合并后

删除本地 feature 分支；若远端分支已合并，删除远端分支（按团队规范）。
