from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

from generate_grocery_list import grocery_items_for_plan
from meal_os import DATA, GROCERY_CATEGORIES, latest_file, parse_plan


OUT_DIR = DATA / "grocery_lists_html"


def item_label(markdown_item: str) -> str:
    return markdown_item.strip()[2:] if markdown_item.startswith("- ") else markdown_item.strip()


def item_id(category: str, label: str) -> str:
    digest = hashlib.sha1(f"{category}|{label}".encode("utf-8")).hexdigest()
    return digest[:12]


def grocery_payload(plan_path: Path) -> dict:
    meta, _, _ = parse_plan(plan_path)
    week = meta.get("week", plan_path.stem)
    categories, skipped = grocery_items_for_plan(plan_path)
    items = []
    for category in GROCERY_CATEGORIES:
        for markdown_item in categories[category]:
            label = item_label(markdown_item)
            if not label or label == "Aucun achat":
                continue
            items.append(
                {
                    "id": item_id(category, label),
                    "category": category,
                    "label": label,
                    "recurrent": "[recurrent]" in label,
                }
            )
    fingerprint = hashlib.sha1(
        "\n".join(f"{item['category']}|{item['label']}" for item in items).encode("utf-8")
    ).hexdigest()[:12]
    return {
        "week": week,
        "sourcePlan": plan_path.name,
        "fingerprint": fingerprint,
        "items": items,
        "skipped": skipped,
        "categories": GROCERY_CATEGORIES,
    }


def render_recurrent_tag(is_recurrent: bool) -> str:
    if not is_recurrent:
        return ""
    return '<span class="tag">recurrent</span>'


def display_label(label: str) -> str:
    return label.replace(" [recurrent]", "")


def render_static_item(item: dict) -> str:
    checked = ' data-static="true"'
    label = html.escape(display_label(item["label"]))
    tag = render_recurrent_tag(bool(item.get("recurrent")))
    return (
        f'<label class="item" data-id="{html.escape(item["id"])}" '
        f'data-category="{html.escape(item["category"])}">'
        f'<input type="checkbox"{checked}>'
        f'<span class="item-label">{label}{tag}</span>'
        "</label>"
    )


def render_static_inventory(payload: dict) -> str:
    if not payload["skipped"]:
        return ""
    items = "\n".join(
        f'        <div class="inventory-item">{html.escape(item)}</div>' for item in payload["skipped"]
    )
    return f"""    <section>
      <h2>Deja dans l'inventaire</h2>
{items}
    </section>"""


def render_static_shopping(payload: dict) -> str:
    sections = []
    for category in payload["categories"]:
        category_items = [item for item in payload["items"] if item["category"] == category]
        if not category_items:
            continue
        rendered_items = "\n".join(f"        {render_static_item(item)}" for item in category_items)
        sections.append(
            f"""    <section>
      <h2>{html.escape(category)}</h2>
      <div class="list">
{rendered_items}
      </div>
    </section>"""
        )
    return "\n".join(sections)


