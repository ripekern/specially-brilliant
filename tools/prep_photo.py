#!/usr/bin/env python3
"""Prepare a service photo for the prose column and the share card.

Every other image on the site is sized to its render slot, and the rules are
easy to get wrong by hand: a portrait phone photo rendered at full column width
takes over the whole screen, and an oversized file costs every visitor the bytes.
This applies the same conventions the rest of the images already follow.

- Landscape is kept and scaled to PROSE_WIDTH.
- Portrait is centre-cropped to LANDSCAPE_RATIO first, because a 2:3 photo in a
  wide prose column reads as broken rather than as a photo.
- Everything lands as WebP at QUALITY, with metadata stripped.

Usage:
    python3 tools/prep_photo.py house-painting-exterior.jpg
    python3 tools/prep_photo.py --ratio 1:1 --name house-painting-exterior shot.jpg

Prints the Markdown to paste into the page:

    ![alt text here](/images/content/house-painting-exterior.webp)
"""

import argparse
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "public" / "images" / "content"
OUT_URL = "/images/content"

# The prose column is roughly 49rem beside the sidebar and can reach the full
# container width on narrow layouts, so 1200px covers both without wasting bytes.
PROSE_WIDTH = 1200
# 4:3, the ratio the existing content photos were cropped to.
LANDSCAPE_RATIO = Fraction(4, 3)
QUALITY = 78

# A share card needs 1200x630 to avoid being letterboxed by the platforms, so a
# crop that already happens to be close to that is left alone.
OG_RATIO = Fraction(1200, 630)
OG_TOLERANCE = 0.06


def ratio_of(size: tuple[int, int]) -> float:
    w, h = size
    return w / h if h else 0.0


def run_magick(args: list[str]) -> None:
    if shutil.which("magick"):
        cmd = ["magick", *args]
    elif shutil.which("convert"):
        cmd = ["convert", *args]
    else:
        sys.exit("ImageMagick is required:  apt install imagemagick")
    subprocess.run(cmd, check=True)


def convert(src: Path, dest: Path, ratio: Fraction | None) -> tuple[int, int]:
    """Write dest from src, cropping to ratio first when the image is portrait.

    Returns the dimensions actually written, so the caller can declare them in
    frontmatter rather than restating the target. Cropping rounds, and the
    result is routinely a pixel or two off 1200x630.
    """
    before = dest.stat().st_size if dest.exists() else 0
    args: list[str] = [str(src)]
    w = h = 0

    if ratio is not None:
        with Image.open(src) as im:
            w, h = im.size
        target = float(ratio)
        if w < h and ratio_of((w, h)) < target:
            # Portrait and taller than the target: crop the height, keep the
            # subject, then scale. -gravity centre is what the existing photos
            # were cropped with.
            args += ["-gravity", "center", "-crop", f"{w}x{round(w / target)}+0+0", "+repage"]

    args += ["-resize", f"{PROSE_WIDTH}x", "-quality", str(QUALITY), "-strip", str(dest)]
    run_magick(args)

    after = dest.stat().st_size
    with Image.open(dest) as im:
        ow, oh = im.size
    print(f"  {dest.relative_to(ROOT)}  {w}x{h} -> {ow}x{oh}, {after / 1024:.0f} KB", end="")
    if before:
        print(f"  (was {before / 1024:.0f} KB)", end="")
    print()
    return ow, oh


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="photo to convert (a phone photo is fine)")
    ap.add_argument("--name", help="output name without extension (default: the source stem)")
    ap.add_argument("--ratio", help="crop to this ratio for wide banners, e.g. 1.91:1")
    ap.add_argument("--og", action="store_true",
                    help=f"also write a 1200x630 share card from the same photo")
    args = ap.parse_args()

    if not args.source.exists():
        sys.exit(f"no such file: {args.source}")

    name = args.name or args.source.stem
    name = "".join(c if c.isalnum() or c in "-_" else "-" for c in name).strip("-").lower()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ratio = Fraction(*map(int, args.ratio.split(":"))) if args.ratio else LANDSCAPE_RATIO

    print(f"\nProse image ({ratio.numerator}:{ratio.denominator}):")
    convert(args.source, OUT_DIR / f"{name}.webp", ratio)

    og_name = None
    og_size = None
    if args.og:
        with Image.open(args.source) as im:
            w, h = im.size
        current = ratio_of((w, h))
        if abs(current - float(OG_RATIO)) / float(OG_RATIO) < OG_TOLERANCE:
            print("\n  photo is already close to 1200x630; using it for both")
            og_name = name
        else:
            og_name = f"{name}-og"
            print("\nShare card (1200x630):")
            og_size = convert(args.source, OUT_DIR / f"{og_name}.jpg", OG_RATIO)

    print(f"\nPaste into the page:\n\n  ![describe what is actually shown](/images/content/{name}.webp)\n")
    if og_name and og_name != name and og_size:
        print("And add to the page frontmatter, with the dimensions it actually wrote:")
        print(f'\n  image: "/images/content/{og_name}.jpg"')
        print(f"  ogImageWidth: {og_size[0]}")
        print(f"  ogImageHeight: {og_size[1]}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())