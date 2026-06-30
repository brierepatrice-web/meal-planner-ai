from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
OUT = ROOT / "docs" / "meal-flow.png"

NODE_RE = re.compile(r'^\s*([A-Za-z][A-Za-z0-9]*)\["(.+?)"\]\s*$')
DECISION_RE = re.compile(r'^\s*([A-Za-z][A-Za-z0-9]*)\{"(.+?)"\}\s*$')
EDGE_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]*)\s+[-.]+(?:\s*[^-]+?\s*)?[-.]*>\s*([A-Za-z][A-Za-z0-9]*)\s*$")

LAYOUT = {
    "user": (0, 0),
    "profile": (0, 2),
    "inventory": (0, 3),
    "planning": (0, 4),
    "history": (0, 5),
    "recipes": (0, 6),
    "validate": (1, 3),
    "plan": (2, 3),
    "draft": (3, 2),
    "pending": (3, 4),
    "scoreDraft": (4, 1),
    "edit": (4, 3),
    "approve": (5, 3),
    "commit": (6, 3),
    "planOut": (7, 2),
    "activeRecipes": (7, 3),
    "groceryValidation": (7, 4),
    "grocery": (8, 4),
    "groceryHtml": (9, 4),
    "groceryReviewCommand": (9, 5),
    "groceryReview": (10, 5),
    "mealHtml": (8, 1),
    "inventoryHtml": (8, 6),
    "consumed": (8, 2),
    "consume": (9, 2),
    "historyUpdate": (10, 1),
    "eventLog": (10, 2),
    "inventoryUpdate": (10, 3),
}


def mermaid_block() -> str:
    text = README.read_text(encoding="utf-8")
    match = re.search(r"```mermaid\n(.*?)\n```", text, re.S)
    if not match:
        raise RuntimeError("No Mermaid block found in README.md")
    return match.group(1)


def parse_graph(block: str) -> tuple[dict[str, tuple[str, bool]], list[tuple[str, str]]]:
    nodes: dict[str, tuple[str, bool]] = {}
    edges: list[tuple[str, str]] = []
    for line in block.splitlines():
        node = NODE_RE.match(line)
        decision = DECISION_RE.match(line)
        edge = EDGE_RE.match(line)
        if node:
            nodes[node.group(1)] = (node.group(2).replace("<br/>", "\n"), False)
        elif decision:
            nodes[decision.group(1)] = (decision.group(2).replace("<br/>", "\n"), True)
        elif edge:
            edges.append((edge.group(1), edge.group(2)))
    return nodes, edges


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def wrap_line(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def node_box(node_id: str) -> tuple[int, int, int, int]:
    col, row = LAYOUT[node_id]
    x = 80 + col * 300
    y = 70 + row * 150
    return x, y, x + 245, y + 95


def center(box: tuple[int, int, int, int]) -> tuple[int, int]:
    x1, y1, x2, y2 = box
    return (x1 + x2) // 2, (y1 + y2) // 2


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    sx, sy = start
    ex, ey = end
    draw.line((sx, sy, ex, ey), fill="#6b7280", width=3)
    angle_x = -1 if ex < sx else 1
    draw.polygon([(ex, ey), (ex - 12 * angle_x, ey - 7), (ex - 12 * angle_x, ey + 7)], fill="#6b7280")


def render() -> None:
    nodes, edges = parse_graph(mermaid_block())
    missing = sorted(set(nodes) - set(LAYOUT))
    if missing:
        raise RuntimeError(f"Missing layout entries for: {', '.join(missing)}")

    image = Image.new("RGB", (3500, 1100), "#f8fafc")
    draw = ImageDraw.Draw(image)
    title_font = load_font(36, bold=True)
    font = load_font(20)
    small_font = load_font(17)

    draw.text((80, 25), "Meal Planner AI - Flow du projet", fill="#111827", font=title_font)

    for source, target in edges:
        if source not in LAYOUT or target not in LAYOUT:
            continue
        sx1, sy1, sx2, sy2 = node_box(source)
        tx1, ty1, tx2, ty2 = node_box(target)
        start = (sx2, (sy1 + sy2) // 2) if tx1 >= sx1 else (sx1, (sy1 + sy2) // 2)
        end = (tx1, (ty1 + ty2) // 2) if tx1 >= sx1 else (tx2, (ty1 + ty2) // 2)
        draw_arrow(draw, start, end)

    for node_id, (label, is_decision) in nodes.items():
        box = node_box(node_id)
        x1, y1, x2, y2 = box
        fill = "#fff7ed" if is_decision else "#ffffff"
        outline = "#f97316" if is_decision else "#2563eb"
        draw.rounded_rectangle(box, radius=14, fill=fill, outline=outline, width=3)
        text_lines: list[str] = []
        for raw_line in label.splitlines():
            text_lines.extend(wrap_line(draw, raw_line, font, 205))
        line_height = 25
        total_height = line_height * len(text_lines)
        y = y1 + ((y2 - y1) - total_height) // 2
        for index, line in enumerate(text_lines):
            active_font = font if index == 0 else small_font
            bbox = draw.textbbox((0, 0), line, font=active_font)
            draw.text(((x1 + x2 - bbox[2]) // 2, y), line, fill="#111827", font=active_font)
            y += line_height

    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT)
    print(f"PNG written: {OUT}")


if __name__ == "__main__":
    render()
