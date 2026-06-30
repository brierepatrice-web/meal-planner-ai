from __future__ import annotations

import argparse
import sys
from pathlib import Path

from generate_grocery_list import raw_grocery_items_for_plan
from grocery_validation import validate_grocery_items, write_codex_review
from meal_os import DATA, GROCERY_CATEGORIES, latest_file, parse_plan


def print_validation_summary(result) -> None:
    print("Grocery validation OK")
    if result.merged:
        print("Merged items:")
        for item in result.merged:
            print(f"- {item}")
    else:
        print("Merged items: none")

    if result.ambiguous:
        print("Ambiguous items for Codex/manual review:")
        for item in result.ambiguous:
            print(f"- {item}")
    else:
        print("Ambiguous items: none")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and normalize a grocery list from a meal plan")
    parser.add_argument("--plan", type=Path, help="Plan Markdown a utiliser")
    parser.add_argument(
        "--ai-review",
        action="store_true",
        help="Ecrit une revue locale preparee pour Codex dans data/grocery_reviews/",
    )
    args = parser.parse_args()

    plan_path = args.plan or latest_file(DATA / "plans")
    if not plan_path:
        print("No plan found. Run scripts/commit_plan.py first.")
        return 1
    if not plan_path.exists():
        print(f"Plan not found: {plan_path}")
        return 1

    try:
        categories, skipped = raw_grocery_items_for_plan(plan_path)
        result = validate_grocery_items(categories, skipped, use_ai=args.ai_review)
    except ValueError as error:
        print(error)
        return 1

    print_validation_summary(result)
    if args.ai_review:
        meta, _, _ = parse_plan(plan_path)
        week = meta.get("week", plan_path.stem)
        out = write_codex_review(result, DATA / "grocery_reviews" / f"{week}.md")
        print(f"Codex review written: {out}")

    print("Validated categories:")
    for category in GROCERY_CATEGORIES:
        count = len(result.categories.get(category, []))
        print(f"- {category}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
