from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from meal_os import GROCERY_CATEGORIES, canonical_ingredient_name


MERGEABLE_UNITS = {"", "tasse", "tasses"}


@dataclass
class GroceryItem:
    name: str
    canonical_name: str
    category: str
    quantity: str
    quantity_number: int | None
    unit: str
    recurrent: bool
    source_label: str

    @property
    def merge_key(self) -> tuple[str, str, str, bool]:
        return (self.category, self.canonical_name, normalized_unit(self.unit), self.recurrent)

    @property
    def rendered(self) -> str:
        suffix = " [recurrent]" if self.recurrent else ""
        return f"- {self.name} ({self.quantity}){suffix}"


@dataclass
class ValidationResult:
    categories: dict[str, list[str]]
    skipped: list[str]
    merged: list[str] = field(default_factory=list)
    ambiguous: list[str] = field(default_factory=list)
    ai_review: str | None = None


def normalized_unit(unit: str) -> str:
    clean = unit.strip().lower()
    if clean in {"tasse", "tasses"}:
        return "tasse"
    return clean


def parse_quantity(value: str) -> tuple[int | None, str]:
    clean = value.strip()
    match = re.fullmatch(r"(\d+)(?:\s+(.+))?", clean)
    if not match:
        return None, clean.lower()
    return int(match.group(1)), (match.group(2) or "").strip().lower()


def parse_grocery_item(category: str, markdown_item: str) -> GroceryItem | None:
    label = markdown_item.strip()
    if label.startswith("- "):
        label = label[2:].strip()
    if not label or label == "Aucun achat":
        return None

    recurrent = False
    if label.endswith(" [recurrent]"):
        recurrent = True
        label = label[: -len(" [recurrent]")].strip()

    match = re.fullmatch(r"(.+?)\s+\((.+)\)", label)
    if not match:
        return None

    name = match.group(1).strip()
    quantity = match.group(2).strip()
    quantity_number, unit = parse_quantity(quantity)
    return GroceryItem(
        name=name,
        canonical_name=canonical_ingredient_name(name),
        category=category if category in GROCERY_CATEGORIES else "Autres",
        quantity=quantity,
        quantity_number=quantity_number,
        unit=unit,
        recurrent=recurrent,
        source_label=markdown_item,
    )


def format_quantity(quantity_number: int, unit: str) -> str:
    unit = unit.strip()
    if not unit:
        return str(quantity_number)
    if normalized_unit(unit) == "tasse" and quantity_number > 1:
        unit = "tasses"
    return f"{quantity_number} {unit}"


def can_merge(item: GroceryItem) -> bool:
    return item.quantity_number is not None and normalized_unit(item.unit) in MERGEABLE_UNITS


def validate_grocery_items(
    categories: dict[str, list[str]],
    skipped: list[str],
    *,
    use_ai: bool = False,
) -> ValidationResult:
    entries_by_category: dict[str, list[GroceryItem | str]] = {category: [] for category in GROCERY_CATEGORIES}
    merge_groups: dict[tuple[str, str, str, bool], list[GroceryItem]] = {}
    ambiguous: list[str] = []

    for category in GROCERY_CATEGORIES:
        for markdown_item in categories.get(category, []):
            item = parse_grocery_item(category, markdown_item)
            if item is None:
                entries_by_category[category].append(markdown_item)
                continue
            entries_by_category[category].append(item)
            if can_merge(item):
                merge_groups.setdefault(item.merge_key, []).append(item)
            elif item.quantity_number is None or normalized_unit(item.unit) not in MERGEABLE_UNITS:
                ambiguous.append(f"{item.name} ({item.quantity})")

    validated = {category: [] for category in GROCERY_CATEGORIES}
    merged_notes: list[str] = []
    rendered_groups: set[tuple[str, str, str, bool]] = set()

    for category in GROCERY_CATEGORIES:
        seen_rendered = set()
        for entry in entries_by_category[category]:
            if isinstance(entry, str):
                if entry not in seen_rendered:
                    validated[category].append(entry)
                    seen_rendered.add(entry)
                continue

            if can_merge(entry):
                if entry.merge_key in rendered_groups:
                    continue
                group = merge_groups[entry.merge_key]
                total = sum(item.quantity_number or 0 for item in group)
                merged_item = GroceryItem(
                    name=entry.name,
                    canonical_name=entry.canonical_name,
                    category=entry.category,
                    quantity=format_quantity(total, entry.unit),
                    quantity_number=total,
                    unit=entry.unit,
                    recurrent=entry.recurrent,
                    source_label=entry.source_label,
                )
                validated[category].append(merged_item.rendered)
                rendered_groups.add(entry.merge_key)
                if len(group) > 1:
                    sources = ", ".join(f"{item.name} ({item.quantity})" for item in group)
                    merged_notes.append(f"{sources} -> {merged_item.name} ({merged_item.quantity})")
            else:
                if entry.rendered not in seen_rendered:
                    validated[category].append(entry.rendered)
                    seen_rendered.add(entry.rendered)

    result = ValidationResult(
        categories=validated,
        skipped=sorted(set(skipped)),
        merged=merged_notes,
        ambiguous=sorted(set(ambiguous)),
    )
    if use_ai:
        result.ai_review = build_codex_review(result)
    return result


def build_codex_review(result: ValidationResult) -> str:
    lines = [
        "# Revue IA Codex - liste d'epicerie",
        "",
        "Cette revue est preparee localement pour Codex. Elle ne modifie pas la liste.",
        "",
        "## Mandat pour Codex",
        "",
        "- Reperer les synonymes probables et doublons restants.",
        "- Proposer des regroupements d'emballage utiles pour l'epicerie.",
        "- Ne pas supprimer les achats recurrents.",
        "- Ne jamais ajouter de crustaces.",
        "- Ne pas modifier l'inventaire.",
        "",
        "## Fusions deterministes deja appliquees",
        "",
    ]
    lines.extend(f"- {item}" for item in result.merged) if result.merged else lines.append("- Aucune")
    lines.extend(["", "## Items ambigus a relire", ""])
    lines.extend(f"- {item}" for item in result.ambiguous) if result.ambiguous else lines.append("- Aucun")
    lines.extend(["", "## Liste validee", ""])
    for category in GROCERY_CATEGORIES:
        lines.append(f"### {category}")
        entries = result.categories.get(category, [])
        lines.extend(entries if entries else ["- Aucun achat"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_codex_review(result: ValidationResult, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.ai_review or build_codex_review(result), encoding="utf-8")
    return out
