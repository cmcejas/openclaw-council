from __future__ import annotations

import json
import os
import shlex
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class OpenClawGatewayConfig:
    url: str | None = None
    token: str | None = None
    password: str | None = None
    session_key: str = "main"

    @classmethod
    def from_env(cls) -> "OpenClawGatewayConfig":
        return cls(
            url=os.getenv("OPENCLAW_GATEWAY_URL") or os.getenv("OPENCLAW_GATEWAY_HTTP_URL"),
            token=os.getenv("OPENCLAW_GATEWAY_TOKEN"),
            password=os.getenv("OPENCLAW_GATEWAY_PASSWORD"),
            session_key=os.getenv("OPENCLAW_SESSION_KEY", "main"),
        )

    def auth_header(self) -> dict[str, str]:
        secret = self.token or self.password
        if not secret:
            return {}
        return {"Authorization": f"Bearer {secret}"}


@dataclass
class OpenClawToolAttempt:
    tool: str
    ok: bool
    transport: str
    status_code: int | None = None
    result: Any = None
    error: str | None = None


@dataclass
class OpenClawCouncilPlan:
    topic: str
    mode: str
    directory: str
    rounds: int
    exchanges: int
    session_strategy: str
    transport_notes: list[str] = field(default_factory=list)
    sequence: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2) + "\n"


