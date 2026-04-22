---
name: openclaw-council
description: Run structured multi-agent deliberation, debate, brainstorm, or research-backed synthesis inside OpenClaw. Use when a task benefits from distinct agent roles, alternating rounds, transcript capture, consensus synthesis, or replayable resume state. Especially relevant for architectural tradeoffs, code review strategy, product decisions, research comparison, and red-team versus builder analysis.
---

# OpenClaw Council

Use this skill to run a council workflow with explicit roles, durable transcript state, and honest synthesis.

## Core workflow

Use this as a thinking pattern, not rigid theater. If two roles are enough, keep it lean. If research is unnecessary, skip the researcher.

1. Clarify the topic, target directory, and desired mode: `standard`, `live`, or `research`.
2. Assign distinct roles:
   - `alpha`: rigorous systems analysis
   - `beta`: creative contrarian / edge-case hunter
   - `researcher`: optional evidence gatherer for research mode
   - `moderator`: final synthesis
3. Prefer real OpenClaw multi-agent primitives when available:
   - `sessions_spawn` for separate agent threads or detached tasks
   - `sessions_send` for alternating turns
   - subagents when the council should stay inside one parent task
4. After every turn, persist the content to a transcript file or structured state.
5. At the end, run a moderator pass that separates:
   - consensus
   - disagreements
   - risks
   - recommended next actions
6. If the work pauses, resume by replaying transcript plus explicit current task state. Do not claim hidden session continuity unless you really have it.

## Mode guide

### Standard mode

Use for deeper analysis with formal rounds.

Pattern:
1. Alpha opening analysis
2. Beta response / critique / expansion
3. Alternate for N rounds
4. Moderator synthesis

Best for:
- architecture reviews
- security or risk reviews
- codebase strategy debates
- choosing between implementation options

### Live mode

Use for faster exploratory back-and-forth.

Pattern:
1. Short alternating messages
2. Encourage concrete options and pivots
3. End with summary and decision memo

Best for:
- brainstorming
- naming and framing work
- initial design exploration
- tradeoff discovery before implementation

### Research mode

Use when evidence gathering matters before debate.

Pattern:
1. Researcher gathers sources and uncertainty notes
2. Alpha builds structured interpretation
3. Beta challenges framing and expands alternatives
4. Moderator synthesizes grounded conclusion

Best for:
- market/tool comparisons
- policy and standards review
- external ecosystem scans
- decisions where current facts matter

## Operating rules

- Distinguish verified facts from inference.
- Do not say an agent used a tool unless a tool actually ran.
- Keep role separation sharp. Avoid two agents collapsing into the same voice.
- Prefer concise turns with explicit tags like `AGREE`, `DISAGREE`, `REFINE`, `RISK`, `NEXT`, `CONSENSUS` when useful.
- If a role is weak or redundant, say so and compress the workflow instead of padding the transcript.
- If the environment lacks direct OpenClaw session APIs, fall back to transcript-first orchestration and say that plainly.

## Recommended output structure

Capture:
- topic
- mode
- directory or scope
- each turn with speaker, role, phase, round number, timestamp
- optional sources for research turns
- final consensus section

## OpenClaw mapping to the original council pattern

- Original Alpha/Beta alternating rounds map naturally to separate subagents or spawned sessions.
- Original live brainstorm maps to short alternating `sessions_send` turns or parent-managed subagent turns.
- Original research mode maps to a first research pass, then grounded debate.
- Original transcript file maps to explicit persisted state. Preserve it after each turn.
- Original resume behavior maps best to transcript replay plus whatever real session continuity your runtime actually exposes.

## Local companion CLI

If this repo is available locally, you can use the bundled CLI for scaffolding and transcript management:

```bash
openclaw-council run "Should we split the monolith?" --mode standard --rounds 4 --output-dir council-output
openclaw-council resume council-output/state.json --speaker "Agent Alpha" --role alpha --phase deliberation --round 1 --content-file alpha.md
openclaw-council render council-output/state.json
```

## Honest limitations

This skill does not itself guarantee:
- automatic OpenClaw daemon integration
- true concurrent sessions
- hidden session-memory replay
- autonomous research without available search/fetch tools

Treat transcript replay as the portable baseline. If your runtime provides stronger session primitives, use them and still preserve transcript state.
