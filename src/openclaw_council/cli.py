from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import __version__


ROLE_LIBRARY = {
    "alpha": {
        "title": "Agent Alpha",
        "stance": "rigorous systems analyst",
        "goal": "decompose the problem, test assumptions, and produce evidence-ranked arguments",
        "instructions": [
            "Map the problem into a few concrete dimensions before recommending action.",
            "Separate verified facts, strong inference, and open assumptions.",
            "Prefer evidence, constraints, and implementation consequences over slogans.",
        ],
    },
    "beta": {
        "title": "Agent Beta",
        "stance": "creative contrarian",
        "goal": "challenge framing, surface edge cases, and expand the option space",
        "instructions": [
            "Look for hidden assumptions, failure modes, and second-order effects.",
            "Offer at least one plausible alternate framing or approach.",
            "Agree explicitly when Alpha is solid, then push on what is still missing.",
        ],
    },
    "researcher": {
        "title": "Researcher",
        "stance": "evidence scout",
        "goal": "gather external facts, sources, and uncertainty notes before deliberation",
        "instructions": [
            "Collect concrete sources, current facts, and obvious gaps in available evidence.",
            "Call out weak, stale, or missing evidence instead of smoothing over it.",
            "Produce a brief that downstream agents can debate against.",
        ],
    },
    "moderator": {
        "title": "Moderator",
        "stance": "synthesis lead",
        "goal": "merge discussion into a useful conclusion with explicit consensus and open issues",
        "instructions": [
            "Summarize consensus, disagreements, risks, and next actions separately.",
            "Do not pretend the council agreed when it did not.",
            "Prefer a reviewable decision memo over a vague summary.",
        ],
    },
}


MODE_GUIDANCE = {
    "standard": [
        "Run formal alternating rounds.",
        "Each turn should build on the previous turn instead of restarting analysis.",
        "Aim for a final decision memo after the final round.",
    ],
    "live": [
        "Use short, energetic exchanges instead of long essays.",
        "Bias toward option discovery, tradeoffs, and practical next steps.",
        "Keep momentum. Do not repeat the same point with different wording.",
    ],
    "research": [
        "Ground claims in current evidence where possible.",
        "Carry forward sources and uncertainty notes into later turns.",
        "Separate what the council knows from what it still needs to verify.",
    ],
}


@dataclass
class TranscriptEntry:
    phase: str
    round_number: int
    speaker: str
    role: str
    content: str
    tags: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    entry_kind: str = "response"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CouncilState:
    version: str
    mode: str
    topic: str
    directory: str
    started_at: str
    updated_at: str
    rounds_planned: int
    exchanges_planned: int
    entries: list[TranscriptEntry] = field(default_factory=list)

    def add(self, entry: TranscriptEntry) -> None:
        self.entries.append(entry)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_json(self) -> str:
        return json.dumps(
            {
                **asdict(self),
                "entries": [asdict(entry) for entry in self.entries],
            },
            indent=2,
        )

    @classmethod
    def from_path(cls, path: Path) -> "CouncilState":
        raw = json.loads(path.read_text(encoding="utf-8"))
        entries = [TranscriptEntry(**entry) for entry in raw.pop("entries", [])]
        state = cls(**raw)
        state.entries = entries
        return state


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def summarize_prior(prior: Iterable[TranscriptEntry], limit: int = 6, chars: int = 280) -> str:
    items = list(prior)
    if not items:
        return "(No prior transcript yet.)"
    recent = items[-limit:]
    lines = []
    for entry in recent:
        compact = " ".join(entry.content.split())
        if len(compact) > chars:
            compact = compact[: chars - 3] + "..."
        lines.append(f"[{entry.phase} #{entry.round_number}] {entry.speaker}: {compact}")
    return "\n".join(lines)


