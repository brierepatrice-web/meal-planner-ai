from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from consume_meal import handle_action


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


class ConsumeMealTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        self.plan = self.data / "plans" / "2026-W26.md"
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
            | Jour 1 | Repas test | famille test | Accompagnement test | OK |
            | Jour 2 | Autre repas | autre famille | aucun | OK |

            ## Lunchs

            | Jour | Kids Lunch | Kids Type | Adult Lunch | Adult Type | Source |
            | --- | --- | --- | --- | --- | --- |
            | Jour 1 | Aucun | aucun | Aucun | aucun | test |
            """,
        )
        write(
            self.data / "recipes" / "mains" / "repas-test.md",
            """
            ---
            title: Repas test
            meal_family: famille test
            protein_type: chicken
            category: main
            ---

            # Repas test

            ## Ingredients

            - poulet | Viandes et poissons | 2
            - riz | Epicerie seche | 1
            """,
        )
        write(
            self.data / "recipes" / "mains" / "autre-repas.md",
            """
            ---
            title: Autre repas
            meal_family: autre famille
            protein_type: beef
            category: main
            ---

            # Autre repas

            ## Ingredients

            - boeuf | Viandes et poissons | 1
            """,
        )
        write(
            self.data / "recipes" / "sides" / "accompagnement-test.md",
            """
            ---
            title: Accompagnement test
            meal_family: accompagnement test
            protein_type: none
            category: side
            ---

            # Accompagnement test

            ## Ingredients

            - concombre | Fruits et legumes | 1
            """,
        )
        write(self.data / "history" / "meals.md", "# Meal History\n")
        write(self.data / "inventory" / "proteins.md", "# Proteins\n\n- poulet | 3\n- boeuf | 1")
        write(self.data / "inventory" / "pantry.md", "# Pantry\n\n- riz | 2")
        write(self.data / "inventory" / "fresh.md", "# Fresh\n\n- concombre | 1")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_consume_day_updates_history_event_log_and_targeted_inventory(self) -> None:
        dinner, deducted, review = handle_action(
            "consume",
            day="Jour 1",
            plan_path=self.plan,
            date="2026-06-29",
            data_dir=self.data,
        )

        self.assertEqual(dinner["meal_family"], "famille test")
        self.assertEqual(review, self.data / "inventory" / "consumption_notes.md")
        self.assertEqual(
            set(deducted),
            {"poulet x2 (proteins)", "riz x1 (pantry)", "concombre x1 (fresh)"},
        )
        self.assertIn("- famille test", (self.data / "history" / "meals.md").read_text(encoding="utf-8"))
        self.assertIn("| 2026-06-29 | 2026-W26 | Jour 1 | consume |", (self.data / "history" / "meal_events.md").read_text(encoding="utf-8"))
        self.assertIn("- poulet | 1", (self.data / "inventory" / "proteins.md").read_text(encoding="utf-8"))
        self.assertIn("- riz | 1", (self.data / "inventory" / "pantry.md").read_text(encoding="utf-8"))
        self.assertNotIn("- concombre", (self.data / "inventory" / "fresh.md").read_text(encoding="utf-8"))
        self.assertIn("- boeuf | 1", (self.data / "inventory" / "proteins.md").read_text(encoding="utf-8"))

    def test_consume_same_week_day_twice_does_not_rededuct_inventory(self) -> None:
        handle_action("consume", day="Jour 1", plan_path=self.plan, date="2026-06-29", data_dir=self.data)

        with self.assertRaisesRegex(ValueError, "deja marque comme consomme"):
            handle_action("consume", day="Jour 1", plan_path=self.plan, date="2026-06-29", data_dir=self.data)

        self.assertIn("- poulet | 1", (self.data / "inventory" / "proteins.md").read_text(encoding="utf-8"))

    def test_existing_history_family_on_same_date_is_not_duplicated(self) -> None:
        write(self.data / "history" / "meals.md", "# Meal History\n\n## 2026-06-29\n\n- famille test")

        handle_action("consume", day="Jour 1", plan_path=self.plan, date="2026-06-29", data_dir=self.data)

        history = (self.data / "history" / "meals.md").read_text(encoding="utf-8")
        self.assertEqual(history.count("- famille test"), 1)

    def test_cancel_and_postpone_only_write_events(self) -> None:
        handle_action("cancel", day="Jour 1", plan_path=self.plan, date="2026-06-29", note="pas faim", data_dir=self.data)
        handle_action("postpone", day="Jour 2", plan_path=self.plan, date="2026-06-30", note="demain", data_dir=self.data)

        events = (self.data / "history" / "meal_events.md").read_text(encoding="utf-8")
        self.assertIn("| 2026-06-29 | 2026-W26 | Jour 1 | cancel | Repas test | famille test | pas faim |", events)
        self.assertIn("| 2026-06-30 | 2026-W26 | Jour 2 | postpone | Autre repas | autre famille | demain |", events)
        self.assertNotIn("- famille test", (self.data / "history" / "meals.md").read_text(encoding="utf-8"))
        self.assertIn("- poulet | 3", (self.data / "inventory" / "proteins.md").read_text(encoding="utf-8"))

    def test_invalid_day_returns_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Repas introuvable"):
            handle_action("consume", day="Jour 9", plan_path=self.plan, date="2026-06-29", data_dir=self.data)


if __name__ == "__main__":
    unittest.main()
