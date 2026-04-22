# openclaw-council

An OpenClaw-native reinterpretation of `council-cli`.

Instead of assuming Claude Code sessions, this repo packages a practical first pass at a council workflow for OpenClaw:
- a real `SKILL.md` for agent use
- a small Python CLI for local orchestration and transcript management
- docs that map original `council-cli` ideas onto OpenClaw concepts
- honest boundaries around what is implemented vs what still depends on host runtime capabilities

## What this is

`openclaw-council` is a GitHub-ready starter repo for running structured multi-agent deliberation around a question, codebase, decision, or research task.

It supports three council shapes:
- **standard**: alternating formal rounds, then synthesis
- **live**: shorter brainstorm-style exchanges
- **research**: evidence-gathering first, then grounded brainstorming and synthesis

It also supports:
- transcript and state output, with prompt versus response entries called out explicitly
- manual resume by appending additional entries
- optional agent execution through a shell command template
- an OpenClaw-focused orchestration pack generator for real `sessions_spawn` / `sessions_send` workflows
- optional `openclaw agent` handoff so a live OpenClaw agent can execute the generated council plan
- optional gateway `/tools/invoke` probing to verify which session primitives are actually callable from a local helper
- role-aware prompt scaffolding for Alpha, Beta, Researcher, and Moderator
- OpenClaw skill instructions for running the workflow inside OpenClaw

## Why this exists

The original `council-cli` launches two Claude Code instances directly and relies on Claude Code session continuation. OpenClaw works differently. It has its own concepts, especially:
- `sessions_spawn`
- `sessions_send`
- subagents
- detached task workflows
- skill-triggered operational guidance

So this repo adapts the **workflow pattern**, not the exact runtime mechanism.

## Current implementation status

### Implemented

- Python CLI: `openclaw-council`
- modes: `standard`, `live`, `research`
- JSON state file and markdown transcript generation
- manual resume/append flow
- prompt scaffolding for Alpha, Beta, Researcher, and Moderator roles
- optional `--agent-command` hook for local orchestration via an external shell command
- `plan-openclaw` command that emits a machine-readable council plan, an OpenClaw orchestrator prompt, and a runnable `openclaw agent` wrapper script
- optional direct gateway probing for `sessions_list`, `sessions_send`, and `sessions_spawn`, with honest capture of policy/runtime failures
- OpenClaw `SKILL.md`
- architecture docs and example outputs

### Not implemented

- guaranteed direct invocation of `sessions_spawn` / `sessions_send` from the local helper in every deployment, because `/tools/invoke` blocks them by default unless the gateway is explicitly configured to allow them
- automatic multi-session lifecycle management against a live OpenClaw daemon without an actual OpenClaw agent or a gateway that exposes those session tools to the helper path
- true concurrent agent execution inside this Python process
- built-in web retrieval stack inside the CLI itself
- guaranteed replay of hidden model state from a prior session

Those are documented honestly below instead of hand-waved.

## Repo layout

- `README.md`: user-facing overview and usage
- `SKILL.md`: OpenClaw skill instructions
- `docs/architecture.md`: original architecture summary and adaptation rationale
- `docs/feature-status.md`: implemented versus conceptual features
- `src/openclaw_council/cli.py`: local CLI implementation
- `examples/`: generated sample outputs and manual resume example

## Install

```bash
cd openclaw-council
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Test

The repo ships stdlib `unittest` coverage, so you can validate it without installing `pytest` first:

```bash
python -m unittest discover -s tests -v
```

## Quick start

### 1. Scaffold a standard council run

```bash
openclaw-council run "Should we split the monolith?" \
  --mode standard \
  --directory . \
  --rounds 4 \
  --output-dir examples/monolith-council
```

This creates scaffold prompts and a transcript without calling any model. Scaffold entries are marked as `Entry kind: prompt` so they are not confused with real agent replies.

### 2. Append real agent output later

```bash
cat alpha-round-1.md | openclaw-council resume examples/monolith-council/state.json \
  --speaker "Agent Alpha" \
  --role alpha \
  --phase deliberation \
  --round 1
```

### 3. Re-render transcript

```bash
openclaw-council render examples/monolith-council/state.json
```

## Optional execution mode

If you already have some local wrapper that can accept a prompt and print a reply, you can wire it in with `--agent-command`.

Example shape:

```bash
openclaw-council run "Evaluate our auth risks" \
  --mode standard \
  --agent-command 'my-agent-runner --prompt "{prompt}"' \
  --output-dir out/auth-council
```

Notes:
- `{prompt}` is replaced inline.
- The command is executed with `shell=True`.
- This is intentionally generic. The repo does **not** pretend to know your local OpenClaw or agent wrapper syntax.

## OpenClaw-native orchestration pack

The new `plan-openclaw` command adds a practical wrapper layer for real OpenClaw environments.

It generates:
- `openclaw-plan.json`: machine-readable turn sequence and transport notes
- `orchestrator-prompt.md`: a ready-to-send prompt that tells a live OpenClaw agent to use `sessions_spawn` / `sessions_send` when available, and to fall back honestly when they are not
- `run-via-openclaw-agent.sh`: a shell wrapper that sends the prompt through `openclaw agent`

Example:

```bash
openclaw-council plan-openclaw "Should we split the monolith?" \
  --mode research \
  --directory . \
  --output-dir out/openclaw-council \
  --probe-session-tools
