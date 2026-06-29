from __future__ import annotations

import argparse
import datetime as dt
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PLAN_DAYS = ["Jour 1", "Jour 2", "Jour 3", "Jour 4", "Jour 5"]
REQUIRED_RECIPE_FIELDS = [
    "title",
    "portions",
    "meal_family",
    "protein_type",
    "prep_time",
    "cook_time",
    "active_time",
    "equipment_required",
    "preferred_seasons",
    "effort_level",
    "leftover_friendly",
    "freezes_well",
    "suggested_side_dishes",
    "category",
]
MAIN_RECIPE_FIELDS = [
    "contains_vegetable",
    "contains_starch",
    "leftover_lunch_portions",
    "leftover_lunch_style",
    "kids_leftover_ok",
    "adult_leftover_ok",
]
LUNCH_RECIPE_FIELDS = [
    "lunch_temperature",
]
LUNCH_TEMPERATURES = {"cold", "reheatable", "both"}
LEFTOVER_LUNCH_STYLES = {"none", "wrap", "bol froid", "restants rechauffes", "sandwich", "salade froide"}
KIDS_LEFTOVER_STYLES = {"wrap", "bol froid", "sandwich", "salade froide"}
GROCERY_CATEGORIES = [
    "Fruits et legumes",
    "Viandes et poissons",
    "Produits laitiers",
    "Boulangerie",
    "Epicerie seche",
    "Surgeles",
    "Condiments",
    "Autres",
]
PEPPER_COLORS = {"rouge", "jaune", "orange", "vert"}
ACTIVE_RECIPE_DIRS = ["mains", "sides", "lunches"]
MODE_RULE_FIELDS = [
    "requires_lunches",
    "requires_child_lunches",
    "avoid_lunches",
    "max_active_time_bias",
    "prefer_meal_tags",
    "avoid_meal_tags",
    "prefer_equipment",
    "avoid_equipment",
    "leftover_strategy",
    "grocery_bias",
    "notes",
]
AMBIGUOUS_PROTEIN_TYPES = {"seafood"}
CRUSTACEAN_PROTEIN_TYPES = {"crustacean"}
CRUSTACEAN_TERMS = {
    "crevette",
    "crevettes",
    "crabe",
    "crabes",
    "homard",
    "homards",
    "langoustine",
    "langoustines",
    "ecrevisse",
    "ecrevisses",
}


def current_week(today: dt.date | None = None) -> str:
    value = today or dt.date.today()
    iso = value.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def season_for_date(today: dt.date | None = None) -> str:
    month = (today or dt.date.today()).month
    if month in (5, 6, 7, 8):
        return "saison_chaude"
    return "saison_froide"


def parse_scalar(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part.strip()) for part in inner.split(",")]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value.strip('"').strip("'")


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def parse_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    _, rest = text.split("---\n", 1)
    raw, body = rest.split("\n---\n", 1)
    data = {}
    for line in raw.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = parse_scalar(value)
    return data, body


def format_list(values) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(str(value) for value in values) + "]"