def build_role_prompt(role: str, topic: str, mode: str, round_number: int, prior: Iterable[TranscriptEntry]) -> str:
    meta = ROLE_LIBRARY[role]
    transcript = summarize_prior(prior)
    role_instructions = "\n".join(f"- {item}" for item in meta["instructions"])
    mode_instructions = "\n".join(f"- {item}" for item in MODE_GUIDANCE[mode])

    if role == "moderator":
        output_shape = (
            "Write sections named CONSENSUS, DISAGREEMENTS, RISKS, and NEXT ACTIONS."
        )
    elif role == "researcher":
        output_shape = (
            "Write sections named FINDINGS, SOURCES, UNCERTAINTIES, and QUESTIONS FOR THE COUNCIL."
        )
    else:
        output_shape = (
            "Use compact markdown bullets. Mark key bullets with AGREE, DISAGREE, REFINE, RISK, or NEXT when useful."
        )

    return (
        f"You are {meta['title']} in an OpenClaw-style council.\n"
        f"Role stance: {meta['stance']}.\n"
        f"Mission: {meta['goal']}.\n\n"
        f"Mode: {mode}\n"
        f"Topic: {topic}\n"
        f"Current round: {round_number}\n\n"
        f"Role guidance:\n{role_instructions}\n\n"
        f"Mode guidance:\n{mode_instructions}\n\n"
        f"Output expectations:\n- {output_shape}\n- Distinguish verified facts from inference.\n- Do not pretend to have used tools you did not use.\n- Be concrete, not decorative.\n\n"
        f"Transcript so far:\n{transcript}\n"
    )


def infer_tags(content: str) -> list[str]:
    tags = []
    for tag in ("AGREE", "DISAGREE", "REFINE", "RISK", "NEXT", "CONSENSUS", "RESEARCH"):
        if re.search(rf"\b{tag}\b", content):
            tags.append(tag)
    return tags


def init_state(args: argparse.Namespace) -> CouncilState:
    return CouncilState(
        version=__version__,
        mode=args.mode,
        topic=args.topic,
        directory=str(Path(args.directory).resolve()),
        started_at=utc_now(),
        updated_at=utc_now(),
        rounds_planned=args.rounds,
        exchanges_planned=args.exchanges,
    )


def save_state(state: CouncilState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.to_json() + "\n", encoding="utf-8")


