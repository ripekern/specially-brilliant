#!/usr/bin/env python3
"""Report every `TODO(owner)` placeholder still sitting in the content.

The service pages were expanded into a structure — scope, cadence, pricing,
FAQ — but the business facts behind them (prices, turnaround times, frequency
recommendations, guarantees) belong to Sven and were deliberately not invented.
Where one is missing the Markdown carries an HTML comment instead of a guess:

    <!-- TODO(owner): starting price for a standard single-story window wash -->

An HTML comment renders as nothing, so a page can look finished and still be
missing a number. This script is the thing that makes that visible: it lists
every placeholder, by file and line, so nothing ships half-answered by accident.

It is a report, not a gate — a non-zero exit would break `npm run build` on a
site that is otherwise fine to deploy. Run it before calling a page done.

Run:  python3 tools/check_todos.py
Exit:  0 clean, 1 placeholders remain
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "src" / "content"

MARKER = re.compile(r"TODO\((?P<who>[\w-]+)\)\s*:?\s*(?P<what>.*?)\s*(?:-->)?$")


def main() -> int:
    files = sorted(CONTENT.rglob("*.md"))
    found: list[tuple[Path, int, str, str]] = []

    for f in files:
        for n, line in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
            for m in MARKER.finditer(line):
                who, what = m.group("who"), m.group("what")
                what = re.sub(r"^(?:starting |typical |usual )", "", what)
                found.append((f, n, who, what))

    if not found:
        print(f"no TODO(owner) placeholders in {len(files)} content files")
        print("\nall owner facts are filled in")
        return 0

    by_who: dict[str, int] = {}
    for _, _, who, _ in found:
        by_who[who] = by_who.get(who, 0) + 1

    print(f"{len(found)} TODO placeholder(s) awaiting owner input\n")
    for who, count in sorted(by_who.items()):
        print(f"  {who}: {count}")
    print()

    for f, n, who, what in found:
        rel = f.relative_to(ROOT)
        print(f"  {rel}:{n}")
        print(f"      [{who}] {what or '(no note)'}")

    print("\nfill these in before treating the page as finished")
    return 1


if __name__ == "__main__":
    sys.exit(main())