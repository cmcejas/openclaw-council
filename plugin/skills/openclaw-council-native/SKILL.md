---
name: openclaw-council-native
description: Use the council_run tool for structured council deliberation inside OpenClaw when the openclaw-council plugin is installed and allowlisted.
---

# OpenClaw Council (native plugin)

When the **openclaw-council** plugin is loaded and `council_run` is allowed for this agent, use it for multi-turn council-style reasoning on a topic.

## When to use

- You need a deliberate second pass (subagent) on strategy, risks, or research-shaped questions.
- The user asked for council, Alpha/Beta style debate, or moderated synthesis.

## Tool

- `council_run` — parameters: `topic` (string), `mode` (`standard` | `live` | `research`), optional `rounds` (1–8).

## Requirements

Plugin tools must survive OpenClaw’s tool **policy** layer. With `tools.profile: "coding"`, add **`council_run`** via **`tools.alsoAllow`** (additive), not only `tools.allow`. See repo `docs/openclaw-plugin-tool-catalog.md`.

## Fallback

If the tool is not available, follow the repository root `SKILL.md` and transcript-first CLI workflow instead.
