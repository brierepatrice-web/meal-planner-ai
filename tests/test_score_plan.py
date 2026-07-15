from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from score_plan import score_plan


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


class ScorePlanTests(unittest.TestCase):
    def test_leftover_usage_score_reads_new_restants_utilises_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "2026-W26.md"
            write(
                plan,
                """
                ---
                week: 2026-W26
                season: saison_chaude
                status: committed
                ---

                # Plan

                ## Soupers

                | Jour | Recipe | Meal Family | Side | Notes |
                | --- | --- | --- | --- | --- |
                | Jour 1 | Tacos de boeuf et haricots | tacos | aucun | OK |

                ## Lunchs

                | Jour | Kids Lunch | Kids Type | Adult Lunch | Adult Type | Source |
                | --- | --- | --- | --- | --- | --- |
                | Jour 2 | Wrap froid de restants - Tacos de boeuf et haricots | wrap | Wrap froid de restants - Tacos de boeuf et haricots | wrap | restants de Jour 1; restants utilises: 2 |
                """,
            )

            scores = score_plan(plan)

        self.assertEqual(scores["leftover_usage_score"], 50)


if __name__ == "__main__":
    unittest.main()
