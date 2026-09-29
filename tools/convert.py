#!/usr/bin/env python3
"""Convert WordPress REST block-editor HTML into clean Markdown + YAML frontmatter.

The REST API strips the `<!-- wp: -->` block markers, leaving semantic HTML whose
presentation is carried in `class` and `style` attributes. Both are discarded: the
design belongs in the stylesheet, the content belongs in Markdown.

Run from the repo root:  python3 tools/convert.py
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "_raw"
OUT = ROOT / "src" / "content"

# Blocks that exist only to carry layout. Their children are kept, the wrapper goes.
LAYOUT_BLOCKS = {
    "wp-block-group", "wp-block-cover", "wp-block-column", "wp-block-columns",
    "wp-block-spacer", "wp-block-buttons", "wp-block-button", "wp-block-separator",
    "wp-block-gallery", "wp-block-image", "wp-block-embed", "wp-block-html",
    "wp-block-table", "wp-block-template-part",
}

DROP_ENTIRELY = {"script", "style", "noscript", "iframe", "form"}

TAG_RE = re.compile(r"<(/?)([a-zA-Z0-9]+)([^>]*?)(/?)>", re.S)
ATTR_RE = re.compile(r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*"([^"]*)"')


def strip_attrs(attr_text: str) -> dict:
    return {k.lower(): v for k, v in ATTR_RE.findall(attr_text or "")}


def unwrap(fragment: str) -> str:
    """Drop layout-only wrapper divs/spacers/buttons, keeping their inner content."""
    for cls in sorted(LAYOUT_BLOCKS, key=len, reverse=True):
        # <div class="wp-block-spacer"></div> and self-closing forms
        fragment = re.sub(
            rf'<(\w+)[^>]*class="[^"]*\b{re.escape(cls)}\b[^"]*"[^>]*/>', "", fragment
        )
        # paired wrappers -> keep the contents
        fragment = re.sub(
            rf'<(\w+)[^>]*class="[^"]*\b{re.escape(cls)}\b[^"]*"[^>]*>(.*?)</\1>',
            r"\2", fragment, flags=re.S,
        )
    return fragment


def inline(text: str) -> str:
    """Normalise inline formatting to Markdown."""
    text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.S | re.I)
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.S | re.I)
    text = re.sub(r"<em>(.*?)</em>", r"*\1*", text, flags=re.S | re.I)
    text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return text


def slug_to_filename(slug: str, is_page: bool) -> Path:
    folder = OUT / ("pages" if is_page else "posts")
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{slug}.md"


def yaml_str(value: str) -> str:
    """Quote a YAML scalar safely."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def frontmatter(fields: dict) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {yaml_str(str(item))}")
        else:
            lines.append(f"{key}: {yaml_str(str(value))}")
    lines.append("---")
    return "\n".join(lines)


def convert_html(source: str) -> str:
    """Block-level conversion: headings, lists, images, paragraphs, then inline."""
    text = source
    for tag in DROP_ENTIRELY:
        text = re.sub(rf"<{tag}\b.*?</{tag}>", "", text, flags=re.S | re.I)
        text = re.sub(rf"<{tag}\b[^>]*/?>", "", text, flags=re.I)

    # images: keep src + alt, drop everything else
    def img_sub(match: re.Match) -> str:
        attrs = strip_attrs(match.group(0))
        src = attrs.get("src", "")
        alt = attrs.get("alt", "").strip()
        if not src or src.startswith("data:"):
            return ""
        return f"\n![{alt}]({src})\n"

    text = re.sub(r"<img[^>]*>", img_sub, text, flags=re.S | re.I)

    # links
    text = re.sub(
        r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
        lambda m: f"[{inline(m.group(2)).strip()}]({m.group(1)})",
        text, flags=re.S | re.I,
    )

    text = unwrap(text)

    # headings
    for level in range(1, 7):
        text = re.sub(
            rf"<h{level}\b[^>]*>(.*?)</h{level}>",
            lambda m, l=level: f"\n\n{'#' * l} {inline(m.group(1)).strip()}\n\n",
            text, flags=re.S | re.I,
        )

    # lists (ul/ol, one level is all this site uses)
    def list_sub(match: re.Match) -> str:
        body = match.group(1)
        item_re = re.compile(r"<li\b[^>]*>(.*?)</li>", re.S | re.I)
        items = [inline(m).strip() for m in item_re.findall(body)]
        return "\n" + "\n".join(f"- {i}" for i in items if i) + "\n"

    text = re.sub(r"<ul\b[^>]*>(.*?)</ul>", list_sub, text, flags=re.S | re.I)
    text = re.sub(r"<ol\b[^>]*>(.*?)</ol>", list_sub, text, flags=re.S | re.I)

    # tables -> simple pipe tables
    def table_sub(match: re.Match) -> str:
        rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", match.group(0), re.S | re.I)
        out = []
        for row in rows:
            cells = [inline(c).strip() for c in re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", row, re.S | re.I)]
            if any(cells):
                out.append("| " + " | ".join(cells) + " |")
        if not out:
            return ""
        if len(out) > 1:
            out.insert(1, "| " + " | ".join("---" for _ in out[0].split("|")[1:-1]) + " |")
        return "\n" + "\n".join(out) + "\n"

    text = re.sub(r"<table\b.*?</table>", table_sub, text, flags=re.S | re.I)

    # paragraphs
    text = re.sub(r"<p\b[^>]*>(.*?)</p>", lambda m: f"\n{inline(m.group(1))}\n", text, flags=re.S | re.I)
    # anything left
    text = inline(text)

    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def main() -> int:
    if not RAW.exists():
        print(f"error: no _raw directory at {RAW}", file=sys.stderr)
        return 1

    aios = json.loads((RAW / "aioseo.json").read_text()) if (RAW / "aioseo.json").exists() else {}
    counts = {"pages": 0, "posts": 0}

    for kind in ("pages", "posts"):
        source = RAW / f"{kind}.json"
        if not source.exists():
            print(f"warning: {source} missing, skipping", file=sys.stderr)
            continue
        for item in json.loads(source.read_text()):
            slug = item["slug"]
            if not slug:
                continue
            body = convert_html(item["content"]["rendered"])
            if not body.strip():
                print(f"  skip (empty): {kind}/{slug}")
                continue
            seo = aios.get(str(item["id"]), {})
            fields = {
                "title": html.unescape(item["title"]["rendered"] or slug),
                "slug": slug,
                "wpId": item["id"],
                "description": seo.get("description"),
                "date": (item.get("date") or "")[:10],
                "modified": (item.get("modified") or "")[:10],
                "source": item.get("link", ""),
            }
            path = slug_to_filename(slug, kind == "pages")
            path.write_text(frontmatter(fields) + "\n" + body, encoding="utf-8")
            counts[kind] += 1
            print(f"  wrote {path.relative_to(ROOT)}  ({len(body)} chars)")

    print(f"\ndone: {counts['pages']} pages, {counts['posts']} posts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
