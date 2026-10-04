#!/usr/bin/env python3
"""Fail the deploy if the built site is not internally consistent.

A subpath deploy is the easy thing to get quietly wrong: absolute links still
build fine, they just 404 once served. This crawls dist/ the way a browser would
and checks every internal link and asset actually resolves, so a regression is
caught in CI rather than by a visitor.

Usage:  python3 tools/verify_build.py [<expected-base-prefix>]

With no argument it checks a root build (base "/"). Pass a repository name to
check a project-page build, e.g. `verify_build.py specially-brilliant`.

Crawling dist/ catches what the Markdown cannot show: a broken link introduced by
a template, an absolute URL that forgets the deploy base, a page that lost its h1.
Three further rules can only be judged from the source, because they are about
what the content claims rather than what it renders, so they are checked against
the frontmatter as well.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
CONTENT = ROOT / "src" / "content"
URL_ATTR = re.compile(r'(href|src)="(/[^"#?]*)"')
IMG_TAG = re.compile(r"<img[^>]*>")
ALT_ATTR = re.compile(r'\balt="([^"]*)"')
FRONTMATTER = re.compile(r"\A---\n(?P<yaml>.*?)\n---\n", re.S)

# Remote hosts a reader may legitimately be sent to; not our problem to verify.
EXTERNAL = ("//", "http://", "https://", "mailto:", "tel:", "bitcoincash:")


def frontmatter(f: Path) -> dict[str, str]:
    """Read the flat `key: value` pairs from a page's frontmatter.

    Deliberately not a YAML parser: the checks below only need top-level scalars,
    and a real parse would mean a dependency plus failures on the nested `faq:`
    and `members:` blocks that are none of this script's business.
    """
    m = FRONTMATTER.match(f.read_text(encoding="utf-8"))
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group("yaml").split("\n"):
        if line[:1].isspace() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip().strip("\"'")
    return out


def check_frontmatter() -> list[tuple[str, str]]:
    """Rules about what a page claims, which the built HTML cannot disprove.

    - the slug is the URL segment, so it has to match the file it is served from
    - a custom share image must declare its dimensions in the same breath, or the
      platform reserves no space for it and the card renders letterboxed
    - a page that asks search engines to ignore it must not also be listed in the
      sitemap, which is the contradiction astro.config's EXCLUDE comment warns of
    """
    problems: list[tuple[str, str]] = []

    for f in sorted(CONTENT.rglob("*.md")):
        meta = frontmatter(f)
        if not meta:
            continue
        rel = f.relative_to(ROOT)

        if f.stem != "index" and meta.get("slug") and meta["slug"] != f.stem:
            problems.append((f"slug {meta['slug']!r} disagrees with filename {f.stem!r}", str(rel)))

        if meta.get("image") and not (meta.get("ogImageWidth") and meta.get("ogImageHeight")):
            problems.append(("custom share image with no ogImageWidth/ogImageHeight", str(rel)))

        if meta.get("noindex") == "true" and meta.get("slug"):
            sm = DIST / "sitemap-0.xml"
            if sm.is_file():
                listed = re.findall(r"<loc>[^<]*?/([^/<]+)/?</loc>", sm.read_text(encoding="utf-8"))
                if meta["slug"] in listed:
                    problems.append((f"noindex page is listed in the sitemap: /{meta['slug']}/", str(rel)))

    return problems


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
    empty_alt: list[str] = []
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

        for tag in IMG_TAG.findall(html):
            if "alt=" not in tag:
                no_alt.append(rel_page)
            elif ALT_ATTR.search(tag).group(1).strip() == "":
                # alt="" is how an image is marked decorative, and it is correct
                # whenever the meaning is already carried by nearby text or by an
                # aria-label on a wrapping link. So this is listed for review, not
                # failed: an empty alt that is *not* deliberate is invisible here.
                empty_alt.append(rel_page)

    frontmatter_problems = check_frontmatter()

    problems = {
        f"dead internal links ({len(dead_links)})": dead_links,
        f"missing assets ({len(missing_assets)})": missing_assets,
        f"unprefixed URLs for base '{prefix or '/'}' ({len(unprefixed)})": unprefixed,
        f"images without alt ({len(no_alt)})": sorted(set(no_alt)),
        f"pages without exactly one h1 ({len(no_h1)})": no_h1,
        f"frontmatter inconsistencies ({len(frontmatter_problems)})": frontmatter_problems,
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

    if empty_alt:
        pages = sorted(set(empty_alt))
        print(f"\n  note  images with alt=\"\" ({len(pages)} page(s)) -- review, not a failure")
        print("          alt=\"\" marks an image decorative, which is right when the meaning")
        print("          is already in nearby text or an aria-label. Confirm that is deliberate.")
        for page in pages[:8]:
            print(f"          {page}")
        if len(pages) > 8:
            print(f"          ... and {len(pages) - 8} more")

    print("\nbuild verification passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
