from __future__ import annotations

import re
import sys

from meal_os import (
    DATA,
    canonical_ingredient_name,
    inventory_names,
    latest_file,
    parser_with_plan_arg,
    parse_plan,
    read_pending_recipes,
    read_recipes,
    season_for_date,
    side_recipes_for_dinner,
)


def clamp(value: int) -> int:
    return max(0, min(100, value))


def score_plan(path):
    meta, dinners, lunches = parse_plan(path)
    recipes = {recipe["title"]: recipe for recipe in read_recipes("main")}
    recipes.update({recipe["title"]: recipe for recipe in read_pending_recipes(path, "main")})
    owned = inventory_names()
    ingredient_count = 0
    inventory_hits = 0
    ingredient_usage = {}
    season = meta.get("season") or season_for_date()

    def score_ingredients(recipe: dict, include_season: bool = False) -> None:
        nonlocal ingredient_count, inventory_hits
        if include_season and season in recipe.get("preferred_seasons", []):
            ingredient_usage.setdefault("_season_hits", 0)
            ingredient_usage["_season_hits"] += 1
        for ingredient in recipe["ingredients"]:
            ingredient_count += 1
            name = ingredient["name"].lower()
            ingredient_usage[name] = ingredient_usage.get(name, 0) + 1
            if canonical_ingredient_name(name) in owned:
                inventory_hits += 1

    for dinner in dinners:
        recipe = recipes.get(dinner["title"])
        if not recipe:
            continue
        score_ingredients(recipe, include_season=True)
        for side_recipe in side_recipes_for_dinner(dinner, path):
            score_ingredients(side_recipe)

    repeated_ingredients = sum(1 for name, count in ingredient_usage.items() if not name.startswith("_") and count > 1)
    season_hits = ingredient_usage.get("_season_hits", 0)
    leftover_capacity = sum(
        int(recipes.get(dinner["title"], {}).get("leftover_lunch_portions", 0) or 0)
        for dinner in dinners
    )
    leftover_used = 0
    for lunch in lunches:
        source = lunch.get("source", "")
        used_match = re.search(r"restants utilises: (\d+)", source)
        legacy_match = re.search(r"restants: (\d+)/(\d+) portions", source)
        if used_match:
            leftover_used += int(used_match.group(1))
        elif legacy_match:
            leftover_used += int(legacy_match.group(1))
    quick_matches = sum(1 for dinner in dinners if "OK" in dinner.get("notes", ""))

    scores = {
        "inventory_usage_score": clamp(round((inventory_hits / max(ingredient_count, 1)) * 100)),
        "ingredient_reuse_score": clamp(40 + repeated_ingredients * 15),
        "waste_reduction_score": clamp(45 + inventory_hits * 7 + repeated_ingredients * 5),
        "season_match_score": clamp(round((season_hits / max(len(dinners), 1)) * 100)),
        "schedule_match_score": clamp(round((quick_matches / max(len(dinners), 1)) * 100)),
        "leftover_usage_score": clamp(round((leftover_used / max(leftover_capacity, 1)) * 100)),
    }
    scores["overall_score"] = round(sum(scores.values()) / len(scores))
    return scores


def main() -> int:
    parser = parser_with_plan_arg("Score a meal plan")
    args = parser.parse_args()
    plan_path = args.plan or latest_file(DATA / "plans")
    if not plan_path:
        print("No plan found. Run scripts/plan_week.py first.")
        return 1
    try:
        scores = score_plan(plan_path)
    except ValueError as error:
        print(error)
        return 1
    for key, value in scores.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
