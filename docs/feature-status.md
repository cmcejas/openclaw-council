# Feature status

This file separates what is implemented now from what is intentionally left conceptual in the first version.

## Implemented now

### Council model
- standard deliberation mode
- live brainstorm mode
- research-first mode
- distinct Alpha, Beta, Researcher, and Moderator role prompts
- transcript phases and round numbering

### Local tooling
- Python package with `openclaw-council` entry point
- `run`, `resume`, `render`, `plan-openclaw`, and `version` commands
- JSON state persistence in `state.json`
- markdown transcript rendering in `transcript.md`
- summary-table escaping for characters like `|` and embedded newlines so prompts do not corrupt the transcript header
- argument validation for common misuse
- optional generic `--agent-command` execution hook
- OpenClaw orchestration-pack generation (`openclaw-plan.json`, orchestrator prompt, runnable `openclaw agent` wrapper script)
- optional gateway `/tools/invoke` probing for `sessions_list`, `sessions_send`, and `sessions_spawn`

### OpenClaw adaptation layer
- a real `SKILL.md`
- explicit guidance for transcript-first orchestration
- explicit integration path for `sessions_spawn` / `sessions_send` workflows
- mapping from `council-cli` concepts to OpenClaw workflows
- honest limitations in user-facing docs

## Partially implemented

### Resume
Implemented as durable transcript/state replay, not as automatic restoration of hidden model memory.

### Execution
Implemented as scaffold generation, a generic shell command hook, and an OpenClaw-oriented helper layer. The repo now ships a real OpenClaw wrapper path, but not a universal native transport backend with direct guaranteed access to session primitives in every deployment.

### Research mode
Implemented as workflow structure and transcript shape. It does not include built-in web search execution inside the CLI.

## Conceptual / future work

- native transport for `sessions_spawn` and `sessions_send` that does not depend on a live OpenClaw agent handoff or custom gateway policy changes
- agent-specific transport adapters with progress tracking against spawned sessions
- detached long-running councils with taskflow integration
- real source harvesting and citation validation in research mode
- true concurrent or persistent council session handling inside this repo
- replay helpers that branch or diff prior council states
- polished HTML or report export

## Why this split is intentional

The first version tries to be useful immediately without pretending that undocumented or environment-specific OpenClaw runtime control is already solved. The new orchestration pack goes further, but it still reports the exact policy boundary when direct local access to session tools is blocked.

That tradeoff keeps the repo honest while still making it reviewable, extensible, and usable right now.