```

If you also want to dispatch the orchestrator prompt immediately:

```bash
openclaw-council plan-openclaw "Should we split the monolith?" \
  --mode standard \
  --output-dir out/openclaw-council \
  --run-via-agent \
  --openclaw-agent-id main
```

Important boundaries:
- Gateway `/tools/invoke` blocks `sessions_send` and `sessions_spawn` by default in stock OpenClaw. This repo probes and reports that honestly instead of pretending it has private control-plane access.
- The practical path from a local helper is usually: generate the orchestration pack, then hand it to a live OpenClaw agent via `openclaw agent` so that agent can call session tools from inside its own runtime.
- When neither path is available, the fallback remains transcript-first orchestration.

## OpenClaw usage model

Inside OpenClaw, the preferred pattern is usually:

1. Trigger the skill for a deliberation task.
2. Spawn or route two agents with distinct roles.
3. Feed them either the repo/codebase or a research brief.
4. Alternate turns using `sessions_send` or subagent messages.
5. Store transcript entries after each turn.
6. Ask a moderator/synthesizer pass for consensus.
7. Resume later by replaying transcript plus current task state.

The included `SKILL.md` tells another OpenClaw agent how to do that carefully and honestly.

## CLI commands

```bash
openclaw-council run TOPIC [--mode standard|live|research] [--rounds N] [--exchanges N] [--output-dir DIR]
openclaw-council resume STATE.json --speaker NAME --role ROLE --phase PHASE --round N [--content-file FILE] [--source URL]
openclaw-council render STATE.json [--output FILE]
openclaw-council plan-openclaw TOPIC [--mode standard|live|research] [--rounds N] [--exchanges N] [--probe-session-tools] [--run-via-agent]
openclaw-council version
```

## Mapping from original council-cli

| council-cli feature | Original behavior | openclaw-council equivalent |
|---|---|---|
| Standard formal rounds | Alpha/Beta alternate with structured prompts | `run --mode standard`, plus skill-guided multi-agent turns |
| Live brainstorm | Short back-and-forth with persistent sessions | `run --mode live` scaffold, transcript-first resume strategy |
| Research mode | Web research, lateral thinking, grounded brainstorm | `run --mode research` with Researcher + Alpha/Beta/Moderator roles |
| Consensus synthesis | Final summary from discussion | Moderator phase + transcript rendering |
| Transcript output | Markdown transcript file | `transcript.md` plus structured `state.json` |
| Resume | Read prior transcript and continue | manual state append / replay-friendly state file |
| Session continuation | Claude Code `--continue` | OpenClaw-style transcript replay and, where available, session reuse |

## Resume and replay strategy

OpenClaw does not guarantee a universal equivalent of Claude Code's exact CLI continuation semantics across every runtime. So this repo uses a more portable strategy:

- treat transcript/state as the durable source of truth
- persist each turn as structured data
- when resuming, replay the relevant transcript into the next prompt
- keep explicit roles and phases so the deliberation can be reconstructed

This is less magical than hidden session state, but more portable and auditable.

## Files

- `SKILL.md`: OpenClaw skill instructions
- `docs/architecture.md`: design, original-architecture summary, and adaptation notes
- `src/openclaw_council/cli.py`: runnable CLI
- `examples/`: example state and transcript output

## Implemented vs conceptual

A more explicit matrix lives in `docs/feature-status.md`.

Short version:

### Implemented
- CLI packaging and entry point
- three council modes
- durable transcript and state files
- manual resume flow
- role-aware prompt scaffolding
- optional generic external runner hook
- OpenClaw orchestration-pack generator with explicit `sessions_spawn` / `sessions_send` integration paths
- optional gateway probing for session-tool reachability
- optional `openclaw agent` handoff wrapper
- OpenClaw skill guidance
- checked-in example outputs

### Conceptual or future
- a universally reliable native OpenClaw transport that can bypass gateway policy limits without a live agent in the middle
- automatic multi-session orchestration with progress tracking against live spawned sessions
- built-in web retrieval and citations in the CLI
- true hidden-state continuation comparable to Claude Code `--continue`

### Native plugin (experimental)

- A real OpenClaw plugin skeleton lives under `plugin/` (`council_run`). It is intended to load as other OpenClaw plugins do; **tool execution is environment-dependent** and requires correct **tool allowlisting** (optional tools and `group:openclaw` do not include plugin tools by default). See `docs/openclaw-plugin-tool-catalog.md` before claiming “works end-to-end.”

## Limitations

### Important

This repo is a **usable first implementation**, not a full OpenClaw daemon integration.

It does not currently:
- bypass default gateway security policy to force `sessions_spawn` or `sessions_send` over `/tools/invoke`
- guarantee that a local helper can directly spawn real OpenClaw sessions in every deployment
- perform autonomous research internally
- guarantee parity with `council-cli`'s exact persistent-session behavior

What it does provide is:
- a clean council data model
- a practical transcript workflow
- a real skill file
- a local CLI that is useful immediately for scaffolding, manual orchestration, record-keeping, and OpenClaw-specific orchestration handoff
- direct probing of what a local OpenClaw gateway really allows
- a clear path for future daemon-backed automation

## Example output

See `examples/sample-standard/` for a checked-in sample transcript.

## Next good improvements

1. Add an OpenClaw transport layer once stable session control endpoints are available.
2. Add per-agent command templates instead of one shared `--agent-command`.
3. Add transcript diff/replay helpers.
4. Add source capture for research mode.
5. Add HTML export for reviewable council reports.

## License

MIT
