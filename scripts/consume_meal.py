from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from meal_os import (
    DATA,
    canonical_ingredient_name,
    ingredient_units,
    integer_quantity,
    item_name,
    item_quantity,
    normalize_text,
    parse_frontmatter,
    parse_ingredients,
    parse_plan,
    recipe_restriction_violations,
)


ACTIONS = {"consume", "cancel", "postpone"}
EVENT_COLUMNS = ["Date", "Week", "Day", "Action", "Recipe", "Meal Family", "Note"]


def latest_plan(data_dir: Path = DATA) -> Path | None:
    plans = sorted((data_dir / "plans").glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    return plans[0] if plans else None


def markdown_cell(value: str) -> str:
    return str(value).replace("|", "/").replace("\n", " ").strip()


def ensure_event_log(data_dir: Path = DATA) -> Path:
    path = data_dir / "history" / "meal_events.md"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Meal Events\n\n"
            + "| "
            + " | ".join(EVENT_COLUMNS)
            + " |\n"
            + "| "
            + " | ".join("---" for _ in EVENT_COLUMNS)
            + " |\n",
            encoding="utf-8",
        )
    return path


def read_events(data_dir: Path = DATA) -> list[dict[str, str]]:
    path = ensure_event_log(data_dir)
    events: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped or "Date | Week" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= len(EVENT_COLUMNS):
            events.append(dict(zip(EVENT_COLUMNS, cells)))
    return events


def append_event(
    data_dir: Path,
    *,
    date: str,
    week: str,
    day: str,
    action: str,
    recipe: str,
    meal_family: str,
    note: str,
) -> None:
    path = ensure_event_log(data_dir)
    row = [date, week, day, action, recipe, meal_family, note]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("| " + " | ".join(markdown_cell(value) for value in row) + " |\n")


def consumed_event_exists(data_dir: Path, week: str, day: str) -> bool:
    return any(event["Week"] == week and event["Day"] == day and event["Action"] == "consume" for event in read_events(data_dir))


def find_dinner(plan_path: Path, day: str) -> tuple[dict, list[dict], dict]:
    meta, dinners, lunches = parse_plan(plan_path)
    for dinner in dinners:
        if normalize_text(dinner["day"]) == normalize_text(day):
            return meta, lunches, dinner
    available = ", ".join(dinner["day"] for dinner in dinners) or "aucun"
    raise ValueError(f"Repas introuvable pour '{day}'. Jours disponibles: {available}.")


def read_recipes_from(data_dir: Path, category: str | None = None, plan_path: Path | None = None) -> list[dict]:
    recipes: list[dict] = []
    recipe_root = data_dir / "recipes"
    for folder in ("mains", "sides", "lunches"):
        for path in sorted((recipe_root / folder).glob("*.md")):
            meta, body = parse_frontmatter(path)
            if not meta:
                continue
            if category and meta.get("category") != category:
                continue
            recipe = dict(meta)
            recipe["path"] = path
            recipe["ingredients"] = parse_ingredients(body)
            recipes.append(recipe)
    if plan_path:
        pending = data_dir / "drafts" / f"{plan_path.stem}_recipes"
        for path in sorted(pending.glob("*.md")):
            meta, body = parse_frontmatter(path)
            if not meta:
                continue
            if category and meta.get("category") != category:
                continue
            recipe = dict(meta)
            recipe["path"] = path
            recipe["pending_recipe"] = True
            recipe["ingredients"] = parse_ingredients(body)
            recipes.append(recipe)
    return recipes


def side_recipes_for(data_dir: Path, dinner: dict, plan_path: Path) -> list[dict]:
    side_value = dinner.get("side", "")
    if not side_value or normalize_text(side_value) == "aucun":
        return []
    lookup = {normalize_text(recipe["title"]): recipe for recipe in read_recipes_from(data_dir, "side", plan_path)}
    recipes = []
    missing = []
    for part in side_value.split(","):
        title = part.strip()
        if not title or normalize_text(title) == "aucun":
            continue
        recipe = lookup.get(normalize_text(title))
        if recipe:
            recipes.append(recipe)
        else:
            missing.append(title)
    if missing:
        raise ValueError(f"Accompagnement inconnu pour {dinner['day']} ({dinner['title']}): {', '.join(missing)}")
    return recipes


