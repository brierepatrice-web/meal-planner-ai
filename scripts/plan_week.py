from __future__ import annotations

import argparse
import datetime as dt
import sys

from meal_os import (
    DATA,
    KIDS_LEFTOVER_STYLES,
    PLAN_DAYS,
    active_mode_rules,
    current_week,
    excluded_recipe_paths,
    frontmatter,
    is_recipe_allowed,
    parse_frontmatter,
    read_constraints,
    read_dietary_restrictions,
    read_equipment,
    read_modes,
    read_recent_meal_families,
    read_recipes,
    season_for_date,
    slug,
)
from score_plan import score_plan


MAX_LUNCH_TYPE_PER_WEEK = 2
KIDS_FALLBACK_LUNCHES = [
    ("Sandwich froid jambon-fromage, fruit et yogourt", "sandwich"),
    ("Boite bento fromage, craquelins, crudites et fruit", "bento"),
    ("Salade de pates froide avec poulet et legumes", "salade froide"),
    ("Yogourt grec, muffin maison, fromage et fruit", "autonome"),
]
ADULT_FALLBACK_LUNCHES = [
    ("Bol froid poulet, riz et crudites", "bol froid", "autonome"),
    ("Salade repas poulet, riz et legumes", "salade froide", "autonome"),
    ("Sandwich froid, fruit et yogourt", "sandwich", "autonome"),
    ("Boite bento fromage, noix, crudites et fruit", "bento", "autonome"),
]
LEFTOVER_LUNCH_LABELS = {
    "wrap": "Wrap froid de restants",
    "bol froid": "Bol froid de restants",
    "restants rechauffes": "Restants rechauffes",
    "sandwich": "Sandwich froid de restants",
    "salade froide": "Salade froide de restants",
}
WARM_SEASON_TAGS = {"bbq", "grill", "griddle", "light", "taco", "burger", "salad", "quick"}
WARM_SEASON_EQUIPMENT = {"BBQ", "BBQ au propane", "Plaque au propane", "Griddle propane"}
WARM_SEASON_AVOID_TAGS = {"heavy_soup", "heavy_stew", "roast", "braise", "raclette", "fondue", "long_cook"}
GENERATED_MAIN_RECIPES = [
    {
        "title": "Bols de poulet citron et riz",
        "meal_family": "bol poulet riz",
        "protein_type": "chicken",
        "prep_time": 15,
        "cook_time": 25,
        "active_time": 20,
        "preferred_seasons": ["saison_chaude", "saison_froide"],
        "effort_level": "low",
        "leftover_friendly": True,
        "leftover_lunch_portions": 4,
        "leftover_lunch_style": "bol froid",
        "kids_leftover_ok": True,
        "adult_leftover_ok": True,
        "freezes_well": False,
        "suggested_side_dishes": ["Concombres et tomates"],
        "contains_vegetable": True,
        "contains_starch": True,
        "mode_tags": ["quick", "leftover_friendly", "lunch_friendly", "batch_cooking"],
        "ingredients": [
            ("poitrines de poulet", "Viandes et poissons", "700 g"),
            ("riz basmati", "Epicerie seche", "2 tasses"),
            ("concombres", "Fruits et legumes", "2"),
            ("tomates cerises", "Fruits et legumes", "1 chopine"),
            ("citron", "Fruits et legumes", "1"),
            ("yogourt grec", "Produits laitiers", "1 tasse"),
        ],
    },
    {
        "title": "Tacos de boeuf et haricots",
        "meal_family": "tacos",
        "protein_type": "beef",
        "prep_time": 15,
        "cook_time": 15,
        "active_time": 25,
        "preferred_seasons": ["saison_chaude"],
        "effort_level": "low",
        "leftover_friendly": True,
        "leftover_lunch_portions": 4,
        "leftover_lunch_style": "wrap",
        "kids_leftover_ok": True,
        "adult_leftover_ok": True,
        "freezes_well": False,
        "suggested_side_dishes": ["Crudites"],
        "contains_vegetable": True,
        "contains_starch": True,
        "mode_tags": ["quick", "taco", "portable", "leftover_friendly"],
        "ingredients": [
            ("boeuf hache", "Viandes et poissons", "600 g"),
            ("epices a tacos", "Epicerie seche", "1 sachet"),
            ("tortillas", "Boulangerie", "10"),
            ("haricots noirs", "Epicerie seche", "1 conserve"),
            ("laitue", "Fruits et legumes", "1"),
            ("salsa", "Condiments", "1 pot"),
            ("fromage rape", "Produits laitiers", "2 tasses"),
        ],
    },
    {
        "title": "Saumon laque et riz",
        "meal_family": "saumon riz",
        "protein_type": "fish",
        "prep_time": 10,
        "cook_time": 20,
        "active_time": 20,
        "preferred_seasons": ["saison_chaude", "saison_froide"],
        "effort_level": "low",
        "leftover_friendly": False,
        "leftover_lunch_portions": 0,
        "leftover_lunch_style": "none",
        "kids_leftover_ok": False,
        "adult_leftover_ok": False,
        "freezes_well": False,
        "suggested_side_dishes": ["Brocoli vapeur"],
        "contains_vegetable": False,
        "contains_starch": True,
        "mode_tags": ["quick", "light"],
        "ingredients": [
            ("filets de saumon", "Viandes et poissons", "4"),
            ("riz basmati", "Epicerie seche", "1 1/2 tasse"),
            ("sauce soya", "Condiments", "1/4 tasse"),
            ("sirop d'erable", "Condiments", "2 c. a soupe"),
            ("citron", "Fruits et legumes", "1"),
        ],
    },
    {
        "title": "Pates saucisses et legumes rotis",
        "meal_family": "pates saucisses",
        "protein_type": "pork",
        "prep_time": 15,
        "cook_time": 25,
        "active_time": 25,
        "preferred_seasons": ["saison_froide"],
        "effort_level": "medium",
        "leftover_friendly": True,
        "leftover_lunch_portions": 4,
        "leftover_lunch_style": "restants rechauffes",
        "kids_leftover_ok": False,
        "adult_leftover_ok": True,
        "freezes_well": False,
        "suggested_side_dishes": [],
        "contains_vegetable": True,
        "contains_starch": True,
        "mode_tags": ["leftover_friendly", "batch_cooking"],
        "ingredients": [
            ("saucisses italiennes", "Viandes et poissons", "5"),
            ("pates courtes", "Epicerie seche", "450 g"),
            ("poivrons", "Fruits et legumes", "3"),
            ("courgettes", "Fruits et legumes", "2"),
            ("sauce tomate", "Epicerie seche", "1 pot"),
            ("parmesan", "Produits laitiers", "1/2 tasse"),
        ],
    },
    {
        "title": "Burgers de dinde",
        "meal_family": "burger",
        "protein_type": "turkey",
        "prep_time": 15,
        "cook_time": 15,
        "active_time": 25,
        "preferred_seasons": ["saison_chaude"],
        "effort_level": "low",
        "leftover_friendly": False,
        "leftover_lunch_portions": 0,
        "leftover_lunch_style": "none",
        "kids_leftover_ok": False,
        "adult_leftover_ok": False,
        "freezes_well": True,
        "suggested_side_dishes": [],
        "contains_vegetable": False,
        "contains_starch": True,
        "mode_tags": ["burger", "bbq", "quick"],
        "ingredients": [
            ("dinde hachee", "Viandes et poissons", "600 g"),
            ("pains burger", "Boulangerie", "4"),
            ("laitue", "Fruits et legumes", "1"),
            ("tomates", "Fruits et legumes", "2"),
            ("fromage cheddar", "Produits laitiers", "4 tranches"),
        ],
    },
    {
        "title": "Chili doux au boeuf",
        "meal_family": "chili",
        "protein_type": "beef",
        "prep_time": 15,
        "cook_time": 40,
        "active_time": 20,
        "preferred_seasons": ["saison_froide"],
        "effort_level": "low",
        "leftover_friendly": True,
        "leftover_lunch_portions": 4,
        "leftover_lunch_style": "restants rechauffes",
        "kids_leftover_ok": False,
        "adult_leftover_ok": True,
        "freezes_well": True,
        "suggested_side_dishes": ["Riz ou pain de mais"],
        "contains_vegetable": True,
        "contains_starch": False,
        "mode_tags": ["leftover_friendly", "batch_cooking", "comfort"],
        "ingredients": [
            ("boeuf hache", "Viandes et poissons", "600 g"),
            ("haricots rouges", "Epicerie seche", "1 conserve"),
            ("tomates en des", "Epicerie seche", "1 conserve"),
            ("mais", "Surgeles", "1 tasse"),
            ("poivron", "Fruits et legumes", "1"),
            ("epices chili", "Epicerie seche", "2 c. a soupe"),
        ],
    },
    {
        "title": "Poulet BBQ, pommes de terre et salade",
        "meal_family": "poulet bbq",
        "protein_type": "chicken",
        "prep_time": 15,
        "cook_time": 30,
        "active_time": 20,
        "preferred_seasons": ["saison_chaude"],
        "effort_level": "low",
        "leftover_friendly": True,
        "leftover_lunch_portions": 4,
        "leftover_lunch_style": "bol froid",
        "kids_leftover_ok": True,
        "adult_leftover_ok": True,
        "freezes_well": False,
        "suggested_side_dishes": [],
        "contains_vegetable": True,
        "contains_starch": True,
        "mode_tags": ["bbq", "grill", "leftover_friendly"],
        "ingredients": [
            ("hauts de cuisse de poulet", "Viandes et poissons", "8"),
            ("sauce BBQ", "Condiments", "1/2 tasse"),
            ("pommes de terre", "Fruits et legumes", "800 g"),
            ("melange salade", "Fruits et legumes", "1 sac"),
            ("vinaigrette", "Condiments", "1/4 tasse"),
        ],
    },
    {
        "title": "Frittata jambon fromage",
        "meal_family": "frittata",
        "protein_type": "egg",
        "prep_time": 10,
        "cook_time": 20,
        "active_time": 15,
        "preferred_seasons": ["saison_chaude", "saison_froide"],
        "effort_level": "low",
        "leftover_friendly": True,
        "leftover_lunch_portions": 2,
        "leftover_lunch_style": "sandwich",
        "kids_leftover_ok": True,
        "adult_leftover_ok": False,
        "freezes_well": False,
        "suggested_side_dishes": [],
        "contains_vegetable": False,
        "contains_starch": False,
        "mode_tags": ["quick", "leftover_friendly", "make_ahead"],
        "ingredients": [
            ("oeufs", "Produits laitiers", "10"),
            ("jambon", "Viandes et poissons", "250 g"),
            ("fromage suisse", "Produits laitiers", "1 tasse"),
            ("lait", "Produits laitiers", "1/2 tasse"),
        ],
    },
]


