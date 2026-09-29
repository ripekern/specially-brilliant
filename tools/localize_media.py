#!/usr/bin/env python3
"""Pull WordPress-hosted content images into the repo and rewrite the references.

A static site that still hotlinks /wp-content/ is not static: it breaks the day
WordPress goes away, and it makes the old host a hard dependency for every page
load. This downloads each unique image once, converts it to WebP, and rewrites
every Markdown reference to a local path.

Third-party images (affiliate trackers, CDNs) are left remote on purpose and
reported, so a human decides whether they belong.

Run:  python3 tools/localize_media.py
"""

import re
import subprocess
import sys
import urllib.parse
from collections import defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "src" / "content"
OUT_DIR = ROOT / "public" / "images" / "content"
OUT_URL = "/images/content"

# Only our own uploads get localized. Anything else stays as-is.
OWN_HOSTS = {"speciallybrilliant.com", "www.speciallybrilliant.com"}

MAX_EDGE = 1400
QUALITY = 80

IMAGE_MD = re.compile(r"(!\[[^\]]*\]\()((?:https?:)?//[^)\s]+)(\))")


def slugify(url: str) -> str:
    """Derive a stable, collision-free local filename from the remote URL."""
    path = urllib.parse.urlparse(url).path
    name = Path(urllib.parse.unquote(path)).stem
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    # WordPress appends -1024x683 style size hints; strip them so the same photo
    # referenced at two sizes collapses to one file.
    safe = re.sub(r"-\d{2,4}x\d{2,4}$", "", safe)
    return safe or "image"


def unique_name(slug: str, used: set[str]) -> str:
    name, n = slug, 2
    while name in used:
        name, n = f"{slug}-{n}", n + 1
    used.add(name)
    return name


def download(url: str, dest: Path) -> bool:
    cmd = ["curl", "-sL", "--fail", "--max-time", "60", "-o", str(dest), url]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0 and dest.exists() and dest.stat().st_size > 0


def convert(src: Path, dest: Path) -> int:
    """Downscale to a sane max edge and write WebP. Returns output size."""
    im = Image.open(src)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    if max(im.size) > MAX_EDGE:
        im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    im.save(dest, "WEBP", quality=QUALITY, method=6)
    return dest.stat().st_size


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(CONTENT.rglob("*.md"))
    url_map: dict[str, str] = {}
    external: dict[str, list[str]] = defaultdict(list)
    used: set[str] = set()
    before_total = 0
    after_total = 0

    for f in files:
        text = f.read_text(encoding="utf-8")
        for m in IMAGE_MD.finditer(text):
            url = m.group(2)
            if url.startswith("//"):
                url = "https:" + url
            host = urllib.parse.urlparse(url).netloc
            if host not in OWN_HOSTS:
                external[host].append(f.relative_to(CONTENT).as_posix())

    todo = []
    for f in files:
        for m in IMAGE_MD.finditer(f.read_text(encoding="utf-8")):
            raw = m.group(2)
            url = "https:" + raw if raw.startswith("//") else raw
            if urllib.parse.urlparse(url).netloc in OWN_HOSTS and url not in url_map:
                todo.append(url)

    print(f"localizing {len(todo)} unique images\n")
    tmp = OUT_DIR / ".tmp"
    tmp.mkdir(exist_ok=True)

    for i, url in enumerate(todo, 1):
        name = unique_name(slugify(url), used)
        raw = tmp / f"{name}.src"
        if not download(url, raw):
            print(f"  [{i}/{len(todo)}] FAILED {url}")
            raw.unlink(missing_ok=True)
            continue
        before_total += raw.stat().st_size
        dest = OUT_DIR / f"{name}.webp"
        try:
            after_total += convert(raw, dest)
        except Exception as exc:  # noqa: BLE001 - report and keep going
            print(f"  [{i}/{len(todo)}] FAILED to convert {url}: {exc}")
            raw.unlink(missing_ok=True)
            dest.unlink(missing_ok=True)
            continue
        raw.unlink(missing_ok=True)
        url_map[url] = f"{OUT_URL}/{name}.webp"
        print(f"  [{i}/{len(todo)}] {name}.webp  {dest.stat().st_size // 1024} KB")

    # Rewrite the Markdown references.
    rewritten = 0
    for f in files:
        text = original = f.read_text(encoding="utf-8")

        def sub(m):
            raw = m.group(2)
            url = "https:" + raw if raw.startswith("//") else raw
            local = url_map.get(url)
            return f"{m.group(1)}{local or raw}{m.group(3)}"

        text = IMAGE_MD.sub(sub, text)
        if text != original:
            f.write_text(text, encoding="utf-8")
            rewritten += 1

    for leftover in tmp.glob("*"):
        leftover.unlink()
    tmp.rmdir()

    print(f"\nrewrote {rewritten} files")
    if before_total:
        print(
            f"images: {before_total // 1024} KB -> {after_total // 1024} KB "
            f"({100 - after_total * 100 // before_total}% smaller)"
        )
    if external:
        print("\nleft remote on purpose (third-party, review these):")
        for host, where in external.items():
            print(f"  {host}: {len(where)} refs in {sorted(set(where))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
