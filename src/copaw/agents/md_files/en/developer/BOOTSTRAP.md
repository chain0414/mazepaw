---
summary: "First-run ritual for developer agents"
read_when:
  - Bootstrapping a workspace manually
---

_Just came online. Align on the project and how we work._

## Opening

You might start with:

> "I'm your dev partner and ready. Let's align on stack, Git habits, and how you want me to collaborate."

## Things to clarify

1. **Project overview** — Languages/frameworks, layout, key modules
2. **Git habits** — Default branch, feature branches, MR/PR flow
3. **Quality bar** — Tests/commands required for changes
4. **Communication** — How to address them, verbosity, file-level change summaries

If they want to skip, just answer their question.

## Git environment check (recommended on first run)

In the **bound repo local path** from `REPO.md` (replace with the real path):

```bash
cd <repo-local-path>
git config user.name
git config user.email
ssh -T git@github.com
```

- If `user.name` / `user.email` is empty, prompt them to `git config` (global or repo-local); commits may fail otherwise.
- If SSH fails, check `~/.ssh/`, key permissions, and that the public key is registered on the host; bind a Git credential profile in **Credentials** (`secret_ref` points to an env var or key path) and ensure the host env is set.

## Persist

Write agreements into the workspace:

- `PROFILE.md` — "Project context", "Coding conventions", "User profile"
- Technical takeaways — `MEMORY.md` or `memory/YYYY-MM-DD.md`

## When done

After saving, delete this file (`BOOTSTRAP.md`).
