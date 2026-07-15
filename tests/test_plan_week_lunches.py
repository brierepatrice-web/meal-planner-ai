from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from plan_week import build_lunches


def dinner(day: str, title: str, portions: int, style: str = "bol froid") -> dict:
    return {
        "day": day,
        "title": title,
        "leftover_friendly": portions > 0,
        "leftover_lunch_portions": portions,
        "leftover_lunch_portions_remaining": portions,
        "leftover_lunch_portions_used": 0,
        "leftover_lunch_style": style,
        "kids_leftover_ok": True,
        "adult_leftover_ok": True,
    }


class PlanWeekLunchTests(unittest.TestCase):
    def test_day_one_lunch_does_not_use_same_day_leftovers(self) -> None:
        lunches = build_lunches(
            [dinner("Jour 1", "Souper jour 1", 4)],
            {"requires_child_lunches": True},
        )

        self.assertNotIn("Souper jour 1", lunches[0]["kids_lunch"])
        self.assertNotIn("Souper jour 1", lunches[0]["adult_lunch"])
        self.assertIn("restants utilises: 0", lunches[0]["source"])

    def test_next_day_can_use_previous_day_leftovers_for_kids_and_adults(self) -> None:
        dinners = [
            dinner("Jour 1", "Souper jour 1", 2),
            dinner("Jour 2", "Souper jour 2", 4),
        ]

        lunches = build_lunches(dinners, {"requires_child_lunches": True})

        self.assertIn("Souper jour 1", lunches[1]["kids_lunch"])
        self.assertIn("Souper jour 1", lunches[1]["adult_lunch"])
        self.assertIn("restants de Jour 1", lunches[1]["source"])
        self.assertIn("restants utilises: 2", lunches[1]["source"])
        self.assertEqual(dinners[0]["leftover_lunch_portions_remaining"], 0)

    def test_leftovers_are_chosen_from_previous_days_only_most_recent_first(self) -> None:
        dinners = [
            dinner("Jour 1", "Souper jour 1", 4),
            dinner("Jour 2", "Souper jour 2", 4),
            dinner("Jour 3", "Souper jour 3", 4),
        ]

        lunches = build_lunches(dinners, {"requires_child_lunches": True})

        self.assertNotIn("Souper jour 1", lunches[0]["kids_lunch"])
        self.assertIn("Souper jour 1", lunches[1]["kids_lunch"])
        self.assertIn("Souper jour 2", lunches[2]["kids_lunch"])
        self.assertNotIn("Souper jour 3", lunches[2]["kids_lunch"])
        self.assertIn("restants de Jour 2", lunches[2]["source"])


if __name__ == "__main__":
    unittest.main()
