# openclaw-council architecture

## Purpose

This repo adapts the core workflow ideas from `council-cli` into an OpenClaw-oriented package.

The goal is not to fake one-to-one parity with Claude Code CLI internals. The goal is to preserve what is valuable:
- role separation
- alternating deliberation
- research-backed variants
- consensus synthesis
- transcript durability
- resumability

## Summary of the original council-cli architecture

Based on `README.md` and `council_cli/council.py` from `council_cli-0.1.2`, the original project is built around these components.

### 1. A transcript manager as the session backbone

The original tool uses a `TranscriptManager` class that stores entries with:
- agent name
- round number
- content
- tags
- consensus flag

It renders markdown transcripts, writes them to disk, and can parse prior transcripts back into memory for resume.

### 2. Strongly differentiated agent prompts

`council.py` defines distinct prompt builders for Alpha and Beta.

- **Alpha** is structured, evidence-driven, and analytical.
- **Beta** is contrarian, creative, and edge-case oriented.

This role asymmetry is a major part of how the original tool avoids two blandly similar model outputs.

### 3. Three execution modes

The original code has three main runners:
- `run_council` for standard alternating rounds
- `run_council_live` for short live brainstorm exchanges
- `run_council_research` for a research-first flow

That split is the main product design of the tool.

### 4. Claude CLI wrapper as transport layer

The original implementation is tightly coupled to Claude Code CLI:
- it locates the `claude` binary
- streams output from subprocess calls
- optionally uses `--continue`
- controls allowed tools in research mode
- uses isolated temp directories to reduce prompt bleed from local files

This means its orchestration logic and transport logic are mixed in one file.

### 5. Resume through transcript plus session continuation

The original tool supports `--resume` in two ways:
- parse prior markdown transcript to reconstruct turn history
- where possible, continue Claude sessions with `--continue`

That gives it a fairly smooth continuation story, but only inside the Claude Code runtime model.

### 6. Final consensus step

After debate or brainstorming, the original tool asks for a final synthesis, using Alpha first and Beta as validator/amender.

That is important because it turns raw dialogue into a decision artifact.

## Why OpenClaw needs a different design

OpenClaw is not just "Claude Code with different branding".

OpenClaw work is commonly organized around:
- agent chat turns
- subagents
- `sessions_spawn`
- `sessions_send`
- taskflow or detached task orchestration
- skills that teach an agent how to operate

So a direct port of `council.py` would be misleading unless the exact same transport guarantees existed.

The correct adaptation is:
1. keep the council model
2. separate it from transport assumptions
3. make transcript state the durable source of truth
4. let OpenClaw-native runtimes plug in stronger session controls later

## This repo's architecture

This first version intentionally splits concerns more clearly than the original single-file implementation.

## 1. Data model first

The CLI centers on two dataclasses:
- `TranscriptEntry`
- `CouncilState`

`CouncilState` persists to JSON and drives markdown rendering. That makes resume and replay explicit instead of hidden in runtime state.

## 2. Role prompt library

The first implementation defines four reusable roles:
- `alpha`
- `beta`
- `researcher`
- `moderator`

These are simpler than the original's long prompt blocks, but they preserve the same structural intent.

## 3. Mode-specific scaffolders

The CLI supports:
- `standard`
- `live`
- `research`

When no agent command is supplied, it generates a council scaffold. This is useful immediately for:
- planning a council
- manual orchestration
- preserving transcript shape
- handing turns to real agents later

## 4. Optional generic execution hook

If `--agent-command` is provided, the CLI can execute a shell template per turn.

This is intentionally generic. It avoids pretending that this repo knows the universal command line for every OpenClaw deployment or every external model runner.

That hook exists so teams can wire in their own wrappers locally.

## 5. Transcript-first resume

Instead of relying on hidden session memory, this repo treats `state.json` as canonical.

Resume works by appending additional structured entries and re-rendering the transcript.

This is less elegant than true persistent agent memory, but more:
- portable
- inspectable
- testable
- OpenClaw-friendly

## 6. Skill plus CLI, not CLI alone

The repo includes `SKILL.md` because in OpenClaw the operational behavior often lives partly in the skill and partly in the helper code.

That is a better fit than shipping just a CLI.

## Mapping table

| Concern | council-cli | openclaw-council |
|---|---|---|
| Agent transport | Claude Code subprocess wrapper | generic command hook or OpenClaw manual/runtime orchestration |
| Session state | transcript plus Claude `--continue` | explicit `state.json` plus transcript replay |
| Modes | standard / live / research | same three modes |
| Consensus | Alpha then Beta consensus prompts | Moderator synthesis phase |
| Output | markdown transcript | markdown transcript + JSON state |
| Runtime assumption | Claude Code installed and authenticated | OpenClaw workflow or any compatible local runner |

## What is practical today

Practical now:
- scaffold real council runs
- use the repo as a durable transcript system
- use the skill to run councils manually inside OpenClaw
- append real turns from subagents or external runners
- generate reviewable markdown artifacts

Conceptual or future work:
- native OpenClaw daemon transport
- automatic turn routing across spawned sessions
- resumable detached councils with taskflow integration
- richer research source ingestion
- transcript diffing and branching

## Architectural tradeoff versus the original

The original project is stronger on direct execution because it owns a concrete Claude Code transport. This repo is stronger on portability and auditability because it treats transcript state as the durable backbone.

That means the first version gives up some runtime elegance in exchange for being honest and adaptable inside OpenClaw.

## Suggested next implementation layer

A good next version would add a transport adapter module such as:
- `transport/generic_shell.py`
- `transport/openclaw_api.py`

Then the council engine could stay stable while execution backends vary.

## Design principle

When porting agent systems across platforms, preserve the decision process, not the old platform's illusions.

That is the design choice here.
