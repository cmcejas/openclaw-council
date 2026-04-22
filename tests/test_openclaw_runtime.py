import unittest
from pathlib import Path

from openclaw_council.openclaw_runtime import build_openclaw_plan, render_orchestrator_prompt


class OpenClawRuntimeTests(unittest.TestCase):
    def test_build_openclaw_plan_standard_sequence(self) -> None:
        plan = build_openclaw_plan(
            topic="Should we split the monolith?",
            mode="standard",
            directory=Path("."),
            rounds=2,
            exchanges=5,
            tool_attempts=[],
        )

        self.assertEqual(
            plan.sequence,
            [
                {"phase": "deliberation", "role": "alpha", "action": "sessions_send_or_replay_turn", "round": 1},
                {"phase": "deliberation", "role": "beta", "action": "sessions_send_or_replay_turn", "round": 1},
                {"phase": "deliberation", "role": "alpha", "action": "sessions_send_or_replay_turn", "round": 2},
                {"phase": "deliberation", "role": "beta", "action": "sessions_send_or_replay_turn", "round": 2},
                {"phase": "consensus", "role": "moderator", "action": "synthesis", "round": 3},
            ],
        )

    def test_render_orchestrator_prompt_mentions_session_tools(self) -> None:
        plan = build_openclaw_plan(
            topic="Evaluate auth risks",
            mode="research",
            directory=Path("."),
            rounds=3,
            exchanges=2,
            tool_attempts=[],
        )

        prompt = render_orchestrator_prompt(plan)
        self.assertIn("sessions_spawn", prompt)
        self.assertIn("sessions_send", prompt)
        self.assertIn("research", prompt.lower())


if __name__ == "__main__":
    unittest.main()
