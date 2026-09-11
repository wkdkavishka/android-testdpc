# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This file is intentionally thin and carries no architecture of its own. The real content
is in the hub, `.github/copilot-instructions.md`, which both Claude Code and GitHub Copilot
read. Update content **there**, never here.

| Kind | Home |
|---|---|
| Rules, architecture map, commands | `.github/copilot-instructions.md` (the hub) |
| Subsystem detail and gotchas | `AI-MD/`, indexed by `AI-MD/README.md` |
| Procedures you invoke | `.claude/skills/<name>/SKILL.md` |
| Personal preferences, gitignored | `CLAUDE.local.md` |

Copilot reads only the hub. It follows no `@`-includes and no links, so anything moved out
of the hub becomes Claude-only.

@CLAUDE.local.md
@.github/copilot-instructions.md
