from __future__ import annotations

import sys

from meal_os import (
    DATA,
    canonical_ingredient_name,
    integer_quantity,
    item_name,
    item_quantity,
    latest_file,
    parser_with_plan_arg,
    parse_plan,
    read_recipes,
    recipe_restriction_violations,
)


def append_history(plan_path):
    meta, dinners, _ = parse_plan(plan_path)
    week = meta.get("week", plan_path.stem)
    history = DATA / "history" / "meals.md"
    text = history.read_text(encoding="utf-8")
    header = f"## {week}"
    if header in text:
        print(f"History already contains {week}; no duplicate entry added.")
        return False
    lines = ["", header, ""]
    for dinner in dinners:
        lines.append(f"- {dinner['meal_family']}")
    history.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return True


def mark_inventory_review(plan_path, deducted):
    meta, dinners, _ = parse_plan(plan_path)
    week = meta.get("week", plan_path.stem)
    review = DATA / "inventory" / "consumption_notes.md"
    lines = [f"# Consumption Notes - {week}", ""]
    lines.append("Articles deduits automatiquement:")
    lines.append("")
    if deducted:
        for item in deducted:
            lines.append(f"- {item}")
    else:
        lines.append("- Aucun article correspondant trouve dans l'inventaire")
    lines.append("")
    lines.append("Inventaire a reviser apres consommation:")
    lines.append("")
    for dinner in dinners:
        lines.append(f"- {dinner['title']} ({dinner['meal_family']})")
    review.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return review


def deduct_inventory(plan_path):
    _, dinners, _ = parse_plan(plan_path)
    recipes = {recipe["title"]: recipe for recipe in read_recipes("main")}
    used_names = set()
    used_quantities = {}
    for dinner in dinners:
        recipe = recipes.get(dinner["title"])
        if not recipe:
            continue
        violations = recipe_restriction_violations(recipe)
        if violations:
            raise ValueError(f"Plan contains forbidden recipe '{dinner['title']}': {', '.join(violations)}")
        for ingredient in recipe["ingredients"]:
            name = canonical_ingredient_name(ingredient["name"])
            quantity = integer_quantity(str(ingredient["quantity"]))
            if quantity is None:
                used_names.add(name)
            else:
                used_quantities[name] = used_quantities.get(name, 0) + quantity

    deducted = []
    for path in sorted((DATA / "inventory").glob("*.md")):
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
            remaining_needed = used_quantities.get(canonical_name, 0)
            if quantity is not None and remaining_needed > 0:
                deducted_quantity = min(quantity, remaining_needed)
                used_quantities[canonical_name] = remaining_needed - deducted_quantity
                deducted.append(f"{name} x{deducted_quantity} ({path.stem})")
                changed = True
                remaining_quantity = quantity - deducted_quantity
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


def main() -> int:
    parser = parser_with_plan_arg("Mark a plan as consumed")
    args = parser.parse_args()
    plan_path = args.plan or latest_file(DATA / "plans")
    if not plan_path:
        print("No plan found. Run scripts/plan_week.py first.")
        return 1
    appended = append_history(plan_path)
    deducted = deduct_inventory(plan_path)
    review = mark_inventory_review(plan_path, deducted)
    print(f"Consumed plan: {plan_path}")
    print(f"History updated: {appended}")
    print(f"Inventory items deducted: {len(deducted)}")
    for item in deducted:
        print(f"- {item}")
    print(f"Inventory review notes: {review}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