def recipe_sort_key(recipe, season, owned_names, mode_rules):
    season_bonus = 20 if season in recipe.get("preferred_seasons", []) else 0
    inventory_bonus = sum(1 for ingredient in recipe["ingredients"] if ingredient["name"].lower() in owned_names)
    leftover_bonus = 5 if recipe.get("leftover_friendly") else 0
    effort_bonus = 4 if recipe.get("effort_level") == "low" else 0
    mode_tags = set(recipe.get("mode_tags", []) or [])
    preferred_tags = set(mode_rules.get("prefer_meal_tags", []) or [])
    avoided_tags = set(mode_rules.get("avoid_meal_tags", []) or [])
    preferred_equipment = set(mode_rules.get("prefer_equipment", []) or [])
    required_equipment = set(recipe.get("equipment_required", []) or [])
    mode_bonus = len(mode_tags & preferred_tags) * 8
    equipment_bonus = len(required_equipment & preferred_equipment) * 4
    avoid_penalty = len(mode_tags & avoided_tags) * 12
    warm_bonus = 0
    warm_penalty = 0
    if season == "saison_chaude":
        warm_bonus = len(mode_tags & WARM_SEASON_TAGS) * 5
        warm_bonus += len(required_equipment & WARM_SEASON_EQUIPMENT) * 5
        warm_penalty = len(mode_tags & WARM_SEASON_AVOID_TAGS) * 15
    return (
        season_bonus
        + inventory_bonus
        + leftover_bonus
        + effort_bonus
        + mode_bonus
        + equipment_bonus
        + warm_bonus
        - avoid_penalty
        - warm_penalty
    )