def used_ingredients_for_dinner(data_dir: Path, plan_path: Path, dinner: dict) -> tuple[set[str], dict[str, int]]:
    recipes = {recipe["title"]: recipe for recipe in read_recipes_from(data_dir, "main", plan_path)}
    recipe = recipes.get(dinner["title"])
    if not recipe:
        raise ValueError(f"Recette introuvable pour '{dinner['title']}'.")
    violations = recipe_restriction_violations(recipe)
    if violations:
        raise ValueError(f"Recette interdite '{dinner['title']}': {', '.join(violations)}")

    used_names: set[str] = set()
    used_quantities: dict[str, int] = {}

    def add_used_ingredients(source_recipe: dict) -> None:
        for ingredient in source_recipe["ingredients"]:
            name = canonical_ingredient_name(ingredient["name"])
            quantity = integer_quantity(str(ingredient["quantity"]))
            if quantity is None:
                used_names.add(name)
            else:
                used_quantities[name] = used_quantities.get(name, 0) + ingredient_units(ingredient["name"], quantity)

    add_used_ingredients(recipe)
    for side_recipe in side_recipes_for(data_dir, dinner, plan_path):
        add_used_ingredients(side_recipe)
    return used_names, used_quantities


def deduct_inventory_for_dinner(data_dir: Path, plan_path: Path, dinner: dict) -> list[str]:
    used_names, used_quantities = used_ingredients_for_dinner(data_dir, plan_path, dinner)
    deducted = []
    inventory_dir = data_dir / "inventory"
    for path in sorted(inventory_dir.glob("*.md")):
        if path.name == "consumption_notes.md":
            continue
        original = path.read_text(encoding="utf-8").splitlines()
        updated = []
        changed = False
        for line in original:
            stripped = line.strip()
            if not stripped.startswith("- "):
                updated.append(line)
                continue

            raw_item = stripped[2:].strip()
            name = item_name(raw_item)
            canonical_name = canonical_ingredient_name(name)
            quantity = integer_quantity(item_quantity(raw_item))
            item_unit_size = ingredient_units(name, 1)
            remaining_needed = used_quantities.get(canonical_name, 0)
            if quantity is not None and remaining_needed > 0:
                inventory_units = ingredient_units(name, quantity)
                deducted_units = min(inventory_units, remaining_needed)
                used_quantities[canonical_name] = remaining_needed - deducted_units
                deducted_quantity = (deducted_units + item_unit_size - 1) // item_unit_size
                deducted.append(f"{name} x{deducted_quantity} ({path.stem})")
                changed = True
                remaining_units = inventory_units - deducted_units
                remaining_quantity = remaining_units // item_unit_size
                if remaining_quantity > 0:
                    item_label = raw_item.split("|", 1)[0].strip()
                    updated.append(f"- {item_label} | {remaining_quantity}")
                continue

            if canonical_name in used_names:
                deducted.append(f"{name} ({path.stem})")
                changed = True
                continue
            updated.append(line)
        if changed:
            path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")
    return deducted