def frontmatter(data: dict) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            rendered = format_list(value)
        elif isinstance(value, bool):
            rendered = "true" if value else "false"
        else:
            rendered = str(value)
        lines.append(f"{key}: {rendered}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def read_bullets(path: Path) -> list[str]:
    if not path.exists():
        return []
    values = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            values.append(stripped[2:].strip())
    return values


def item_name(value: str) -> str:
    return value.split("|", 1)[0].strip().lower()


def item_quantity(value: str) -> str:
    parts = [part.strip() for part in value.split("|")]
    return parts[1] if len(parts) > 1 else ""


def integer_quantity(value: str) -> int | None:
    clean = value.strip()
    if re.fullmatch(r"\d+", clean):
        return int(clean)
    return None


def canonical_ingredient_name(value: str) -> str:
    clean = normalize_text(value).strip()
    parts = clean.split()
    if parts and parts[0] in {"poivron", "poivrons"}:
        if len(parts) == 1 or parts[1] in PEPPER_COLORS:
            return "poivron"
    return clean


def read_inventory() -> dict[str, list[str]]:
    inventory = {}
    for path in sorted((DATA / "inventory").glob("*.md")):
        inventory[path.stem] = read_bullets(path)
    return inventory


def inventory_names() -> set[str]:
    names = set()
    for items in read_inventory().values():
        for item in items:
            name = item_name(item)
            names.add(name)
            names.add(canonical_ingredient_name(name))
    return names


def inventory_quantities() -> dict[str, int]:
    quantities: dict[str, int] = {}
    for items in read_inventory().values():
        for item in items:
            quantity = integer_quantity(item_quantity(item))
            if quantity is None:
                continue
            name = canonical_ingredient_name(item_name(item))
            quantities[name] = quantities.get(name, 0) + quantity
    return quantities


def read_modes() -> list[str]:
    path = DATA / "profile" / "modes.md"
    modes = []
    in_active_modes = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# Active Modes"):
            in_active_modes = True
            continue
        if line.startswith("## "):
            in_active_modes = False
        if line.strip().startswith("- "):
            if not in_active_modes:
                continue
            modes.append(line.strip()[2:].strip())
    return modes


def read_mode_definitions() -> dict[str, dict]:
    path = DATA / "profile" / "mode_definitions.md"
    definitions: dict[str, dict] = {}
    if not path.exists():
        return definitions

    current_mode = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            current_mode = stripped[3:].strip()
            definitions[current_mode] = {}
            continue
        if not current_mode or not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        definitions[current_mode][key.strip()] = parse_scalar(value)
    return definitions


def active_mode_rules(active_modes: list[str] | None = None, definitions: dict[str, dict] | None = None) -> dict:
    active_modes = active_modes if active_modes is not None else read_modes()
    definitions = definitions if definitions is not None else read_mode_definitions()
    rules = {
        "requires_lunches": False,
        "requires_child_lunches": False,
        "avoid_lunches": False,
        "max_active_time_bias": 0,
        "prefer_meal_tags": [],
        "avoid_meal_tags": [],
        "prefer_equipment": [],
        "avoid_equipment": [],
        "leftover_strategy": [],
        "grocery_bias": [],
        "notes": [],
    }

    for mode in active_modes:
        definition = definitions.get(mode, {})
        rules["requires_lunches"] = rules["requires_lunches"] or bool(definition.get("requires_lunches", False))
        rules["requires_child_lunches"] = rules["requires_child_lunches"] or bool(
            definition.get("requires_child_lunches", False)
        )
        rules["avoid_lunches"] = rules["avoid_lunches"] or bool(definition.get("avoid_lunches", False))
        rules["max_active_time_bias"] += int(definition.get("max_active_time_bias", 0) or 0)
        for key in ("prefer_meal_tags", "avoid_meal_tags", "prefer_equipment", "avoid_equipment"):
            for value in definition.get(key, []) or []:
                if value not in rules[key]:
                    rules[key].append(value)
        for key in ("leftover_strategy", "grocery_bias", "notes"):
            value = definition.get(key)
            if value and value not in rules[key]:
                rules[key].append(value)

    return rules


def read_equipment() -> set[str]:
    return set(read_bullets(DATA / "profile" / "equipment.md"))


def read_profile_values(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        values[key.strip()] = parse_scalar(value)
    return values


def read_dietary_restrictions() -> dict:
    profile = read_profile_values(DATA / "profile" / "household.md")
    return {
        "forbidden_ingredient_groups": profile.get("forbidden_ingredient_groups", []),
        "forbidden_ingredients": profile.get("forbidden_ingredients", []),
        "allowed_ingredient_groups": profile.get("allowed_ingredient_groups", []),
    }


def read_constraints() -> dict[str, dict]:
    path = DATA / "planning" / "weekly_constraints.md"
    constraints = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "---" in line or "Day" in line or "Jour |" in line or "Slot" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 3:
            max_active_time = int(cells[1]) if cells[1] else 999
            constraints[cells[0]] = {
                "max_active_time": max_active_time,
                "constraint": cells[2],
            }
    return constraints


def read_recent_meal_families(limit_weeks: int = 3) -> set[str]:
    path = DATA / "history" / "meals.md"
    if not path.exists():
        return set()
    sections = []
    current = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if current:
                sections.append(current)
            current = []
            continue
        if line.strip().startswith("- "):
            current.append(line.strip()[2:].strip())
    if current:
        sections.append(current)
    recent = sections[-limit_weeks:]
    return {family for week in recent for family in week}


def recipe_paths() -> list[Path]:
    paths = []
    for folder in ACTIVE_RECIPE_DIRS:
        paths.extend((DATA / "recipes" / folder).glob("*.md"))
    return sorted(paths)


def excluded_recipe_paths() -> list[Path]:
    return sorted((DATA / "recipes" / "excluded").glob("*.md"))


def read_recipes(category: str | None = None) -> list[dict]:
    recipes = []
    for path in recipe_paths():
        meta, body = parse_frontmatter(path)
        if not meta:
            continue
        if category and meta.get("category") != category:
            continue
        recipe = dict(meta)
        recipe["path"] = path
        recipe["ingredients"] = parse_ingredients(body)
        recipes.append(recipe)
    return recipes


def pending_recipe_dir_for_plan(plan_path: Path) -> Path:
    return DATA / "drafts" / f"{plan_path.stem}_recipes"


def read_pending_recipes(plan_path: Path, category: str | None = None) -> list[dict]:
    recipes = []
    folder = pending_recipe_dir_for_plan(plan_path)
    if not folder.exists():
        return recipes
    for path in sorted(folder.glob("*.md")):
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


def crustacean_term_in_text(value: str) -> str | None:
    normalized = normalize_text(value)
    for term in CRUSTACEAN_TERMS:
        if term in normalized:
            return term
    return None


def recipe_restriction_violations(recipe: dict, restrictions: dict | None = None) -> list[str]:
    restrictions = restrictions or read_dietary_restrictions()
    forbidden_groups = set(restrictions.get("forbidden_ingredient_groups", []))
    forbidden_ingredients = {normalize_text(str(value)) for value in restrictions.get("forbidden_ingredients", [])}
    protein_type = normalize_text(str(recipe.get("protein_type", "")))
    violations = []

    if protein_type in AMBIGUOUS_PROTEIN_TYPES:
        violations.append("protein_type seafood is ambiguous; use fish, mussels, or crustacean")

    if "crustaceans" in forbidden_groups and protein_type in CRUSTACEAN_PROTEIN_TYPES:
        violations.append("protein_type crustacean is forbidden")

    if "crustaceans" in forbidden_groups:
        for ingredient in recipe.get("ingredients", []):
            term = crustacean_term_in_text(ingredient.get("name", ""))
            if term:
                violations.append(f"forbidden crustacean ingredient: {ingredient['name']}")

    for ingredient in recipe.get("ingredients", []):
        ingredient_name = normalize_text(ingredient.get("name", ""))
        if ingredient_name in forbidden_ingredients:
            violations.append(f"forbidden ingredient: {ingredient['name']}")

    return violations


def is_recipe_allowed(recipe: dict, restrictions: dict | None = None) -> bool:
    return not recipe_restriction_violations(recipe, restrictions)


def parse_ingredients(body: str) -> list[dict]:
    ingredients = []
    in_section = False
    for line in body.splitlines():
        if line.startswith("## "):
            in_section = line.strip().lower() == "## ingredients"
            continue
        if in_section and line.strip().startswith("- "):
            parts = [part.strip() for part in line.strip()[2:].split("|")]
            ingredients.append(
                {
                    "name": parts[0],
                    "category": parts[1] if len(parts) > 1 else "Autres",
                    "quantity": parts[2] if len(parts) > 2 else "au besoin",
                }
            )
    return ingredients


def read_recurring_groceries() -> list[dict]:
    items = []
    for line in read_bullets(DATA / "planning" / "recurring_groceries.md"):
        parts = [part.strip() for part in line.split("|")]
        items.append(
            {
                "name": parts[0],
                "category": parts[1] if len(parts) > 1 else "Autres",
                "quantity": parts[2] if len(parts) > 2 else "au besoin",
                "recurring": True,
            }
        )
    return items


def latest_file(folder: Path, pattern: str = "*.md") -> Path | None:
    files = sorted(folder.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return files[0] if files else None


def parse_plan(path: Path) -> tuple[dict, list[dict], list[dict]]:
    meta, body = parse_frontmatter(path)
    dinners = []
    lunches = []
    section = None
    for line in body.splitlines():
        if line.startswith("## Soupers"):
            section = "dinners"
            continue
        if line.startswith("## Lunchs"):
            section = "lunches"
            continue
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and cells[0] in {"Day", "Jour", "Slot"}:
            continue
        if section == "dinners" and len(cells) >= 5:
            dinners.append(
                {
                    "day": cells[0],
                    "title": cells[1],
                    "meal_family": cells[2],
                    "side": cells[3],
                    "notes": cells[4],
                }
            )
        if section == "lunches" and len(cells) >= 6:
            lunches.append(
                {
                    "day": cells[0],
                    "kids_lunch": cells[1],
                    "kids_type": cells[2],
                    "adult_lunch": cells[3],
                    "adult_type": cells[4],
                    "source": cells[5],
                }
            )
        elif section == "lunches" and len(cells) >= 4:
            lunches.append(
                {
                    "day": cells[0],
                    "kids_lunch": cells[1],
                    "adult_lunch": cells[2],
                    "source": cells[3],
                }
            )
        elif section == "lunches" and len(cells) >= 3:
            lunches.append({"day": cells[0], "lunch": cells[1], "source": cells[2]})
    return meta, dinners, lunches


def slug(value: str) -> str:
    clean_value = normalize_text(value)
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", clean_value).strip("-")
    return clean or "item"


def parser_with_plan_arg(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--plan", type=Path, help="Plan Markdown a utiliser")
    return parser