def choose_recipes(season: str, mode_rules: dict | None = None) -> list[dict]:
    from meal_os import inventory_names

    mode_rules = mode_rules or active_mode_rules()
    equipment = read_equipment()
    restrictions = read_dietary_restrictions()
    recent_families = read_recent_meal_families()
    owned = inventory_names()
    avoided_equipment = set(mode_rules.get("avoid_equipment", []) or [])
    avoided_tags = set(mode_rules.get("avoid_meal_tags", []) or [])
    recipes = []
    for recipe in read_recipes("main"):
        if not is_recipe_allowed(recipe, restrictions):
            continue
        required = set(recipe.get("equipment_required", []))
        if not required.issubset(equipment):
            continue
        if required & avoided_equipment:
            continue
        if set(recipe.get("mode_tags", []) or []) & avoided_tags:
            continue
        if recipe.get("meal_family") in recent_families:
            continue
        recipes.append(recipe)
    recipes.sort(key=lambda recipe: recipe_sort_key(recipe, season, owned, mode_rules), reverse=True)
    return recipes


def recipe_from_template(template: dict) -> dict:
    recipe = {key: value for key, value in template.items() if key != "ingredients"}
    recipe.update(
        {
            "portions": 4,
            "equipment_required": [],
            "category": "main",
            "generated": True,
        }
    )
    recipe["ingredients"] = [
        {"name": name, "category": category, "quantity": quantity}
        for name, category, quantity in template["ingredients"]
    ]
    return recipe


