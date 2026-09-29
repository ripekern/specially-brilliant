#!/usr/bin/env python3
"""Add editorial classification to exported Markdown frontmatter.

The WordPress export carries no notion of "this is a service page". It matters a
lot here: services get cards, a sidebar CTA, and a slot in the header; transactional
pages are hidden from navigation and noindexed. This writes that intent into each
file's frontmatter so the templates never have to guess from a slug.

Run:  python3 tools/classify.py
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "src" / "content" / "pages"
POSTS = ROOT / "src" / "content" / "posts"

# slug -> (type, order, noindex, tags)
CLASSIFY: dict[str, tuple[str, int, bool, list[str]]] = {
    # Service pages: the pages that earn money. Order sets the card grid sequence.
    "window-washing": ("service", 10, False, ["service", "exterior"]),
    "gutter-cleaning": ("service", 20, False, ["service", "exterior"]),
    "pressure-washing": ("service", 30, False, ["service", "exterior"]),
    "automobile-detailing": ("service", 40, False, ["service", "vehicle"]),
    "house-painting": ("service", 50, False, ["service", "exterior"]),
    "moss-removal": ("service", 60, False, ["service", "roof"]),

    # Core pages: the connective tissue. In the header or footer, indexable.
    "services": ("core", 10, False, []),
    "about-us": ("core", 20, False, []),
    "schedule": ("core", 30, False, []),
    "privacy-policy": ("core", 90, False, []),

    # Transactional: reached from a CTA or a payment link, never from search or nav.
    "schedule-page": ("transactional", 10, True, []),
    "pay-online": ("transactional", 20, True, []),
    "payment-success": ("transactional", 30, True, []),
    "fees": ("transactional", 40, True, []),
    "coldscript": ("transactional", 50, True, []),
    "lender": ("transactional", 60, True, []),
    "loan-vetting-worksheet": ("transactional", 70, True, []),

    # Side projects: unrelated to home services, kept but quarantined.
    "rewards-program": ("side-project", 10, False, ["bitcoin-cash"]),
    "bitcoin-cash-co-op": ("side-project", 20, True, ["bitcoin-cash"]),
}


def patch(path: Path, type_: str, order: int, noindex: bool, tags: list[str]) -> bool:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        print(f"  no frontmatter: {path.name}")
        return False

    fm = match.group(1)
    additions = [
        f"type: \"{type_}\"",
        f"order: {order}",
        f"noindex: {'true' if noindex else 'false'}",
    ]
    if tags:
        rendered = ", ".join(f'"{t}"' for t in tags)
        additions.append(f"tags: [{rendered}]")
    else:
        additions.append("tags: []")

    fm = re.sub(r"^type:.*$", "", fm, flags=re.M)
    fm = re.sub(r"^order:.*$", "", fm, flags=re.M)
    fm = re.sub(r"^noindex:.*$", "", fm, flags=re.M)
    fm = re.sub(r"^tags:.*$", "", fm, flags=re.M)
    fm = re.sub(r"\n{3,}", "\n", fm).rstrip()

    text = f"---\n{fm}\n" + "\n".join(additions) + f"\n---\n" + text[match.end():]
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    changed = 0
    unclassified: list[str] = []

    for path in sorted(PAGES.glob("*.md")):
        slug = path.stem
        rule = CLASSIFY.get(slug)
        if not rule:
            unclassified.append(f"pages/{slug}")
            continue
        changed += patch(path, *rule)
        print(f"  {slug:<32} {rule[0]}")

    for path in sorted(POSTS.glob("*.md")):
        changed += patch(path, "post", 100, False, ["blog"])
        print(f"  {path.stem:<32} post")

    if unclassified:
        print("\nUNCLASSIFIED (kept as 'core' by default, review these):")
        for item in unclassified:
            print(f"  {item}")

    print(f"\npatched {changed} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
