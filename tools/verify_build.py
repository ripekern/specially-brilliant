#!/usr/bin/env python3
"""Fail the deploy if the built site is not internally consistent.

A subpath deploy is the easy thing to get quietly wrong: absolute links still
build fine, they just 404 once served. This crawls dist/ the way a browser would
and checks every internal link and asset actually resolves, so a regression is
caught in CI rather than by a visitor.

Usage:  python3 tools/verify_build.py [<expected-base-prefix>]

With no argument it checks a root build (base "/"). Pass a repository name to
check a project-page build, e.g. `verify_build.py specially-brilliant`.
"""

import re
import sys
from pathlib import Path

DIST = Path(__file__).resolve().parent.parent / "dist"
URL_ATTR = re.compile(r'(href|src)="(/[^"#?]*)"')

# Remote hosts a reader may legitimately be sent to; not our problem to verify.
EXTERNAL = ("//", "http://", "https://", "mailto:", "tel:", "bitcoincash:")


def main() -> int:
    if not DIST.is_dir():
        print("FAIL: dist/ does not exist — the build did not run")
        return 1

    prefix = f"/{sys.argv[1]}" if len(sys.argv) > 1 else ""

    pages = sorted(DIST.rglob("*.html"))
    if not pages:
        print("FAIL: dist/ contains no HTML")
        return 1

    dead_links: list[str] = []
    missing_assets: list[str] = []
    unprefixed: list[str] = []
    no_alt: list[str] = []
    no_h1: list[str] = []
    checked = 0

    for page in pages:
        html = page.read_text(errors="ignore")
        rel_page = page.relative_to(DIST).as_posix()

        headings = re.findall(r"<h([1-6])[ >]", html.split("<body>")[1] if "<body>" in html else html)
        if headings.count("1") != 1:
            no_h1.append(f"{rel_page} (h1 count: {headings.count('1')})")

        for attr, url in URL_ATTR.findall(html):
            if url.startswith(EXTERNAL):
                continue
            checked += 1
            if prefix and not url.startswith(prefix + "/") and url != prefix:
                unprefixed.append(f"{rel_page}: {attr}={url}")
                continue
            rel = url[len(prefix):] if prefix else url
            if not rel or rel == "/":
                continue
            candidates = (
                [DIST / rel.lstrip("/") / "index.html", DIST / rel.lstrip("/")]
                if attr == "href"
                else [DIST / rel.lstrip("/")]
            )
            if not any(c.exists() for c in candidates):
                (dead_links if attr == "href" else missing_assets).append(
                    f"{rel_page}: {attr}={url}"
                )

        for tag in re.findall(r"<img[^>]*>", html):
            if "alt=" not in tag:
                no_alt.append(rel_page)

    problems = {
        f"dead internal links ({len(dead_links)})": dead_links,
        f"missing assets ({len(missing_assets)})": missing_assets,
        f"unprefixed URLs for base '{prefix or '/'}' ({len(unprefixed)})": unprefixed,
        f"images without alt ({len(no_alt)})": sorted(set(no_alt)),
        f"pages without exactly one h1 ({len(no_h1)})": no_h1,
    }

    failed = False
    print(f"checked {len(pages)} pages, {checked} internal URLs, base '{prefix or '/'}'")
    for label, items in problems.items():
        if items:
            failed = True
            print(f"  FAIL  {label}")
            for item in items[:8]:
                print(f"          {item}")
            if len(items) > 8:
                print(f"          ... and {len(items) - 8} more")
        else:
            print(f"  ok    {label}")

    if failed:
        print("\nbuild verification FAILED")
        return 1
    print("\nbuild verification passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
