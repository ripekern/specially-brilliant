#!/usr/bin/env python3
"""Normalise heading levels in the imported Markdown.

The WordPress export preserved whatever level each author happened to pick, which
produces outlines a screen reader cannot follow: a lone `h6` before an `h2`, a
body that starts at `h3`, and pages whose content repeats the `h1` the template
already renders.

This rewrites the body so the outline is valid, without touching content:

- levels are clamped to 2-4 (deeper than h4 is not meaningful for this content)
- no heading may skip a level relative to the one before it
- the shallowest heading in a file is pulled down to h2, since the layout owns h1

Idempotent: running it twice changes nothing.

Run:  python3 tools/normalize_headings.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "src" / "content"

MIN_LEVEL = 2
MAX_LEVEL = 4

HEADING = re.compile(r"^(#{1,6})(\s+)(.*)$", re.M)


def normalize(markdown: str) -> tuple[str, int]:
    """Rewrite heading levels in-place, returning the new text and a change count."""
    # Fenced code can contain '#' comment lines; skip rewriting inside it.
    in_fence = False
    out_lines = []
    for line in markdown.split("\n"):
        is_fence_line = line.lstrip().startswith("```")
        if is_fence_line:
            in_fence = not in_fence
        if in_fence or is_fence_line:
            out_lines.append((True, line))
            continue
        out_lines.append((False, line))

    current = 1
    changes = 0

    def repl(m: re.Match) -> str:
        nonlocal current, changes
        level = min(max(len(m.group(1)), MIN_LEVEL), MAX_LEVEL)
        level = min(level, current + 1)  # no skipping a level
        level = max(level, MIN_LEVEL)
        current = level
        hashes = "#" * level
        new = f"{hashes}{m.group(2)}{m.group(3)}"
        if new != m.group(0):
            changes += 1
        return new

    out = []
    for is_fence, line in out_lines:
        out.append(line if is_fence or not HEADING.match(line) else HEADING.sub(repl, line))

    return "\n".join(out), changes


def main() -> int:
    total = 0
    for f in sorted(CONTENT.rglob("*.md")):
        text = f.read_text(encoding="utf-8")
        parts = text.split("---\n", 2)
        if len(parts) < 3:
            print(f"  {f.relative_to(ROOT)}: no frontmatter, skipped")
            continue
        head, body = "---\n" + parts[1] + "---\n", parts[2]
        new_body, changes = normalize(body)
        if changes:
            f.write_text(head + new_body, encoding="utf-8")
            total += changes
            print(f"  {f.stem:<52} {changes} heading(s) adjusted")
    print(f"\n{total} headings adjusted across "
          f"{len(list(CONTENT.rglob('*.md')))} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