def method_steps_for(recipe: dict) -> list[str]:
    family = str(recipe.get("meal_family", "")).lower()
    title = str(recipe.get("title", "ce repas")).lower()
    protein = str(recipe.get("protein_type", "")).lower()
    tags = set(recipe.get("mode_tags", []) or [])

    if "pates" in family or "pates" in title:
        return [
            "Porter une grande casserole d'eau salee a ebullition. Cuire les pates jusqu'a ce qu'elles soient al dente et reserver un peu d'eau de cuisson avant d'egoutter.",
            "Pendant la cuisson des pates, couper les legumes et preparer la proteine pour que tout soit pret avant l'assemblage.",
            "Cuire la proteine dans une grande poele jusqu'a ce qu'elle soit bien doree, puis ajouter les legumes et cuire jusqu'a ce qu'ils soient tendres.",
            "Ajouter la sauce ou les ingredients cremes/tomates dans la poele. Detendre avec un peu d'eau de cuisson des pates au besoin.",
            "Ajouter les pates, bien melanger et ajuster l'assaisonnement. Finir avec le fromage ou les garnitures prevues.",
            "Pour les restants, refroidir rapidement en portions. Rechauffer avec une petite touche d'eau, de lait ou de sauce pour ramener la texture.",
        ]
    if "taco" in family or "taco" in tags:
        return [
            "Preparer les garnitures avant de cuire la viande: couper les legumes, ouvrir les conserves et sortir les sauces.",
            "Cuire la proteine dans une grande poele a feu moyen-vif en la defaisant ou en la retournant jusqu'a ce qu'elle soit bien cuite.",
            "Ajouter les epices et un petit fond d'eau ou de sauce. Laisser mijoter quelques minutes pour bien enrober la garniture.",
            "Rechauffer les tortillas juste avant de servir pour les rendre souples.",
            "Servir en mode assemblage avec les garnitures, la salsa et le fromage.",
            "Garder la garniture principale a part pour les lunchs; elle se transforme facilement en wraps froids ou bols.",
        ]
    if "bol" in family:
        return [
            "Lancer le riz ou la base de cereales en premier. Pendant la cuisson, couper les legumes et preparer la sauce.",
            "Couper la proteine en morceaux reguliers, puis l'assaisonner simplement avec sel, poivre et les aromates prevus.",
            "Cuire la proteine dans une poele chaude jusqu'a ce qu'elle soit doree et bien cuite.",
            "Repartir la base dans les bols, ajouter la proteine, les legumes et la sauce.",
            "Gouter un bol avant de servir et ajuster avec citron, sel, sauce ou herbes selon le besoin.",
            "Pour les lunchs, refroidir les elements avant d'assembler et garder la sauce a part.",
        ]
    if "bbq" in family or "bbq" in tags or "grill" in tags:
        return [
            "Preparer les accompagnements en premier, surtout les pommes de terre ou legumes qui prennent plus longtemps.",
            "Assaisonner la proteine et garder une partie de la sauce propre pour la fin de cuisson.",
            "Cuire sur le BBQ, au four ou a la poele en retournant a mi-cuisson, jusqu'a ce que la proteine soit bien cuite.",
            "Ajouter la derniere couche de sauce dans les dernieres minutes pour eviter qu'elle brule.",
            "Laisser reposer la proteine quelques minutes pendant que la salade ou les crudites sont assemblees.",
            "Pour les lunchs, reserver la proteine refroidie et garder les elements frais separes.",
        ]
    if "frittata" in family or protein == "egg":
        return [
            "Prechauffer le four a 375 F et graisser un plat allant au four ou une poele allant au four.",
            "Preparer les garnitures: couper la viande ou les legumes et mesurer le fromage.",
            "Fouetter les oeufs avec le lait, une pincee de sel et du poivre jusqu'a ce que le melange soit uniforme.",
            "Repartir les garnitures dans le plat, puis verser les oeufs par-dessus.",
            "Cuire jusqu'a ce que le centre soit pris et que les bords commencent a dorer, puis laisser reposer 5 minutes.",
            "Pour les lunchs, refroidir completement avant de couper en portions ou de mettre en sandwich.",
        ]
    if "chili" in family or "comfort" in tags:
        return [
            "Couper les legumes et ouvrir les conserves avant de commencer la cuisson.",
            "Dans une grande casserole, faire brunir la viande ou la proteine principale a feu moyen-vif.",
            "Ajouter les legumes et les epices. Cuire quelques minutes pour developper le gout.",
            "Ajouter les tomates, haricots, bouillon ou autres liquides prevus, puis porter a faible ebullition.",
            "Laisser mijoter jusqu'a ce que le plat epaississe et que les saveurs soient bien combinees.",
            "Servir avec l'accompagnement prevu. Portionner les restants; ce type de repas se rechauffe tres bien.",
        ]
    if protein == "fish":
        return [
            "Lancer le riz, les pommes de terre ou l'accompagnement principal avant le poisson.",
            "Preparer la sauce ou la laque, puis eponger le poisson pour qu'il cuise mieux.",
            "Deposer le poisson sur une plaque ou dans une poele, puis badigeonner avec la sauce.",
            "Cuire jusqu'a ce que le poisson se defasse facilement a la fourchette, en evitant de trop le cuire.",
            "Pendant la cuisson, preparer le legume rapide ou la salade.",
            "Servir le poisson le soir meme; eviter de compter sur des restants de lunch si la recette n'est pas prevue pour ca.",
        ]
    return [
        "Lire la recette au complet, sortir les ingredients et preparer les accompagnements qui prennent le plus de temps.",
        "Couper les legumes, mesurer les sauces et assaisonner la proteine avant de commencer la cuisson.",
        "Cuire la proteine ou l'element principal jusqu'a ce qu'il soit bien cuit et dore.",
        "Ajouter les legumes, sauces ou feculents selon la recette, puis laisser cuire jusqu'a la bonne texture.",
        "Assembler le repas, gouter et ajuster l'assaisonnement avant de servir.",
        "S'il y a des restants, refroidir rapidement et portionner selon les lunchs prevus.",
    ]


