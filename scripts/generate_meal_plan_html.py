from __future__ import annotations

import argparse
import hashlib
import html
import re
from pathlib import Path

from meal_os import DATA, latest_file, parse_frontmatter, parse_plan, read_pending_recipes, read_recipes


OUT_DIR = DATA / "meal_plan_html"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def recipe_id(title: str) -> str:
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:10]
    return f"recipe-{digest}"


def recipe_lookup(plan_path: Path) -> dict[str, dict]:
    recipes = read_recipes("main") + read_pending_recipes(plan_path, "main")
    return {recipe["title"]: recipe for recipe in recipes}


def section_bullets(body: str, heading: str) -> list[str]:
    values = []
    in_section = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if in_section:
                break
            in_section = stripped.lower() == heading.lower()
            continue
        if in_section and stripped.startswith("- "):
            value = stripped[2:].strip()
            value = re.sub(r"^\d+\.\s*", "", value)
            values.append(value)
    return values


def method_steps(recipe: dict) -> list[str]:
    _, body = parse_frontmatter(recipe["path"])
    return section_bullets(body, "## methode")


def render_ingredient(ingredient: dict) -> str:
    quantity = ingredient.get("quantity", "au besoin")
    name = ingredient.get("name", "")
    category = ingredient.get("category", "Autres")
    return (
        "<li>"
        f"<span>{esc(name)}</span>"
        f"<strong>{esc(quantity)}</strong>"
        f"<small>{esc(category)}</small>"
        "</li>"
    )


def render_recipe(recipe: dict | None, dinner: dict) -> str:
    title = dinner["title"]
    anchor = recipe_id(title)
    side = dinner.get("side") or "aucun"
    notes = dinner.get("notes") or ""

    if not recipe:
        return f"""
        <section class="recipe-card" id="{anchor}">
          <div class="recipe-heading">
            <div>
              <p class="eyebrow">{esc(dinner["day"])}</p>
              <h2>{esc(title)}</h2>
            </div>
          </div>
          <p class="missing">Recette introuvable dans la banque active ou pending.</p>
          <a class="top-link" href="#top">Retour en haut</a>
        </section>
        """

    ingredients = "\n".join(render_ingredient(item) for item in recipe.get("ingredients", []))
    steps = method_steps(recipe)
    method = "\n".join(f"<li>{esc(step)}</li>" for step in steps)
    if not method:
        method = "<li>Methode non disponible.</li>"

    meta_items = [
        ("Portions", recipe.get("portions")),
        ("Actif", recipe.get("active_time")),
        ("Prep", recipe.get("prep_time")),
        ("Cuisson", recipe.get("cook_time")),
    ]
    meta = "\n".join(
        f"<span class=\"pill\"><strong>{esc(label)}</strong> {esc(value)}</span>"
        for label, value in meta_items
        if value not in (None, "")
    )

    return f"""
    <section class="recipe-card" id="{anchor}">
      <div class="recipe-heading">
        <div>
          <p class="eyebrow">{esc(dinner["day"])}</p>
          <h2>{esc(title)}</h2>
        </div>
        <a class="small-action" href="#top">Plan</a>
      </div>
      <div class="meta-row">
        {meta}
        <span class="pill"><strong>Accompagnement</strong> {esc(side)}</span>
      </div>
      <p class="notes">{esc(notes)}</p>
      <div class="recipe-grid">
        <div>
          <h3>Ingredients</h3>
          <ul class="ingredients">
            {ingredients}
          </ul>
        </div>
        <div>
          <h3>Methode</h3>
          <ol class="method">
            {method}
          </ol>
        </div>
      </div>
    </section>
    """


def render_agenda(dinners: list[dict]) -> str:
    items = []
    for dinner in dinners:
        anchor = recipe_id(dinner["title"])
        side = dinner.get("side") or "aucun"
        notes = dinner.get("notes") or ""
        items.append(
            f"""
            <a class="agenda-card" href="#{anchor}">
              <span class="day">{esc(dinner["day"])}</span>
              <strong>{esc(dinner["title"])}</strong>
              <span>{esc(side)}</span>
              <small>{esc(notes)}</small>
            </a>
            """
        )
    return "\n".join(items)


