from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_meal_plan_html import render_html


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


class GenerateMealPlanHtmlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan = self.root / "2026-W26.md"
        write(
            self.root / "2026-W26_recipes" / "repas-test.md",
            """
            ---
            title: Repas test
            portions: 4
            meal_family: famille test
            protein_type: chicken
            prep_time: 10
            cook_time: 20
            active_time: 15
            category: main
            ---

            # Repas test

            ## Ingredients

            - poulet | Viandes et poissons | 2

            ## Methode

            - 1. Cuire le repas.
            """,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_render_html_shows_kids_and_adult_lunches_in_agenda(self) -> None:
        write(
            self.plan,
            """
            ---
            week: 2026-W26
            status: committed
            ---

            # Plan

            ## Soupers

            | Jour | Recipe | Meal Family | Side | Notes |
            | --- | --- | --- | --- | --- |
            | Jour 1 | Repas test | famille test | aucun | OK |

            ## Lunchs

            | Jour | Kids Lunch | Kids Type | Adult Lunch | Adult Type | Source |
            | --- | --- | --- | --- | --- | --- |
            | Jour 1 | Sandwich froid test | sandwich | Bol rechauffe test | restants rechauffes | restants; test |
            """,
        )

        html = render_html(self.plan)

        self.assertIn("Lunch enfant", html)
        self.assertIn("Sandwich froid test", html)
        self.assertIn("Lunch adulte", html)
        self.assertIn("Bol rechauffe test", html)
        self.assertIn("restants; test", html)

    def test_render_html_handles_missing_lunch_for_day(self) -> None:
        write(
            self.plan,
            """
            ---
            week: 2026-W26
            status: committed
            ---

            # Plan

            ## Soupers

            | Jour | Recipe | Meal Family | Side | Notes |
            | --- | --- | --- | --- | --- |
            | Jour 1 | Repas test | famille test | aucun | OK |
            """,
        )

        html = render_html(self.plan)

        self.assertIn("Repas test", html)
        self.assertNotIn("Lunch enfant", html)
        self.assertNotIn("Lunch adulte", html)


if __name__ == "__main__":
    unittest.main()