def render_recipe(recipe: dict) -> str:
    meta = {key: value for key, value in recipe.items() if key not in {"ingredients", "path", "pending_recipe"}}
    lines = [frontmatter(meta).rstrip(), "", f"# {recipe['title']}", ""]
    lines.extend(["## Ingredients", ""])
    for ingredient in recipe["ingredients"]:
        lines.append(f"- {ingredient['name']} | {ingredient['category']} | {ingredient['quantity']}")
    lines.extend(["", "## Methode", ""])
    for index, step in enumerate(method_steps_for(recipe), start=1):
        lines.append(f"- {index}. {step}")
    return "\n".join(lines).rstrip() + "\n"


def prepare_pending_recipe(recipe: dict) -> dict:
    recipe["pending_recipe"] = True
    return recipe


def generate_missing_recipes(count: int, season: str, existing_families: set[str]) -> list[dict]:
    generated = []
    templates = sorted(
        GENERATED_MAIN_RECIPES,
        key=lambda item: (0 if season in item.get("preferred_seasons", []) else 1, item["title"]),
    )
    for template in templates:
        if len(generated) >= count:
            break
        if template["meal_family"] in existing_families:
            continue
        recipe = recipe_from_template(template)
        generated.append(prepare_pending_recipe(recipe))
        existing_families.add(recipe["meal_family"])
    return generated