def invoke_tool_http(config: OpenClawGatewayConfig, tool: str, args: dict[str, Any] | None = None, action: str | None = None) -> OpenClawToolAttempt:
    if not config.url:
        return OpenClawToolAttempt(tool=tool, ok=False, transport="gateway-http", error="No gateway URL configured.")

    payload: dict[str, Any] = {
        "tool": tool,
        "args": args or {},
        "sessionKey": config.session_key,
    }
    if action is not None:
        payload["action"] = action

    req = urllib.request.Request(
        config.url.rstrip("/") + "/tools/invoke",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **config.auth_header(),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            body = json.loads(raw) if raw else {}
            return OpenClawToolAttempt(
                tool=tool,
                ok=bool(body.get("ok", True)),
                transport="gateway-http",
                status_code=resp.status,
                result=body.get("result", body),
                error=None if body.get("ok", True) else body.get("error", {}).get("message"),
            )
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        message = raw
        try:
            message = json.loads(raw).get("error", {}).get("message", raw)
        except json.JSONDecodeError:
            pass
        return OpenClawToolAttempt(
            tool=tool,
            ok=False,
            transport="gateway-http",
            status_code=exc.code,
            error=message,
        )
    except urllib.error.URLError as exc:
        return OpenClawToolAttempt(tool=tool, ok=False, transport="gateway-http", error=str(exc.reason))


def run_agent_cli(message: str, agent_id: str | None = None, session_id: str | None = None, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    command = ["openclaw", "agent", "--json", "--timeout", str(timeout), "--message", message]
    if agent_id:
        command.extend(["--agent", agent_id])
    if session_id:
        command.extend(["--session-id", session_id])
    return subprocess.run(command, text=True, capture_output=True)


def build_openclaw_sequence(mode: str, rounds: int, exchanges: int) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if mode == "research":
        steps.append({"phase": "research", "role": "researcher", "action": "sessions_spawn_or_inline_research", "round": 0})
        for exchange in range(1, exchanges + 1):
            steps.append(
                {
                    "phase": "grounded-brainstorm",
                    "role": "alpha" if exchange % 2 else "beta",
                    "action": "sessions_send_or_replay_turn",
                    "round": exchange,
                }
            )
        steps.append({"phase": "consensus", "role": "moderator", "action": "synthesis", "round": exchanges + 1})
        return steps

    if mode == "live":
        for exchange in range(1, exchanges + 1):
            steps.append(
                {
                    "phase": "brainstorm",
                    "role": "alpha" if exchange % 2 else "beta",
                    "action": "sessions_send_or_replay_turn",
                    "round": exchange,
                }
            )
        steps.append({"phase": "summary", "role": "moderator", "action": "synthesis", "round": exchanges + 1})
        return steps

    for round_number in range(1, rounds + 1):
        steps.append({"phase": "deliberation", "role": "alpha", "action": "sessions_send_or_replay_turn", "round": round_number})
        steps.append({"phase": "deliberation", "role": "beta", "action": "sessions_send_or_replay_turn", "round": round_number})
    steps.append({"phase": "consensus", "role": "moderator", "action": "synthesis", "round": rounds + 1})
    return steps


def build_openclaw_plan(topic: str, mode: str, directory: Path, rounds: int, exchanges: int, tool_attempts: list[OpenClawToolAttempt]) -> OpenClawCouncilPlan:
    notes = []
    if tool_attempts:
        for attempt in tool_attempts:
            if attempt.ok:
                notes.append(f"{attempt.tool} reachable via {attempt.transport}.")
            else:
                status = f"HTTP {attempt.status_code}" if attempt.status_code else "no HTTP status"
                notes.append(f"{attempt.tool} not directly callable via {attempt.transport} ({status}: {attempt.error or 'unknown error'}).")
    if not notes:
        notes.append("No direct gateway tool probe was attempted.")

    notes.append(
        "If sessions_spawn/sessions_send are blocked over /tools/invoke, the real fallback is to drive an OpenClaw agent via `openclaw agent` and let that agent call session tools inside its own run."
    )
    notes.append(
        "This helper does not claim hidden session continuity. Transcript replay remains the durable baseline unless your live OpenClaw runtime confirms stronger continuity."
    )

    return OpenClawCouncilPlan(
        topic=topic,
        mode=mode,
        directory=str(directory.resolve()),
        rounds=rounds,
        exchanges=exchanges,
        session_strategy="Prefer sessions_spawn + sessions_send when the target agent/runtime exposes them. Otherwise run transcript-first orchestration with explicit replay.",
        transport_notes=notes,
        sequence=build_openclaw_sequence(mode, rounds, exchanges),
    )


def render_orchestrator_prompt(plan: OpenClawCouncilPlan) -> str:
    sequence_lines = "\n".join(
        f"- phase={step['phase']}, round={step['round']}, role={step['role']}, action={step['action']}" for step in plan.sequence
    )
    notes = "\n".join(f"- {note}" for note in plan.transport_notes)
    return f"""You are orchestrating an OpenClaw council run.

Topic: {plan.topic}
Mode: {plan.mode}
Directory: {plan.directory}
Rounds: {plan.rounds}
Exchanges: {plan.exchanges}

Session strategy:
{plan.session_strategy}

Transport notes:
{notes}

Required behavior:
1. Use real OpenClaw session primitives if available in this runtime, especially sessions_spawn and sessions_send.
2. If those tools are unavailable, blocked by policy, or the runtime is sandbox-limited, say that plainly and fall back to transcript-first orchestration.
3. Keep roles distinct: alpha, beta, researcher when needed, moderator.
4. After each turn, persist or emit structured transcript content that includes phase, round, speaker, role, and any sources.
5. End with a moderator synthesis that separates consensus, disagreements, risks, and next actions.
6. Do not claim hidden session continuity unless you actually resumed a real session.

Suggested turn sequence:
{sequence_lines}

If session tools are available, a good pattern is:
- spawn alpha and beta sessions early with sessions_spawn when durable separate threads are useful
- use sessions_send to alternate turns and pass compact transcript replay between them
- for research mode, gather evidence first, then feed the brief into alpha and beta
- synthesize with a moderator pass at the end

If session tools are not available, do the best real fallback in one session, but keep the role separation explicit and preserve the transcript structure.
"""


def render_agent_cli_command(prompt_path: Path, agent_id: str | None = None, session_id: str | None = None, timeout: int = 600) -> str:
    parts = ["openclaw", "agent", "--json", "--timeout", shlex.quote(str(timeout))]
    if agent_id:
        parts.extend(["--agent", shlex.quote(agent_id)])
    if session_id:
        parts.extend(["--session-id", shlex.quote(session_id)])
    parts.extend(["--message", '"$(cat ' + shlex.quote(str(prompt_path)) + ')"'])
    return " ".join(parts)
