from __future__ import annotations

import sys
from pathlib import Path

from meal_os import (
    DATA,
    KIDS_LEFTOVER_STYLES,
    LUNCH_RECIPE_FIELDS,
    LUNCH_TEMPERATURES,
    LEFTOVER_LUNCH_STYLES,
    MAIN_RECIPE_FIELDS,
    MODE_RULE_FIELDS,
    REQUIRED_RECIPE_FIELDS,
    normalize_text,
    parse_frontmatter,
    parse_ingredients,
    parse_plan,
    read_mode_definitions,
    read_modes,
    recipe_paths,
    recipe_restriction_violations,
    side_titles as parse_side_titles,
)

ALLOWED_MODES = {"ecole", "pas_ecole"}
ALLOWED_SEASONS = {"saison_chaude", "saison_froide"}

REQUIRED_FILES = [
    DATA / "profile" / "household.md",
    DATA / "profile" / "equipment.md",
    DATA / "profile" / "modes.md",
    DATA / "profile" / "mode_definitions.md",
    DATA / "planning" / "weekly_constraints.md",
    DATA / "planning" / "recurring_groceries.md",
    DATA / "history" / "meals.md",
    DATA / "history" / "meal_events.md",
]


def validate_required_files(errors: list[str]) -> None:
    for path in REQUIRED_FILES:
        if not path.exists():
            errors.append(f"Missing required file: {path}")


def validate_recipes(errors: list[str]) -> None:
    paths = recipe_paths()
    if not paths:
        return
    side_recipe_titles = set()
    for path in paths:
        meta, _ = parse_frontmatter(path)
        if meta.get("category") == "side" and meta.get("title"):
            side_recipe_titles.add(normalize_text(str(meta["title"])))

    for path in paths:
        meta, body = parse_frontmatter(path)
        if not meta:
            errors.append(f"{path}: missing frontmatter")
            continue
        for field in REQUIRED_RECIPE_FIELDS:
            if field not in meta or meta[field] in ("", None):
                errors.append(f"{path}: missing required field '{field}'")
        if meta.get("category") not in {"main", "side", "lunch"}:
            errors.append(f"{path}: category must be main, side, or lunch")
        seasons = meta.get("preferred_seasons", [])
        if not isinstance(seasons, list) or not seasons:
            errors.append(f"{path}: preferred_seasons must be a non-empty list")
        else:
            invalid = [season for season in seasons if season not in ALLOWED_SEASONS]
            if invalid:
                errors.append(f"{path}: invalid preferred_seasons: {invalid}")
        if meta.get("category") == "main":
            for field in MAIN_RECIPE_FIELDS:
                if field not in meta:
                    errors.append(f"{path}: missing main recipe field '{field}'")
            for field in ("contains_vegetable", "contains_starch", "kids_leftover_ok", "adult_leftover_ok"):
                if field in meta and not isinstance(meta[field], bool):
                    errors.append(f"{path}: main recipe field '{field}' must be true or false")
            portions = meta.get("leftover_lunch_portions")
            style = meta.get("leftover_lunch_style")
            if not isinstance(portions, int) or portions < 0 or portions > 4:
                errors.append(f"{path}: leftover_lunch_portions must be an integer from 0 to 4")
            if style not in LEFTOVER_LUNCH_STYLES:
                errors.append(f"{path}: leftover_lunch_style must be one of {sorted(LEFTOVER_LUNCH_STYLES)}")
            if meta.get("leftover_friendly") is False:
                if portions != 0:
                    errors.append(f"{path}: leftover_friendly false requires leftover_lunch_portions: 0")
                if style != "none":
                    errors.append(f"{path}: leftover_friendly false requires leftover_lunch_style: none")
                if meta.get("kids_leftover_ok") or meta.get("adult_leftover_ok"):
                    errors.append(f"{path}: leftover_friendly false requires kids/adult leftover flags to be false")
            if meta.get("leftover_friendly") is True:
                if not isinstance(portions, int) or portions < 1:
                    errors.append(f"{path}: leftover_friendly true requires at least 1 leftover lunch portion")
                if style == "none":
                    errors.append(f"{path}: leftover_friendly true requires a leftover style other than none")
                if not meta.get("kids_leftover_ok") and not meta.get("adult_leftover_ok"):
                    errors.append(f"{path}: leftover_friendly true requires kids or adults to be leftover-compatible")
            if meta.get("kids_leftover_ok") and style not in KIDS_LEFTOVER_STYLES:
                errors.append(f"{path}: kids leftover style must be cold or portable")
            for side_title in meta.get("suggested_side_dishes", []) or []:
                if normalize_text(str(side_title)) not in side_recipe_titles:
                    errors.append(f"{path}: unknown suggested side dish '{side_title}'")
        if meta.get("category") == "lunch":
            for field in LUNCH_RECIPE_FIELDS:
                if field not in meta or meta[field] not in LUNCH_TEMPERATURES:
                    errors.append(
                        f"{path}: lunch recipe field '{field}' must be one of {sorted(LUNCH_TEMPERATURES)}"
                    )
            if meta.get("for_children", False) and meta.get("lunch_temperature") != "cold":
                errors.append(f"{path}: child lunch recipes must be cold")
        if "mode_tags" in meta and not isinstance(meta["mode_tags"], list):
            errors.append(f"{path}: mode_tags must be a list")
        recipe = dict(meta)
        recipe["ingredients"] = parse_ingredients(body)
        for violation in recipe_restriction_violations(recipe):
            errors.append(f"{path}: dietary restriction violation: {violation}")


def validate_modes(errors: list[str]) -> None:
    definitions = read_mode_definitions()
    active_modes = read_modes()
    for mode in active_modes:
        if mode not in ALLOWED_MODES:
            errors.append(f"Active mode '{mode}' must be ecole or pas_ecole")
        if mode not in definitions:
            errors.append(f"Active mode '{mode}' is missing from data/profile/mode_definitions.md")
    for mode, definition in definitions.items():
        if mode not in ALLOWED_MODES:
            errors.append(f"Mode '{mode}' is obsolete; only ecole and pas_ecole are supported")
        for field in MODE_RULE_FIELDS:
            if field not in definition:
                errors.append(f"Mode '{mode}' is missing field '{field}'")
        for field in ("prefer_meal_tags", "avoid_meal_tags", "prefer_equipment", "avoid_equipment"):
            if field in definition and not isinstance(definition[field], list):
                errors.append(f"Mode '{mode}' field '{field}' must be a list")
        if "requires_child_lunches" in definition and not isinstance(definition["requires_child_lunches"], bool):
            errors.append(f"Mode '{mode}' field 'requires_child_lunches' must be true or false")


def validate_plans(errors: list[str]) -> None:
    side_recipe_titles = set()
    for path in recipe_paths():
        meta, _ = parse_frontmatter(path)
        if meta.get("category") == "side" and meta.get("title"):
            side_recipe_titles.add(normalize_text(str(meta["title"])))

    for folder in (DATA / "drafts", DATA / "plans"):
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.md")):
            _, dinners, _ = parse_plan(path)
            for dinner in dinners:
                for side_title in parse_side_titles(dinner.get("side")):
                    if normalize_text(side_title) not in side_recipe_titles:
                        errors.append(
                            f"{path}: unknown side dish '{side_title}' in {dinner.get('day')} ({dinner.get('title')})"
                        )


def main() -> int:
    errors: list[str] = []
    validate_required_files(errors)
    validate_modes(errors)
    validate_recipes(errors)
    validate_plans(errors)
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Validation OK")
    print(f"Recipes checked: {len(recipe_paths())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
