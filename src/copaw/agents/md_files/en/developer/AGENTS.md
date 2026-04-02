---
summary: "Developer agent workspace rules"
read_when:
  - Bootstrapping a workspace manually
---

## Repository-first

- **Code and Git** default to the **local repository paths** listed in `REPO.md` (`repo_assets`), not this agent workspace root.
- When the user says "repo", "code", "project", or "the codebase", work under the bound checkout paths first; the workspace holds memory, config, and skills.
- Multiple repos: confirm which one (name / ID) before running commands.

## Change protocol

- **Large changes**: produce an actionable Plan (context, approach, blast radius, risks, rollback) and **wait for confirmation** before editing. See `active_skills/dev_planning/`.
- **Every change**: summarize touched files; show diff or a concise summary when useful.
- **Business logic**: pair changes with unit tests (or the project's minimum bar). See `active_skills/testing/`.
- **Destructive ops** (delete files, force-push, history rewrite): ask first.

## Git and branches

- Before editing, **fetch/pull** in the target repo and know current branch vs remote.
- Small fixes on the agreed branch; **cross-cutting or risky work** uses a feature branch, then **MR/PR** to main. Details in `active_skills/git_workflow/`.

## Merge requests and the review queue

When your team uses CoPaw **Review Queue** (console or `POST /insights/review-queue`) as a gate before merging:

- **First** enqueue a **merge_request** item (title, summary, optional MR URL). **After** the user **approves** it in the queue, guide them to **Approve / Merge** on GitHub/GitLab (or follow your maintainer workflow).
- Do **not** treat the MR as ready to merge while the queue item is still pending.
- How to enqueue is documented in `active_skills/git_workflow/` under “MR and review queue”.

## Code review (including self-review)

- Before merge/delivery, check: **correctness, security, maintainability, performance, tests**.
- Use severity levels: blocker / suggestion / nit. See `active_skills/code_review/`.

## Memory (engineering-focused)

Each session is fresh; durable context lives in workspace files:

- **Daily notes:** `memory/YYYY-MM-DD.md`
- **Long-term:** `MEMORY.md` — ADR summaries, stack choices, recurring pitfalls, repo conventions
- Read before overwrite.

Prefer capturing: architecture decisions, module boundaries, invariants, performance baselines, agreed conventions from reviews.

## Safety

- Never leak secrets, tokens, or internal-only endpoints into outputs.
- If unsure about safety, ask.

## Tools

For workflows, open `active_skills/<name>/SKILL.md`.

## Heartbeat

If heartbeat is configured: follow `HEARTBEAT.md` strictly; do not guess unfinished tasks from old chats.
