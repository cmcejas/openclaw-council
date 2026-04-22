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
- `run`, `resume`, `render`, and `version` commands
- JSON state persistence in `state.json`
- markdown transcript rendering in `transcript.md`
- argument validation for common misuse
- optional generic `--agent-command` execution hook

### OpenClaw adaptation layer
- a real `SKILL.md`
- explicit guidance for transcript-first orchestration
- mapping from `council-cli` concepts to OpenClaw workflows
- honest limitations in user-facing docs

## Partially implemented

### Resume
Implemented as durable transcript/state replay, not as automatic restoration of hidden model memory.

### Execution
Implemented as either scaffold generation or a generic shell command hook. The repo does not ship a native OpenClaw transport backend.

### Research mode
Implemented as workflow structure and transcript shape. It does not include built-in web search execution inside the CLI.

## Conceptual / future work

- native transport for `sessions_spawn` and `sessions_send`
- agent-specific transport adapters
- detached long-running councils with taskflow integration
- real source harvesting and citation validation in research mode
- true concurrent or persistent council session handling
- replay helpers that branch or diff prior council states
- polished HTML or report export

## Why this split is intentional

The first version tries to be useful immediately without pretending that undocumented or environment-specific OpenClaw runtime control is already solved.

That tradeoff keeps the repo honest while still making it reviewable, extensible, and usable right now.