def render_markdown(state: CouncilState) -> str:
    lines = [
        "# OpenClaw Council Transcript",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Topic | {state.topic} |",
        f"| Mode | {state.mode} |",
        f"| Directory | {state.directory} |",
        f"| Started | {state.started_at} |",
        f"| Updated | {state.updated_at} |",
        f"| Planned rounds | {state.rounds_planned} |",
        f"| Planned exchanges | {state.exchanges_planned} |",
        "",
    ]

    current_phase = None
    for entry in state.entries:
        phase_heading = f"## {entry.phase.title()}"
        if phase_heading != current_phase:
            current_phase = phase_heading
            lines.extend([phase_heading, ""])
        lines.extend(
            [
                f"### {entry.speaker} (round {entry.round_number}, role: {entry.role})",
                "",
                f"Entry kind: {entry.entry_kind}  ",
                f"Tags: {', '.join(entry.tags) if entry.tags else 'none'}  ",
                f"Timestamp: {entry.timestamp}",
                "",
                entry.content.rstrip(),
                "",
            ]
        )
        if entry.sources:
            lines.append("Sources:")
            for source in entry.sources:
                lines.append(f"- {source}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(state: CouncilState, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "state.json"
    transcript_path = output_dir / "transcript.md"
    save_state(state, state_path)
    transcript_path.write_text(render_markdown(state), encoding="utf-8")
    return state_path, transcript_path


def run_agent_command(command_template: str, prompt: str, workdir: Path) -> str:
    command = command_template.replace("{prompt}", prompt)
    result = subprocess.run(
        command,
        cwd=str(workdir),
        shell=True,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Agent command failed with exit code {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip() or "(Agent returned no stdout)"


def add_scaffold_entry(state: CouncilState, phase: str, round_number: int, speaker: str, role: str, content: str) -> None:
    state.add(
        TranscriptEntry(
            phase=phase,
            round_number=round_number,
            speaker=speaker,
            role=role,
            content=content,
            tags=[],
            entry_kind="prompt",
        )
    )


def scaffold_standard(state: CouncilState) -> None:
    for round_number in range(1, state.rounds_planned + 1):
        alpha = build_role_prompt("alpha", state.topic, state.mode, round_number, state.entries)
        beta = build_role_prompt("beta", state.topic, state.mode, round_number, state.entries)
        add_scaffold_entry(state, "deliberation", round_number, "Agent Alpha", "alpha", alpha)
        add_scaffold_entry(state, "deliberation", round_number, "Agent Beta", "beta", beta)

    moderator = build_role_prompt("moderator", state.topic, state.mode, state.rounds_planned + 1, state.entries)
    add_scaffold_entry(state, "consensus", state.rounds_planned + 1, "Moderator", "moderator", moderator)


def scaffold_live(state: CouncilState) -> None:
    speaker_cycle = [("Agent Alpha", "alpha"), ("Agent Beta", "beta")]
    for exchange in range(1, state.exchanges_planned + 1):
        speaker, role = speaker_cycle[(exchange - 1) % 2]
        prompt = build_role_prompt(role, state.topic, state.mode, exchange, state.entries)
        add_scaffold_entry(state, "brainstorm", exchange, speaker, role, prompt)
    summary = build_role_prompt("moderator", state.topic, state.mode, state.exchanges_planned + 1, state.entries)
    add_scaffold_entry(state, "summary", state.exchanges_planned + 1, "Moderator", "moderator", summary)


def scaffold_research(state: CouncilState) -> None:
    research = build_role_prompt("researcher", state.topic, state.mode, 0, state.entries)
    add_scaffold_entry(state, "research", 0, "Researcher", "researcher", research)
    for exchange in range(1, state.exchanges_planned + 1):
        speaker, role = ("Agent Alpha", "alpha") if exchange % 2 else ("Agent Beta", "beta")
        prompt = build_role_prompt(role, state.topic, state.mode, exchange, state.entries)
        add_scaffold_entry(state, "grounded-brainstorm", exchange, speaker, role, prompt)
    summary = build_role_prompt("moderator", state.topic, state.mode, state.exchanges_planned + 1, state.entries)
    add_scaffold_entry(state, "consensus", state.exchanges_planned + 1, "Moderator", "moderator", summary)


def execute_mode(state: CouncilState, args: argparse.Namespace) -> None:
    if args.agent_command:
        if state.mode == "standard":
            for round_number in range(1, state.rounds_planned + 1):
                for speaker, role, phase in [
                    ("Agent Alpha", "alpha", "deliberation"),
                    ("Agent Beta", "beta", "deliberation"),
                ]:
                    prompt = build_role_prompt(role, state.topic, state.mode, round_number, state.entries)
                    content = run_agent_command(args.agent_command, prompt, Path(state.directory))
                    state.add(
                        TranscriptEntry(
                            phase=phase,
                            round_number=round_number,
                            speaker=speaker,
                            role=role,
                            content=content,
                            tags=infer_tags(content),
                            entry_kind="response",
                        )
                    )
            moderator_prompt = build_role_prompt("moderator", state.topic, state.mode, state.rounds_planned + 1, state.entries)
            summary = run_agent_command(args.agent_command, moderator_prompt, Path(state.directory))
            state.add(
                TranscriptEntry(
                    phase="consensus",
                    round_number=state.rounds_planned + 1,
                    speaker="Moderator",
                    role="moderator",
                    content=summary,
                    tags=infer_tags(summary),
                    entry_kind="response",
                )
            )
        elif state.mode == "live":
            for exchange in range(1, state.exchanges_planned + 1):
                speaker, role = ("Agent Alpha", "alpha") if exchange % 2 else ("Agent Beta", "beta")
                prompt = build_role_prompt(role, state.topic, state.mode, exchange, state.entries)
                content = run_agent_command(args.agent_command, prompt, Path(state.directory))
                state.add(
                    TranscriptEntry(
                        phase="brainstorm",
                        round_number=exchange,
                        speaker=speaker,
                        role=role,
                        content=content,
                        tags=infer_tags(content),
                        entry_kind="response",
                    )
                )
            summary_prompt = build_role_prompt("moderator", state.topic, state.mode, state.exchanges_planned + 1, state.entries)
            summary = run_agent_command(args.agent_command, summary_prompt, Path(state.directory))
            state.add(
                TranscriptEntry(
                    phase="summary",
                    round_number=state.exchanges_planned + 1,
                    speaker="Moderator",
                    role="moderator",
                    content=summary,
                    tags=infer_tags(summary),
                    entry_kind="response",
                )
            )
        else:
            research_prompt = build_role_prompt("researcher", state.topic, state.mode, 0, state.entries)
            research = run_agent_command(args.agent_command, research_prompt, Path(state.directory))
            state.add(
                TranscriptEntry(
                    phase="research",
                    round_number=0,
                    speaker="Researcher",
                    role="researcher",
                    content=research,
                    tags=infer_tags(research),
                    entry_kind="response",
                )
            )
            for exchange in range(1, state.exchanges_planned + 1):
                speaker, role = ("Agent Alpha", "alpha") if exchange % 2 else ("Agent Beta", "beta")
                prompt = build_role_prompt(role, state.topic, state.mode, exchange, state.entries)
                content = run_agent_command(args.agent_command, prompt, Path(state.directory))
                state.add(
                    TranscriptEntry(
                        phase="grounded-brainstorm",
                        round_number=exchange,
                        speaker=speaker,
                        role=role,
                        content=content,
                        tags=infer_tags(content),
                        entry_kind="response",
                    )
                )
            summary_prompt = build_role_prompt("moderator", state.topic, state.mode, state.exchanges_planned + 1, state.entries)
            summary = run_agent_command(args.agent_command, summary_prompt, Path(state.directory))
            state.add(
                TranscriptEntry(
                    phase="consensus",
                    round_number=state.exchanges_planned + 1,
                    speaker="Moderator",
                    role="moderator",
                    content=summary,
                    tags=infer_tags(summary),
                    entry_kind="response",
                )
            )
        return

    if state.mode == "standard":
        scaffold_standard(state)
    elif state.mode == "live":
        scaffold_live(state)
    else:
        scaffold_research(state)


def append_manual_entry(state: CouncilState, speaker: str, role: str, phase: str, round_number: int, content: str, sources: list[str]) -> None:
    state.add(
        TranscriptEntry(
            phase=phase,
            round_number=round_number,
            speaker=speaker,
            role=role,
            content=content,
            tags=infer_tags(content),
            sources=sources,
            entry_kind="response",
        )
    )


def validate_run_args(args: argparse.Namespace) -> None:
    if args.mode == "standard" and args.rounds < 1:
        raise SystemExit("--rounds must be at least 1 in standard mode.")
    if args.mode in {"live", "research"} and args.exchanges < 1:
        raise SystemExit("--exchanges must be at least 1 in live or research mode.")
    if args.agent_command and "{prompt}" not in args.agent_command:
        raise SystemExit("--agent-command must include the literal placeholder {prompt}.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenClaw-friendly council scaffolder and transcript runner")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Create or execute a council run")
    run.add_argument("topic")
    run.add_argument("--mode", choices=["standard", "live", "research"], default="standard")
    run.add_argument("--directory", default=".")
    run.add_argument("--rounds", type=int, default=5)
    run.add_argument("--exchanges", type=int, default=10)
    run.add_argument("--output-dir", default="council-output")
    run.add_argument(
        "--agent-command",
        help="Optional shell command template used for each turn. Use {prompt} as the insertion placeholder.",
    )

    resume = sub.add_parser("resume", help="Append manual entries to an existing state file")
    resume.add_argument("state_file")
    resume.add_argument("--speaker", required=True)
    resume.add_argument("--role", required=True)
    resume.add_argument("--phase", required=True)
    resume.add_argument("--round", dest="round_number", required=True, type=int)
    resume.add_argument("--content-file", help="Read content from a file instead of stdin")
    resume.add_argument("--source", action="append", default=[])

    render = sub.add_parser("render", help="Render markdown transcript from a state file")
    render.add_argument("state_file")
    render.add_argument("--output", default="-")

    sub.add_parser("version", help="Print version")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.command == "version":
        print(__version__)
        return 0

    if args.command == "run":
        validate_run_args(args)
        state = init_state(args)
        execute_mode(state, args)
        state_path, transcript_path = write_outputs(state, Path(args.output_dir))
        print(f"state: {state_path}")
        print(f"transcript: {transcript_path}")
        print(f"entries: {len(state.entries)}")
        return 0

    if args.command == "resume":
        state_path = Path(args.state_file)
        state = CouncilState.from_path(state_path)
        if args.content_file:
            content = Path(args.content_file).read_text(encoding="utf-8")
        else:
            content = sys.stdin.read().strip()
        if not content:
            raise SystemExit("No content provided. Use --content-file or pipe content on stdin.")
        append_manual_entry(state, args.speaker, args.role, args.phase, args.round_number, content, args.source)
        transcript_path = state_path.with_name("transcript.md")
        state_path.write_text(state.to_json() + "\n", encoding="utf-8")
        transcript_path.write_text(render_markdown(state), encoding="utf-8")
        print(f"updated: {state_path}")
        print(f"transcript: {transcript_path}")
        return 0

    if args.command == "render":
        state = CouncilState.from_path(Path(args.state_file))
        output = render_markdown(state)
        if args.output == "-":
            sys.stdout.write(output)
        else:
            Path(args.output).write_text(output, encoding="utf-8")
            print(args.output)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
