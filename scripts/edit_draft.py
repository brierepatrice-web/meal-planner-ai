from __future__ import annotations

import argparse
import sys
from pathlib import Path

from meal_os import DATA, latest_file
from score_plan import score_plan


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip("|").split("|")]


def render_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def update_score(text: str, draft_path: Path) -> str:
    marker = "## Score"
    if marker not in text:
        return text.rstrip() + "\n\n## Score\n\nLe score est calcule apres ecriture du plan.\n"
    before, _ = text.split(marker, 1)
    scores = score_plan(draft_path)
    rendered = "\n".join(f"- {key}: {value}" for key, value in scores.items())
    return before.rstrip() + f"\n\n{marker}\n\n{rendered}\n"


def edit_draft(draft_path: Path, args: argparse.Namespace) -> bool:
    lines = draft_path.read_text(encoding="utf-8").splitlines()
    section = None
    changed = False
    updated = []

    for line in lines:
        if line.startswith("## Soupers"):
            section = "dinners"
            updated.append(line)
            continue
        if line.startswith("## Lunchs"):
            section = "lunches"
            updated.append(line)
            continue
        if line.startswith("## "):
            section = None
            updated.append(line)
            continue
        if not line.startswith("|") or "---" in line:
            updated.append(line)
            continue

        cells = split_row(line)
        if not cells or cells[0] != args.slot or cells[0] in {"Jour", "Day", "Slot"}:
            updated.append(line)
            continue

        if section == "dinners" and len(cells) >= 5:
            if args.dinner_title:
                cells[1] = args.dinner_title
            if args.meal_family:
                cells[2] = args.meal_family
            if args.side:
                cells[3] = args.side
            if args.notes:
                cells[4] = args.notes
            changed = True
            updated.append(render_row(cells))
            continue

        if section == "lunches" and len(cells) >= 6:
            if args.kids_lunch:
                cells[1] = args.kids_lunch
            if args.kids_type:
                cells[2] = args.kids_type
            if args.adult_lunch:
                cells[3] = args.adult_lunch
            if args.adult_type:
                cells[4] = args.adult_type
            if args.source:
                cells[5] = args.source
            changed = True
            updated.append(render_row(cells))
            continue

        updated.append(line)

    if changed:
        draft_path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")
        draft_path.write_text(update_score(draft_path.read_text(encoding="utf-8"), draft_path), encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Edit a draft meal plan slot")
    parser.add_argument("--draft", type=Path, help="Draft plan Markdown to edit")
    parser.add_argument("--slot", required=True, help="Slot to edit, e.g. Jour 3")
    parser.add_argument("--dinner-title")
    parser.add_argument("--meal-family")
    parser.add_argument("--side")
    parser.add_argument("--notes")
    parser.add_argument("--kids-lunch")
    parser.add_argument("--kids-type")
    parser.add_argument("--adult-lunch")
    parser.add_argument("--adult-type")
    parser.add_argument("--source")
    args = parser.parse_args()

    draft_path = args.draft or latest_file(DATA / "drafts")
    if not draft_path:
        print("No draft found. Run scripts/plan_week.py first.")
        return 1
    if not draft_path.exists():
        print(f"Draft not found: {draft_path}")
        return 1
    if not edit_draft(draft_path, args):
        print(f"No matching editable row found for {args.slot}.")
        return 1
    print(f"Draft updated: {draft_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