def render_html(payload: dict) -> str:
    json_payload = json.dumps(payload, ensure_ascii=False)
    escaped_payload = html.escape(json_payload, quote=False)
    title = f"Liste d'epicerie - {payload['week']}"
    static_inventory = render_static_inventory(payload)
    static_shopping = render_static_shopping(payload)
    total_items = len(payload["items"])
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #172033;
      --muted: #647084;
      --line: #d9dee8;
      --accent: #0f766e;
      --accent-soft: #d9f3ef;
      --done: #eef1f5;
      --shadow: 0 2px 10px rgba(15, 23, 42, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      font-size: 16px;
      line-height: 1.35;
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 10;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      padding: 14px 16px 12px;
      box-shadow: var(--shadow);
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 22px;
      letter-spacing: 0;
    }}
    .meta {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      color: var(--muted);
      font-size: 14px;
    }}
    main {{
      max-width: 760px;
      margin: 0 auto;
      padding: 14px 12px 98px;
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
      box-shadow: var(--shadow);
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
    section {{
      margin: 0 0 14px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    h2 {{
      margin: 0;
      padding: 12px 14px;
      font-size: 17px;
      background: #fafbfc;
      border-bottom: 1px solid var(--line);
      letter-spacing: 0;
    }}
    .list {{
      display: grid;
      gap: 0;
    }}
    .item {{
      display: grid;
      grid-template-columns: 34px 1fr;
      align-items: center;
      gap: 8px;
      width: 100%;
      min-height: 54px;
      padding: 10px 14px;
      background: var(--panel);
      border: 0;
      border-bottom: 1px solid var(--line);
      color: var(--text);
      text-align: left;
      font: inherit;
    }}
    .item:last-child {{ border-bottom: 0; }}
    .item input {{
      width: 24px;
      height: 24px;
      accent-color: var(--accent);
    }}
    .item-label {{
      overflow-wrap: anywhere;
    }}
    .tag {{
      display: inline-block;
      margin-left: 6px;
      padding: 2px 6px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: #115e59;
      font-size: 12px;
      vertical-align: middle;
    }}
    .empty, .inventory-item {{
      padding: 12px 14px;
      color: var(--muted);
      border-bottom: 1px solid var(--line);
    }}
    .inventory-item:last-child {{ border-bottom: 0; }}
    .done-section .item {{
      background: var(--done);
      color: var(--muted);
    }}
    .done-section .item-label {{
      text-decoration: line-through;
    }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <div class="meta">
      <span>Source: {html.escape(payload['sourcePlan'])}</span>
      <strong id="remainingCount">{total_items} restants</strong>
    </div>
  </header>
  <main>
    <div id="inventory">
{static_inventory}
    </div>
    <div id="shopping">
{static_shopping}
    </div>
    <section class="done-section">
      <h2>Achete</h2>
      <div class="list" id="doneList">
        <div class="empty">Rien de coche pour le moment.</div>
      </div>
    </section>
  </main>
  <nav class="quick-nav" aria-label="Navigation mobile">
    <a class="active" href="liste-epicerie.html">Epicerie</a>
    <a href="repas-semaine.html">Repas</a>
  </nav>
  <script type="application/json" id="groceryData">{escaped_payload}</script>
  <script>
    const data = JSON.parse(document.getElementById("groceryData").textContent);
    const storageKey = `grocery-html:${{data.week}}:${{data.fingerprint}}`;
    const checked = new Set(JSON.parse(localStorage.getItem(storageKey) || "[]"));
    const shopping = document.getElementById("shopping");
    const doneList = document.getElementById("doneList");
    const remainingCount = document.getElementById("remainingCount");

    function save() {{
      localStorage.setItem(storageKey, JSON.stringify([...checked]));
    }}

    function itemElement(item) {{
      const label = document.createElement("label");
      label.className = "item";
      label.dataset.id = item.id;
      label.dataset.category = item.category;

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = checked.has(item.id);
      checkbox.addEventListener("change", () => {{
        if (checkbox.checked) {{
          checked.add(item.id);
        }} else {{
          checked.delete(item.id);
        }}
        save();
        render();
      }});

      const text = document.createElement("span");
      text.className = "item-label";
      text.textContent = item.label.replace(" [recurrent]", "");
      if (item.recurrent) {{
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = "recurrent";
        text.appendChild(tag);
      }}

      label.appendChild(checkbox);
      label.appendChild(text);
      return label;
    }}

    function renderInventory() {{
      const inventory = document.getElementById("inventory");
      inventory.replaceChildren();
      if (!data.skipped.length) return;
      const section = document.createElement("section");
      const h2 = document.createElement("h2");
      h2.textContent = "Deja dans l'inventaire";
      section.appendChild(h2);
      data.skipped.forEach((item) => {{
        const div = document.createElement("div");
        div.className = "inventory-item";
        div.textContent = item;
        section.appendChild(div);
      }});
      inventory.appendChild(section);
    }}

    function render() {{
      shopping.replaceChildren();
      doneList.replaceChildren();
      let remaining = 0;

      data.categories.forEach((category) => {{
        const categoryItems = data.items.filter((item) => item.category === category);
        const activeItems = categoryItems.filter((item) => !checked.has(item.id));
        if (!categoryItems.length) return;

        const section = document.createElement("section");
        const h2 = document.createElement("h2");
        h2.textContent = category;
        section.appendChild(h2);

        const list = document.createElement("div");
        list.className = "list";
        if (activeItems.length) {{
          activeItems.forEach((item) => list.appendChild(itemElement(item)));
        }} else {{
          const empty = document.createElement("div");
          empty.className = "empty";
          empty.textContent = "Tout est coche dans cette categorie.";
          list.appendChild(empty);
        }}
        section.appendChild(list);
        shopping.appendChild(section);
        remaining += activeItems.length;
      }});

      data.items
        .filter((item) => checked.has(item.id))
        .forEach((item) => doneList.appendChild(itemElement(item)));

      if (!doneList.children.length) {{
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = "Rien de coche pour le moment.";
        doneList.appendChild(empty);
      }}

      remainingCount.textContent = `${{remaining}} restant${{remaining > 1 ? "s" : ""}}`;
    }}

    renderInventory();
    render();
  </script>
</body>
</html>
"""


def write_grocery_html(plan_path: Path, out_path: Path | None = None) -> Path:
    payload = grocery_payload(plan_path)
    out = out_path or OUT_DIR / f"{payload['week']}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(payload), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a mobile-friendly grocery list HTML file")
    parser.add_argument("--plan", type=Path, help="Plan Markdown a utiliser")
    parser.add_argument("--out", type=Path, help="Chemin HTML de sortie")
    args = parser.parse_args()
    plan_path = args.plan or latest_file(DATA / "plans")
    if not plan_path:
        print("No plan found. Run scripts/commit_plan.py first.")
        return 1
    if not plan_path.exists():
        print(f"Plan not found: {plan_path}")
        return 1
    out = write_grocery_html(plan_path, args.out)
    print(f"Grocery HTML written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
