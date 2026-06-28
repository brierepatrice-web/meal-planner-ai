from __future__ import annotations

import argparse
import sys
from pathlib import Path

from generate_grocery_list import write_grocery_list
from meal_os import (
    DATA,
    frontmatter,
    latest_file,
    parse_frontmatter,
    parse_plan,
    read_pending_recipes,
    read_recipes,
    recipe_restriction_violations,
    slug,
)


def active_recipe_path(title: str) -> Path:
    base = DATA / "recipes" / "mains" / f"{slug(title)}.md"
    if not base.exists():
        return base
    suffix = 2
    while True:
        candidate = DATA / "recipes" / "mains" / f"{slug(title)}-{suffix}.md"
        if not candidate.exists():
            return candidate
        suffix += 1


def activate_pending_recipes(draft_path: Path) -> list[Path]:
    _, dinners, _ = parse_plan(draft_path)
    dinner_titles = {dinner["title"] for dinner in dinners}
    active_titles = {recipe["title"] for recipe in read_recipes("main")}
    activated = []

    for recipe in read_pending_recipes(draft_path, "main"):
        if recipe["title"] not in dinner_titles or recipe["title"] in active_titles:
            continue
        violations = recipe_restriction_violations(recipe)
        if violations:
            raise ValueError(f"Pending recipe '{recipe['title']}' is forbidden: {', '.join(violations)}")
        out = active_recipe_path(recipe["title"])
        out.write_text(recipe["path"].read_text(encoding="utf-8"), encoding="utf-8")
        activated.append(out)
        active_titles.add(recipe["title"])

    return activated


def write_committed_plan(draft_path: Path) -> Path:
    meta, body = parse_frontmatter(draft_path)
    week = meta.get("week", draft_path.stem)
    meta["status"] = "committed"
    out = DATA / "plans" / f"{week}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(frontmatter(meta).rstrip() + "\n\n" + body.lstrip(), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Commit a draft meal plan and generate its grocery list")
    parser.add_argument("--draft", type=Path, help="Draft plan Markdown to commit")
    args = parser.parse_args()
    draft_path = args.draft or latest_file(DATA / "drafts")
    if not draft_path:
        print("No draft found. Run scripts/plan_week.py first.")
        return 1
    if not draft_path.exists():
        print(f"Draft not found: {draft_path}")
        return 1

    meta, _, _ = parse_plan(draft_path)
    if meta.get("status") != "draft":
        print(f"Refusing to commit non-draft plan with status: {meta.get('status')}")
        return 1

    try:
        activated = activate_pending_recipes(draft_path)
        plan_path = write_committed_plan(draft_path)
        grocery_path = write_grocery_list(plan_path)
    except ValueError as error:
        print(error)
        return 1

    print(f"Committed plan: {plan_path}")
    print(f"Activated pending recipes: {len(activated)}")
    for path in activated:
        print(f"- {path}")
    print(f"Grocery list written: {grocery_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