def render_html(plan_path: Path) -> str:
    meta, dinners, _ = parse_plan(plan_path)
    week = meta.get("week") or plan_path.stem
    recipes = recipe_lookup(plan_path)
    recipe_sections = "\n".join(render_recipe(recipes.get(dinner["title"]), dinner) for dinner in dinners)

    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Repas de la semaine - {esc(week)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f5ef;
      --paper: #ffffff;
      --ink: #172026;
      --muted: #657078;
      --line: #dad5ca;
      --accent: #0f766e;
      --accent-soft: #d8f3ee;
      --warm: #f4b860;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 10;
      background: rgba(247, 245, 239, 0.96);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(12px);
    }}
    .bar, main {{
      width: min(1120px, 100%);
      margin: 0 auto;
      padding: 16px;
    }}
    main {{ padding-bottom: 98px; }}
    h1, h2, h3, p {{ margin-top: 0; }}
    h1 {{ margin-bottom: 4px; font-size: 28px; line-height: 1.15; }}
    h2 {{ margin-bottom: 0; font-size: 24px; line-height: 1.2; }}
    h3 {{ margin-bottom: 12px; font-size: 18px; }}
    .subtitle {{ margin: 0 0 12px; color: var(--muted); font-size: 14px; }}
    .small-action, .top-link {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid var(--accent);
      background: var(--accent);
      color: white;
      font-weight: 700;
      text-decoration: none;
    }}
    .small-action, .top-link {{
      background: white;
      color: var(--accent);
    }}
    .quick-nav {{
      position: fixed;
      left: 50%;
      bottom: calc(10px + env(safe-area-inset-bottom));
      z-index: 20;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      width: min(760px, calc(100% - 24px));
      margin: 0 auto;
      padding: 8px;
      background: rgba(255, 255, 255, 0.96);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(15, 23, 42, 0.12);
      transform: translateX(-50%);
    }}
    .quick-nav a {{
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      border-radius: 8px;
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
    }}
    .quick-nav a.active {{
      background: var(--accent);
      color: white;
    }}
    .agenda {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 10px;
      margin: 12px 0 24px;
    }}
    .agenda-card {{
      min-height: 150px;
      display: grid;
      align-content: start;
      gap: 7px;
      padding: 14px;
      border: 1px solid var(--line);
      border-left: 6px solid var(--warm);
      border-radius: 8px;
      background: var(--paper);
      color: inherit;
      text-decoration: none;
    }}
    .agenda-card strong {{ font-size: 18px; line-height: 1.25; }}
    .agenda-card small, .agenda-card span:not(.day) {{ color: var(--muted); }}
    .day, .eyebrow {{
      color: var(--accent);
      font-size: 13px;
      font-weight: 800;
      letter-spacing: 0;
      text-transform: uppercase;
    }}
    .recipe-card {{
      margin: 0 0 18px;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--paper);
    }}
    .recipe-heading {{
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 14px;
      margin-bottom: 14px;
    }}
    .meta-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }}
    .pill {{
      display: inline-flex;
      gap: 6px;
      align-items: center;
      padding: 7px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: #164e46;
      font-size: 14px;
    }}
    .notes {{ color: var(--muted); }}
    .recipe-grid {{
      display: grid;
      grid-template-columns: minmax(260px, 0.8fr) minmax(0, 1.2fr);
      gap: 22px;
      align-items: start;
    }}
    .ingredients, .method {{ margin: 0; padding-left: 22px; }}
    .ingredients li {{
      margin: 0 0 9px;
      padding-bottom: 9px;
      border-bottom: 1px solid #ece7dc;
    }}
    .ingredients span, .ingredients strong, .ingredients small {{
      display: block;
    }}
    .ingredients strong {{ color: var(--accent); }}
    .ingredients small {{ color: var(--muted); }}
    .method li {{ margin-bottom: 12px; padding-left: 4px; }}
    .missing {{
      padding: 12px;
      border: 1px solid #f59e0b;
      border-radius: 8px;
      background: #fffbeb;
    }}
    @media (max-width: 720px) {{
      .bar, main {{ padding: 14px; }}
      h1 {{ font-size: 25px; }}
      .recipe-card {{ padding: 15px; }}
      .recipe-heading {{ align-items: stretch; }}
      .small-action {{ min-width: 72px; }}
      .recipe-grid {{ grid-template-columns: 1fr; gap: 18px; }}
      .agenda {{ grid-template-columns: 1fr; }}
      .agenda-card {{ min-height: 0; }}
    }}
  </style>
</head>
<body>
  <header id="top">
    <div class="bar">
      <h1>Repas de la semaine - {esc(week)}</h1>
      <p class="subtitle">Plan source: {esc(plan_path.as_posix())}</p>
    </div>
  </header>
  <main>
    <section aria-labelledby="agenda-title">
      <h2 id="agenda-title">Agenda</h2>
      <div class="agenda">
        {render_agenda(dinners)}
      </div>
    </section>
    <section id="recettes" aria-labelledby="recipes-title">
      <h2 id="recipes-title">Recettes completes</h2>
      {recipe_sections}
    </section>
  </main>
  <nav class="quick-nav" aria-label="Navigation mobile">
    <a href="liste-epicerie.html">Epicerie</a>
    <a class="active" href="repas-semaine.html">Repas</a>
  </nav>
</body>
</html>
"""


def write_meal_plan_html(plan_path: Path, out_path: Path | None = None) -> Path:
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan not found: {plan_path}")

    meta, _, _ = parse_plan(plan_path)
    week = meta.get("week") or plan_path.stem
    target = out_path or OUT_DIR / f"{week}.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_html(plan_path), encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Generer une page HTML mobile du plan de repas.")
    parser.add_argument("--plan", type=Path, help="Plan Markdown a utiliser")
    parser.add_argument("--out", type=Path, help="Chemin HTML de sortie")
    args = parser.parse_args()

    plan_path = args.plan or latest_file(DATA / "plans")
    if not plan_path:
        raise SystemExit("Aucun plan committed trouve dans data/plans/.")

    out_path = write_meal_plan_html(plan_path, args.out)
    print(f"Meal plan HTML written: {out_path}")


if __name__ == "__main__":
    main()