def append_consumed_history(data_dir: Path, date: str, meal_family: str) -> bool:
    path = data_dir / "history" / "meals.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("# Meal History\n", encoding="utf-8")
    lines = path.read_text(encoding="utf-8").splitlines()
    header = f"## {date}"
    if header not in lines:
        path.write_text(path.read_text(encoding="utf-8").rstrip() + f"\n\n{header}\n\n- {meal_family}\n", encoding="utf-8")
        return True

    header_index = lines.index(header)
    insert_index = len(lines)
    for index in range(header_index + 1, len(lines)):
        if lines[index].startswith("## "):
            insert_index = index
            break
        if lines[index].strip() == f"- {meal_family}":
            return False
    lines.insert(insert_index, f"- {meal_family}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True


def append_inventory_notes(
    data_dir: Path,
    *,
    date: str,
    week: str,
    dinner: dict,
    deducted: list[str],
) -> Path:
    path = data_dir / "inventory" / "consumption_notes.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8").rstrip() if path.exists() else "# Consumption Notes"
    lines = [
        "",
        f"## {date} - {week} - {dinner['day']}",
        "",
        f"Repas: {dinner['title']} ({dinner['meal_family']})",
        "",
        "Articles deduits automatiquement:",
        "",
    ]
    if deducted:
        lines.extend(f"- {item}" for item in deducted)
    else:
        lines.append("- Aucun article correspondant trouve dans l'inventaire")
    path.write_text(existing + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return path


def handle_action(
    action: str,
    *,
    day: str,
    plan_path: Path,
    date: str,
    note: str = "",
    data_dir: Path = DATA,
) -> tuple[dict, list[str], Path | None]:
    if action not in ACTIONS:
        raise ValueError(f"Action invalide: {action}")
    meta, _, dinner = find_dinner(plan_path, day)
    week = str(meta.get("week", plan_path.stem))

    if action == "consume" and consumed_event_exists(data_dir, week, dinner["day"]):
        raise ValueError(f"{week} {dinner['day']} est deja marque comme consomme; inventaire non modifie.")

    deducted: list[str] = []
    review_path: Path | None = None
    if action == "consume":
        deducted = deduct_inventory_for_dinner(data_dir, plan_path, dinner)
        append_consumed_history(data_dir, date, dinner["meal_family"])
        review_path = append_inventory_notes(data_dir, date=date, week=week, dinner=dinner, deducted=deducted)

    append_event(
        data_dir,
        date=date,
        week=week,
        day=dinner["day"],
        action=action,
        recipe=dinner["title"],
        meal_family=dinner["meal_family"],
        note=note,
    )
    return dinner, deducted, review_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Marquer un souper comme consomme, annule ou reporte")
    parser.add_argument("--plan", type=Path, help="Plan Markdown a utiliser")
    parser.add_argument("--date", help="Date YYYY-MM-DD pour le journal; defaut: aujourd'hui")
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in sorted(ACTIONS):
        subparser = subparsers.add_parser(action)
        subparser.add_argument("--plan", type=Path, default=argparse.SUPPRESS, help="Plan Markdown a utiliser")
        subparser.add_argument("--date", default=argparse.SUPPRESS, help="Date YYYY-MM-DD pour le journal; defaut: aujourd'hui")
        subparser.add_argument("--day", required=True, help='Position du plan, par exemple "Jour 1"')
        subparser.add_argument("--note", default="", help="Note optionnelle pour le journal")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    plan_path = args.plan or latest_plan(DATA)
    if not plan_path:
        print("No plan found. Run scripts/plan_week.py and scripts/commit_plan.py first.")
        return 1
    if not plan_path.exists():
        print(f"Error: plan not found: {plan_path}")
        return 1
    date = args.date or dt.date.today().isoformat()
    try:
        dt.date.fromisoformat(date)
        dinner, deducted, review_path = handle_action(
            args.action,
            day=args.day,
            plan_path=plan_path,
            date=date,
            note=args.note,
            data_dir=DATA,
        )
    except ValueError as error:
        print(f"Error: {error}")
        return 1

    print(f"Meal action: {args.action}")
    print(f"Plan: {plan_path}")
    print(f"Day: {dinner['day']}")
    print(f"Meal: {dinner['title']} ({dinner['meal_family']})")
    if args.action == "consume":
        print(f"Inventory items deducted: {len(deducted)}")
        for item in deducted:
            print(f"- {item}")
        print(f"Inventory review notes: {review_path}")
    else:
        print("Inventory unchanged.")
    print(f"Event log: {DATA / 'history' / 'meal_events.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