def excluded_meal_families() -> set[str]:
    families = set()
    for path in excluded_recipe_paths():
        meta, _ = parse_frontmatter(path)
        family = meta.get("meal_family")
        if family:
            families.add(family)
    return families


def select_recipe_for_day(recipes: list[dict], used: set[str], max_active: int) -> dict:
    selected = None
    for recipe in recipes:
        if recipe["meal_family"] in used:
            continue
        if int(recipe.get("active_time", 999)) <= max_active:
            selected = recipe
            break
    if selected:
        return selected
    return next(recipe for recipe in recipes if recipe["meal_family"] not in used)


def side_dishes_for(recipe: dict) -> str:
    sides = list(recipe.get("suggested_side_dishes", []) or [])
    vegetable_terms = ("legume", "crudite", "brocoli", "salade", "concombre", "tomate", "carotte")
    starch_terms = ("riz", "pomme", "pain", "pate", "couscous", "mais")
    normalized_sides = [side.lower() for side in sides]
    has_side_vegetable = any(any(term in side for term in vegetable_terms) for side in normalized_sides)
    has_side_starch = any(any(term in side for term in starch_terms) for side in normalized_sides)
    if not recipe.get("contains_vegetable", False) and not has_side_vegetable:
        sides.append("Legumes de saison")
    if not recipe.get("contains_starch", False) and not has_side_starch:
        sides.append("Riz, pommes de terre ou pain")
    return ", ".join(sides) if sides else "aucun"


def lunch_recipe(temperatures: set[str]) -> dict | None:
    for recipe in read_recipes("lunch"):
        if recipe.get("lunch_temperature") in temperatures:
            return recipe
    return None


def choose_lunch_option(options: list[tuple], counts: dict[str, int]) -> tuple:
    for option in options:
        lunch_type = option[1]
        if counts.get(lunch_type, 0) < MAX_LUNCH_TYPE_PER_WEEK:
            counts[lunch_type] = counts.get(lunch_type, 0) + 1
            return option
    option = options[0]
    lunch_type = option[1]
    counts[lunch_type] = counts.get(lunch_type, 0) + 1
    return option


def use_leftover_lunch(dinner: dict, person: str, counts: dict[str, int]) -> tuple[str, str, str] | None:
    style = dinner.get("leftover_lunch_style", "none")
    if not dinner.get("leftover_friendly"):
        return None
    if int(dinner.get("leftover_lunch_portions_remaining", 0) or 0) <= 0:
        return None
    if person == "kids" and not dinner.get("kids_leftover_ok"):
        return None
    if person == "adults" and not dinner.get("adult_leftover_ok"):
        return None
    if person == "kids" and style not in KIDS_LEFTOVER_STYLES:
        return None
    if counts.get(style, 0) >= MAX_LUNCH_TYPE_PER_WEEK:
        return None

    counts[style] = counts.get(style, 0) + 1
    dinner["leftover_lunch_portions_used"] += 1
    dinner["leftover_lunch_portions_remaining"] -= 1
    lunch = f"{LEFTOVER_LUNCH_LABELS.get(style, 'Restants')} - {dinner['title']}"
    return lunch, style, "restants"


