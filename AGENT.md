

# Project Memory — apex-fs-commander
> 19 notes | Score threshold: >40

## Safety — Never Run Destructive Commands

> Dangerous commands are actively monitored.
> Critical/high risk commands trigger error notifications in real-time.

- **NEVER** run `rm -rf`, `del /s`, `rmdir`, `format`, or any command that deletes files/directories without EXPLICIT user approval.
- **NEVER** run `DROP TABLE`, `DELETE FROM`, `TRUNCATE`, or any destructive database operation.
- **NEVER** run `git push --force`, `git reset --hard`, or any command that rewrites history.
- **NEVER** run `npm publish`, `docker rm`, `terraform destroy`, or any irreversible deployment/infrastructure command.
- **NEVER** pipe remote scripts to shell (`curl | bash`, `wget | sh`).
- **ALWAYS** ask the user before running commands that modify system state, install packages, or make network requests.
- When in doubt, **show the command first** and wait for approval.

## 📝 NOTE: 1 uncommitted file(s) in working tree.\n\n## Important Warnings

- **gotcha in .gitignore** — File updated (external): .gitignore

Content summary (76 lines):
# APE

## Active: `.`

- **gotcha in .gitignore**
- **[.windsurfrules] NEVER use TailwindCSS. Only use vanilla CSS.**
- **[CLAUDE.md] NEVER use TailwindCSS. Only use vanilla CSS.**

## Project Standards

- [.windsurfrules] NEVER use TailwindCSS. Only use vanilla CSS.
- [CLAUDE.md] NEVER use TailwindCSS. Only use vanilla CSS.
- Git Commit: feat: add macOS launchctl process tracking to scripts/status — confirmed 3x
- Git Commit: fix: resolve parent REPO_ROOT path and add offline --no-pip  — confirmed 3x
- Git Commit: chore: reorganize repository structure and reconfigure smith — confirmed 3x
- Version your API from day 1 (/api/v1/)
- Use consistent response format across all endpoints
- Implement soft delete for important data — don't hard delete without confirmation

## Verified Best Practices

- Agent generates new migration for every change (squash related changes)
- Agent installs packages without checking if already installed

## Available Tools (ON-DEMAND only)
- `sys_core_01(q)` — Deep search when stuck
- `sys_core_05(query)` — Full-text lookup
> Context above IS your context. Do NOT call sys_core_14() at startup.
