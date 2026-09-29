#!/usr/bin/env python3
"""Audit the palette: WCAG contrast for every colour pair the site actually uses.

Resolves the tokens in tokens.css for both the :root (light) values and the
prefers-color-scheme: dark overrides, then scores each real foreground/background
pair from the stylesheets.

    AA text      4.5:1   (normal body copy)
    AA large     3.0:1   (>=24px, or >=18.66px bold — headings and large buttons)
    AA non-text  3.0:1   (borders, icons, control edges)
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = (ROOT / "src/styles/tokens.css").read_text()


def resolve_tokens():
    """Return {mode: {token: hex}} for light and dark."""
    light, dark = {}, {}
    # :root block
    root = re.search(r":root\s*\{(.*?)\n\}", TOKENS, re.S).group(1)
    for name, val in re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{3,8})", root):
        light[name] = val.lower()
    # dark block only overrides; unset tokens keep their light value
    dm = re.search(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*:root\s*\{(.*?)\n\s*\}\s*\}", TOKENS, re.S)
    if not dm:
        raise SystemExit(
            "FAIL: no prefers-color-scheme:dark :root block found in tokens.css.\n"
            "Auditing light values twice silently would report dark mode as passing."
        )
    dark = dict(light)
    for name, val in re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{3,8})", dm.group(1)):
        dark[name] = val.lower()
    overrides = {k for k in dark if dark[k] != light.get(k)}
    if not overrides:
        raise SystemExit("FAIL: dark block parsed but changed no tokens — check the regex.")
    return {"light": light, "dark": dark}


def expand(hexval):
    h = hexval.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(hexval):
    def chan(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = expand(hexval)
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


# (label, fg token, bg token, minimum, where it is used)
PAIRS = [
    ("body copy",              "--ink-800",   "--white",      4.5, "base.css: body"),
    ("muted / meta text",      "--ink-600",   "--white",      4.5, "components: card text, faq body"),
    ("faintest text",          "--ink-500",   "--white",      4.5, "components: tagline, small print"),
    ("inline link",            "--text-brand","--white",      4.5, "base.css: a"),
    ("link hover",             "--text-brand-muted","--white",  4.5, "base.css: a:hover"),
    ("brand heading",          "--text-brand-strong","--white",3.0, "components: h2/h3, card titles"),
    ("card / nav CTA link",    "--text-brand","--white",      4.5, "components: .card__cta, .panel__list a"),
    ("primary button label",   "#ffffff",     "--brand-700",  4.5, "components: .btn--primary"),
    ("primary button hover",   "#ffffff",     "--brand-600",  4.5, "components: .btn--primary:hover"),
    ("accent button label",    "--brand-900", "--accent-500", 4.5, "components: .btn--accent"),
    ("accent button hover",    "--brand-900", "--accent-600", 4.5, "components: .btn--accent:hover"),
    ("ghost button label",     "--text-brand","--white",      4.5, "components: .btn--ghost"),
    ("ghost button border",    "--brand-500", "--white",      3.0, "components: .btn--ghost border"),
    ("hero body over gradient","#ffffff",     "--brand-800",  4.5, "components: .hero"),
    ("hero accent, darkest",   "--accent-500","--brand-900",  4.5, "components: .hero__eyebrow"),
    ("hero accent, mid",       "--accent-500","--brand-800",  4.5, "hero gradient midpoint"),
    ("hero accent, lightest",  "--accent-500","--brand-700",  4.5, "hero gradient end"),
    ("hero accent icon",       "--accent-500","--brand-700",  3.0, "components: .hero__proof-item svg"),
    ("tinted panel",           "--text-brand-strong","--brand-50", 4.5, "components: .btn--ghost:hover, .callout"),
    ("tinted panel link",      "--text-brand","--brand-50",  4.5, "components: callout links"),
    ("tinted panel strong",    "--text-brand-strong","--brand-100", 4.5, "components: .card__media alt panels"),
    ("feature strip",          "--ink-600",   "--ink-100",    4.5, "components: .stats band"),
    ("footer body",            "--footer-text","--footer-bg", 4.5, "components: .footer"),
    ("footer link",            "--footer-text","--footer-bg", 4.5, "components: .footer a"),
    ("cta band body",          "#ffffff",     "--brand-800",  4.5, "components: .cta-band"),
    ("panel on brand",         "--brand-300", "--brand-800",  4.5, "components: .panel--accent a"),
    ("success icon",           "--success-600","--white",     3.0, "components: .features svg"),
    ("success text",           "--success-600","--white",     4.5, "components: .pill--success"),
    ("focus ring",             "--brand-500", "--white",      3.0, "base.css: :focus-visible"),
]


def main():
    modes = resolve_tokens()
    rows = []
    for label, fg, bg, minimum, where in PAIRS:
        for mode, toks in modes.items():
            f = fg if fg.startswith("#") else toks.get(fg)
            b = bg if bg.startswith("#") else toks.get(bg)
            if not f or not b:
                continue
            r = ratio(f, b)
            rows.append((label, mode, fg, f, bg, b, r, minimum, where, r >= minimum))

    width = max(len(r[0]) for r in rows)
    for label, mode, fg, f, bg, b, r, minimum, where, ok in rows:
        flag = "PASS" if ok else "FAIL"
        print(f"{flag}  {label:<{width}}  {mode:<5}  {f} on {b}  {r:5.2f}:1  (needs {minimum})")

    fails = [r for r in rows if not r[9]]
    print(f"\n{len(rows) - len(fails)}/{len(rows)} pass, {len(fails)} failing")
    if fails:
        print("\nFailing pairs:")
        for label, mode, fg, f, bg, b, r, minimum, where, _ in fails:
            print(f"  [{mode}] {label}: {f} on {b} = {r:.2f}:1, needs {minimum} — {where}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
