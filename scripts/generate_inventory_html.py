from __future__ import annotations

import argparse
import html
from pathlib import Path

from meal_os import DATA, read_bullets


OUT_DIR = DATA / "inventory_html"
INVENTORY_ORDER = ["fresh", "freezer", "pantry", "proteins", "condiments"]
INVENTORY_LABELS = {
    "fresh": "Frais",
    "freezer": "Congelateur",
    "pantry": "Garde-manger",
    "proteins": "Proteines",
    "condiments": "Condiments",
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def inventory_payload() -> list[dict]:
    sections = []
    inventory_dir = DATA / "inventory"
    known_paths = [inventory_dir / f"{name}.md" for name in INVENTORY_ORDER]
    extra_paths = sorted(path for path in inventory_dir.glob("*.md") if path not in known_paths)

    for path in [*known_paths, *extra_paths]:
        if not path.exists():
            continue
        items = []
        for raw_item in read_bullets(path):
            parts = [part.strip() for part in raw_item.split("|")]
            if not parts or not parts[0] or parts[0].lower() == "no items yet.":
                continue
            items.append(
                {
                    "name": parts[0],
                    "detail": " | ".join(parts[1:]) if len(parts) > 1 else "",
                }
            )
        sections.append(
            {
                "id": path.stem,
                "title": INVENTORY_LABELS.get(path.stem, path.stem.replace("-", " ").title()),
                "items": items,
            }
        )
    return sections


def render_item(item: dict) -> str:
    detail = item.get("detail") or "en inventaire"
    return f"""
        <li class="item">
          <span>{esc(item["name"])}</span>
          <strong>{esc(detail)}</strong>
        </li>"""


def render_section(section: dict) -> str:
    items = section["items"]
    if items:
        rendered_items = "\n".join(render_item(item) for item in items)
    else:
        rendered_items = '<li class="empty">Aucun item</li>'
    count = len(items)
    label = f"{count} item" if count == 1 else f"{count} items"
    return f"""
    <section>
      <h2>
        <span>{esc(section["title"])}</span>
        <small>{esc(label)}</small>
      </h2>
      <ul class="list">
{rendered_items}
      </ul>
    </section>"""


def render_html(sections: list[dict]) -> str:
    section_html = "\n".join(render_section(section) for section in sections)
    total_items = sum(len(section["items"]) for section in sections)
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Inventaire</title>
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
      grid-template-columns: repeat(3, 1fr);
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
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 0;
      padding: 12px 14px;
      font-size: 17px;
      background: #fafbfc;
      border-bottom: 1px solid var(--line);
      letter-spacing: 0;
    }}
    h2 small {{
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }}
    .list {{
      list-style: none;
      margin: 0;
      padding: 0;
    }}
    .item {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      min-height: 52px;
      padding: 11px 14px;
      border-bottom: 1px solid var(--line);
    }}
    .item:last-child {{ border-bottom: 0; }}
    .item span {{
      overflow-wrap: anywhere;
      font-weight: 700;
    }}
    .item strong {{
      color: var(--accent);
      text-align: right;
      white-space: normal;
    }}
    .empty {{
      padding: 12px 14px;
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <header>
    <h1>Inventaire</h1>
    <div class="meta">{total_items} items en inventaire</div>
  </header>
  <main>
{section_html}
  </main>
  <nav class="quick-nav" aria-label="Navigation mobile">
    <a href="liste-epicerie.html">Epicerie</a>
    <a href="repas-semaine.html">Repas</a>
    <a class="active" href="inventaire.html">Inventaire</a>
  </nav>
</body>
</html>
"""


def write_inventory_html(out_path: Path | None = None) -> Path:
    out = out_path or OUT_DIR / "inventaire.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(inventory_payload()), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generer une page HTML mobile de l'inventaire.")
    parser.add_argument("--out", type=Path, help="Chemin HTML de sortie")
    args = parser.parse_args()
    out_path = write_inventory_html(args.out)
    print(f"Inventory HTML written: {out_path}")


if __name__ == "__main__":
    main()
