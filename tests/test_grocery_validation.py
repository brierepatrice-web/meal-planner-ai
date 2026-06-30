from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from grocery_validation import validate_grocery_items
from meal_os import DATA, GROCERY_CATEGORIES
from generate_grocery_list import raw_grocery_items_for_plan


def empty_categories() -> dict[str, list[str]]:
    return {category: [] for category in GROCERY_CATEGORIES}


class GroceryValidationTests(unittest.TestCase):
    def test_merges_duplicate_counts(self) -> None:
        categories = empty_categories()
        categories["Fruits et legumes"] = ["- concombres (2)", "- concombres (1)"]

        result = validate_grocery_items(categories, [])

        self.assertIn("- concombres (3)", result.categories["Fruits et legumes"])
        self.assertEqual(len(result.categories["Fruits et legumes"]), 1)

    def test_merges_same_numeric_unit(self) -> None:
        categories = empty_categories()
        categories["Epicerie seche"] = ["- riz basmati (2 tasses)", "- riz basmati (1 tasse)"]

        result = validate_grocery_items(categories, [])

        self.assertIn("- riz basmati (3 tasses)", result.categories["Epicerie seche"])
        self.assertEqual(len(result.categories["Epicerie seche"]), 1)

    def test_does_not_merge_unmergeable_units(self) -> None:
        categories = empty_categories()
        categories["Fruits et legumes"] = ["- pommes de terre (800 g)", "- pommes de terre (1 sac)"]

        result = validate_grocery_items(categories, [])

        self.assertIn("- pommes de terre (800 g)", result.categories["Fruits et legumes"])
        self.assertIn("- pommes de terre (1 sac)", result.categories["Fruits et legumes"])

    def test_preserves_recurrent_items(self) -> None:
        categories = empty_categories()
        categories["Produits laitiers"] = ["- lait en poches (1 sac) [recurrent]"]

        result = validate_grocery_items(categories, [])

        self.assertEqual(result.categories["Produits laitiers"], ["- lait en poches (1 sac) [recurrent]"])

    def test_keeps_items_in_existing_categories(self) -> None:
        categories = empty_categories()
        categories["Condiments"] = ["- salsa (1 pot)"]

        result = validate_grocery_items(categories, [])

        self.assertEqual(result.categories["Condiments"], ["- salsa (1 pot)"])

    def test_current_week_duplicates_are_consolidated(self) -> None:
        plan_path = DATA / "plans" / "2026-W26.md"
        categories, skipped = raw_grocery_items_for_plan(plan_path)

        result = validate_grocery_items(categories, skipped)

        self.assertIn("- citron (2)", result.categories["Fruits et legumes"])
        self.assertIn("- concombre (2)", result.categories["Fruits et legumes"])
        self.assertIn("- pois chiches (1 boite 540 ml)", result.categories["Epicerie seche"])
        self.assertIn("- feta emiettee (3/4 tasse)", result.categories["Produits laitiers"])
        self.assertIn("- riz basmati (3 tasses)", result.categories["Epicerie seche"])
        self.assertNotIn("- riz basmati (2 tasses)", result.categories["Epicerie seche"])
        self.assertNotIn("- riz basmati (1 tasse)", result.categories["Epicerie seche"])


if __name__ == "__main__":
    unittest.main()