def build_lunches(dinners: list[dict], mode_rules: dict | None = None) -> list[dict]:
    mode_rules = mode_rules or {}
    requires_child_lunches = bool(mode_rules.get("requires_child_lunches", False))
    cold_lunch = lunch_recipe({"cold", "both"})
    adult_lunch = lunch_recipe({"cold", "reheatable", "both"})
    kids_counts: dict[str, int] = {}
    adult_counts: dict[str, int] = {}
    lunches = []
    for dinner in dinners:
        if requires_child_lunches:
            kids_leftover = use_leftover_lunch(dinner, "kids", kids_counts)
            if kids_leftover:
                kids, kids_type, kids_source = kids_leftover
            elif cold_lunch:
                kids_type = cold_lunch.get("lunch_type", "autonome")
                if kids_counts.get(kids_type, 0) < MAX_LUNCH_TYPE_PER_WEEK:
                    kids = cold_lunch["title"]
                    kids_counts[kids_type] = kids_counts.get(kids_type, 0) + 1
                    kids_source = "lunch existant"
                else:
                    kids, kids_type = choose_lunch_option(KIDS_FALLBACK_LUNCHES, kids_counts)
                    kids_source = "autonome"
            else:
                kids, kids_type = choose_lunch_option(KIDS_FALLBACK_LUNCHES, kids_counts)
                kids_source = "autonome"
        else:
            kids = "Aucun lunch enfant requis"
            kids_type = "aucun"
            kids_source = "non requis"

        adult_leftover = use_leftover_lunch(dinner, "adults", adult_counts)
        if adult_leftover:
            adults, adult_type, adult_source = adult_leftover
        elif adult_lunch:
            adult_type = adult_lunch.get("lunch_type", "autonome")
            if adult_counts.get(adult_type, 0) < MAX_LUNCH_TYPE_PER_WEEK:
                adults = adult_lunch["title"]
                adult_counts[adult_type] = adult_counts.get(adult_type, 0) + 1
                adult_source = "lunch existant"
            else:
                adults, adult_type, adult_source = choose_lunch_option(ADULT_FALLBACK_LUNCHES, adult_counts)
        else:
            adults, adult_type, adult_source = choose_lunch_option(ADULT_FALLBACK_LUNCHES, adult_counts)
        used = dinner.get("leftover_lunch_portions_used", 0)
        capacity = dinner.get("leftover_lunch_portions", 0)
        diagnostic = f"restants: {used}/{capacity} portions utilisees" if capacity else "restants: 0/0 portions"
        if requires_child_lunches:
            source = kids_source if kids_source == adult_source else f"enfants: {kids_source}; adultes: {adult_source}"
        else:
            source = f"adultes: {adult_source}"
        lunches.append(
            {
                "day": dinner["day"],
                "kids_lunch": kids,
                "kids_type": kids_type,
                "adult_lunch": adults,
                "adult_type": adult_type,
                "source": f"{source}; {diagnostic}",
            }
        )
    return lunches


