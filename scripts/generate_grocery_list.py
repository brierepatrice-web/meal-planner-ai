from __future__ import annotations

import sys
from pathlib import Path

from meal_os import (
    DATA,
    GROCERY_CATEGORIES,
    canonical_ingredient_name,
    ingredient_units,
    integer_quantity,
    inventory_names,
    inventory_quantities,
    latest_file,
    parser_with_plan_arg,
    parse_plan,
    purchase_quantity_for_units,
    read_pending_recipes,
    read_recipes,
    read_recurring_groceries,
    recipe_restriction_violations,
    side_recipes_for_dinner,
)

RECIPE_GROCERY_EXCLUDED_INGREDIENTS = {"lait"}


def add_ingredient_to_categories(
    ingredient: dict,
    categories: dict[str, list[str]],
    skipped: list[str],
    owned: set[str],
    available_quantities: dict[str, int],
    quantified_inventory: set[str],
) -> None:
    name = ingredient["name"].lower()
    canonical_name = canonical_ingredient_name(name)
    if canonical_name in RECIPE_GROCERY_EXCLUDED_INGREDIENTS:
        return
    needed_quantity = integer_quantity(str(ingredient["quantity"]))
    available_quantity = available_quantities.get(canonical_name, 0)
    if needed_quantity is not None and available_quantity > 0:
        needed_units = ingredient_units(name, needed_quantity)
        used_units = min(needed_units, available_quantity)
        available_quantities[canonical_name] = available_quantity - used_units
        if used_units == needed_units:
            skipped.append(ingredient["name"])
            return
        ingredient = dict(ingredient)
        ingredient["quantity"] = str(purchase_quantity_for_units(name, needed_units - used_units))
    elif canonical_name in owned and (needed_quantity is None or canonical_name not in quantified_inventory):
        skipped.append(ingredient["name"])
        return
    category = ingredient["category"]
    if category not in categories:
        category = "Autres"
    rendered = f"- {ingredient['name']} ({ingredient['quantity']})"
    if rendered not in categories[category]:
        categories[category].append(rendered)


def grocery_items_for_plan(plan_path: Path) -> tuple[dict[str, list[str]], list[str]]:
    _, dinners, _ = parse_plan(plan_path)
    recipes = {recipe["title"]: recipe for recipe in read_recipes("main")}
    recipes.update({recipe["title"]: recipe for recipe in read_pending_recipes(plan_path, "main")})
    owned = inventory_names()
    available_quantities = inventory_quantities()
    quantified_inventory = set(available_quantities)
    categories = {category: [] for category in GROCERY_CATEGORIES}
    skipped = []

    for dinner in dinners:
        recipe = recipes.get(dinner["title"])
        if not recipe:
            continue
        violations = recipe_restriction_violations(recipe)
        if violations:
            raise ValueError(f"Plan contains forbidden recipe '{dinner['title']}': {', '.join(violations)}")
        for ingredient in recipe["ingredients"]:
            add_ingredient_to_categories(
                ingredient,
                categories,
                skipped,
                owned,
                available_quantities,
                quantified_inventory,
            )
        for side_recipe in side_recipes_for_dinner(dinner, plan_path):
            for ingredient in side_recipe["ingredients"]:
                add_ingredient_to_categories(
                    ingredient,
                    categories,
                    skipped,
                    owned,
                    available_quantities,
                    quantified_inventory,
                )

    for item in read_recurring_groceries():
        category = item["category"] if item["category"] in categories else "Autres"
        rendered = f"- {item['name']} ({item['quantity']}) [recurrent]"
        if rendered not in categories[category]:
            categories[category].append(rendered)

    return categories, sorted(set(skipped))


def write_grocery_list(plan_path: Path) -> Path:
    meta, _, _ = parse_plan(plan_path)
    week = meta.get("week", plan_path.stem)
    categories, skipped = grocery_items_for_plan(plan_path)
    out = DATA / "grocery_lists" / f"{week}.md"
    lines = [f"# Liste d'epicerie - {week}", "", f"Source plan: {plan_path.name}", ""]
    if skipped:
        lines.append("## Deja dans l'inventaire")
        lines.append("")
        for item in skipped:
            lines.append(f"- {item}")
        lines.append("")
    for category in GROCERY_CATEGORIES:
        lines.append(f"## {category}")
        lines.append("")
        entries = categories[category]
        if entries:
            lines.extend(entries)
        else:
            lines.append("- Aucun achat")
        lines.append("")
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = parser_with_plan_arg("Generate grocery list from a meal plan")
    args = parser.parse_args()
    plan_path = args.plan or latest_file(DATA / "plans")
    if not plan_path:
        print("No plan found. Run scripts/plan_week.py first.")
        return 1
    try:
        out = write_grocery_list(plan_path)
    except ValueError as error:
        print(error)
        return 1
    print(f"Grocery list written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
