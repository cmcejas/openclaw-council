import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from openclaw_council.cli import (
    CouncilState,
    TranscriptEntry,
    escape_markdown_table_cell,
    render_markdown,
)


class CliRenderingTests(unittest.TestCase):
    def test_escape_markdown_table_cell_escapes_pipes_and_newlines(self) -> None:
        self.assertEqual(
            escape_markdown_table_cell("schools | venues\nnext"),
            "schools \\| venues<br>next",
        )

    def test_render_markdown_escapes_topic_in_summary_table(self) -> None:
        state = CouncilState(
            version="0.2.0",
            mode="standard",
            topic="Should Lockup support schools | venues first?",
            directory=str(Path(".").resolve()),
            started_at="2026-04-22T00:00:00+00:00",
            updated_at="2026-04-22T00:00:00+00:00",
            rounds_planned=1,
            exchanges_planned=2,
            entries=[
                TranscriptEntry(
                    phase="deliberation",
                    round_number=1,
                    speaker="Agent Alpha",
                    role="alpha",
                    content="AGREE keep the pilot narrow.",
                )
            ],
        )

        rendered = render_markdown(state)

        self.assertIn("| Topic | Should Lockup support schools \\| venues first? |", rendered)
        self.assertIn("### Agent Alpha (round 1, role: alpha)", rendered)


if __name__ == "__main__":
    unittest.main()