def build_plan(week: str, season: str) -> tuple[dict, list[dict], list[dict], list[dict]]:
    constraints = read_constraints()
    modes = read_modes()
    mode_rules = active_mode_rules(modes)
    existing_recipes = choose_recipes(season, mode_rules)
    generated_target = 1 if len(existing_recipes) >= 4 else len(PLAN_DAYS) - len(existing_recipes)
    existing_families = {recipe["meal_family"] for recipe in read_recipes("main")} | excluded_meal_families()
    generated_recipes = generate_missing_recipes(generated_target, season, existing_families)
    existing_target = len(PLAN_DAYS) - len(generated_recipes)
    recipes = existing_recipes[:existing_target] + generated_recipes
    if len(recipes) < len(PLAN_DAYS):
        print("Not enough eligible recipes to fill the plan.")
        sys.exit(1)

    dinners = []
    used = set()
    for day in PLAN_DAYS:
        base_max_active = constraints.get(day, {}).get("max_active_time", 999)
        max_active = max(0, base_max_active + int(mode_rules.get("max_active_time_bias", 0) or 0))
        selected = select_recipe_for_day(recipes, used, max_active)
        used.add(selected["meal_family"])
        active = int(selected.get("active_time", 0))
        status = "OK" if active <= max_active else f"depasse {max_active} min"
        source = "nouveau" if selected.get("pending_recipe") else "existant"
        dinners.append(
            {
                "day": day,
                "title": selected["title"],
                "meal_family": selected["meal_family"],
                "side": side_dishes_for(selected),
                "notes": f"{active} min actif; {status}; {source}",
                "leftover_friendly": bool(selected.get("leftover_friendly")),
                "leftover_lunch_portions": int(selected.get("leftover_lunch_portions", 0) or 0),
                "leftover_lunch_portions_remaining": int(selected.get("leftover_lunch_portions", 0) or 0),
                "leftover_lunch_portions_used": 0,
                "leftover_lunch_style": selected.get("leftover_lunch_style", "none"),
                "kids_leftover_ok": bool(selected.get("kids_leftover_ok", False)),
                "adult_leftover_ok": bool(selected.get("adult_leftover_ok", False)),
            }
        )

    lunches = build_lunches(dinners, mode_rules)
    meta = {
        "week": week,
        "season": season,
        "modes": modes,
        "days": "Jour 1-Jour 5",
        "status": "draft",
        "new_dinner_recipes": len(generated_recipes),
        "pending_recipes": len(generated_recipes),
    }
    return meta, dinners, lunches, generated_recipes


def write_pending_recipes(week: str, recipes: list[dict]) -> None:
    if not recipes:
        return
    out_dir = DATA / "drafts" / f"{week}_recipes"
    out_dir.mkdir(parents=True, exist_ok=True)
    for recipe in recipes:
        out = out_dir / f"{slug(recipe['title'])}.md"
        out.write_text(render_recipe(recipe), encoding="utf-8")


def write_plan(meta: dict, dinners: list[dict], lunches: list[dict], pending_recipes: list[dict]) -> str:
    out = DATA / "drafts" / f"{meta['week']}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_pending_recipes(meta["week"], pending_recipes)
    lines = [frontmatter(meta).rstrip(), "", f"# Plan de repas - {meta['week']}", ""]
    lines.extend(["## Soupers", "", "| Jour | Recipe | Meal Family | Side | Notes |", "| --- | --- | --- | --- | --- |"])
    for dinner in dinners:
        lines.append(
            f"| {dinner['day']} | {dinner['title']} | {dinner['meal_family']} | {dinner['side']} | {dinner['notes']} |"
        )
    lines.append("")
    lines.extend(
        [
            "## Lunchs",
            "",
            "| Jour | Kids Lunch | Kids Type | Adult Lunch | Adult Type | Source |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for lunch in lunches:
        lines.append(
            f"| {lunch['day']} | {lunch['kids_lunch']} | {lunch['kids_type']} | {lunch['adult_lunch']} | {lunch['adult_type']} | {lunch['source']} |"
        )
    lines.append("")
    lines.append("## Score")
    lines.append("")
    lines.append("Le score est calcule apres ecriture du plan.")
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    scores = score_plan(out)
    scored = out.read_text(encoding="utf-8").replace(
        "Le score est calcule apres ecriture du plan.",
        "\n".join(f"- {key}: {value}" for key, value in scores.items()),
    )
    out.write_text(scored, encoding="utf-8")
    return str(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the current weekly meal plan")
    parser.add_argument("--date", help="Date YYYY-MM-DD used for week and season detection")
    args = parser.parse_args()
    today = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    week = current_week(today)
    season = season_for_date(today)
    meta, dinners, lunches, pending_recipes = build_plan(week, season)
    plan_path = write_plan(meta, dinners, lunches, pending_recipes)
    print(f"Draft written: {plan_path}")
    if pending_recipes:
        print(f"Pending recipes written: {DATA / 'drafts' / f'{week}_recipes'}")
    print("Grocery list not generated until commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
