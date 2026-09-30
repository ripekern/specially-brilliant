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


VALUE = r"(#[0-9a-fA-F]{3,8}|var\(--[\w-]+\))"


def deref(tokens):
    """Follow var() aliases down to a concrete hex, dropping any that dangle.

    Several tokens are defined as aliases (--footer-bg: var(--ink-900)). Left as
    literal strings they score as unresolvable and the pair is silently skipped,
    which is how the whole light-mode footer went unaudited: --footer-bg and
    --footer-text are both aliases there, so every footer pair vanished from the
    light column and the audit reported a pass it never actually checked.
    """
    out = {}
    for name, val in tokens.items():
        seen = set()
        while val.startswith("var(") and val not in seen:
            seen.add(val)
            ref = re.fullmatch(r"var\((--[\w-]+)\)", val)
            if not ref or ref.group(1) not in tokens:
                val = None
                break
            val = tokens[ref.group(1)]
        if val and val.startswith("#"):
            out[name] = val
    return out


def resolve_tokens():
    """Return {mode: {token: hex}} for light and dark."""
    light, dark = {}, {}
    # :root block
    root = re.search(r":root\s*\{(.*?)\n\}", TOKENS, re.S).group(1)
    for name, val in re.findall(rf"(--[\w-]+):\s*{VALUE}", root):
        light[name] = val.lower()
    # dark block only overrides; unset tokens keep their light value
    dm = re.search(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*:root\s*\{(.*?)\n\s*\}\s*\}", TOKENS, re.S)
    if not dm:
        raise SystemExit(
            "FAIL: no prefers-color-scheme:dark :root block found in tokens.css.\n"
            "Auditing light values twice silently would report dark mode as passing."
        )
    dark = dict(light)
    for name, val in re.findall(rf"(--[\w-]+):\s*{VALUE}", dm.group(1)):
        dark[name] = val.lower()
    overrides = {k for k in dark if dark[k] != light.get(k)}
    if not overrides:
        raise SystemExit("FAIL: dark block parsed but changed no tokens — check the regex.")
    # Dereference per mode, so an alias picks up that mode's value of its target.
    light, dark = deref(light), deref(dark)
    return {"light": light, "dark": dark}


def expand(hexval):
    h = hexval.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def composite(fg, alpha, bg):
    """Flatten a translucent foreground onto an opaque background.

    Several rules use color-mix(in srgb, <colour> N%, transparent), which puts
    real opacity between the text and the surface behind it. Scoring the raw
    hex would credit the text with contrast it does not have, so resolve the
    blend first and score the result.
    """
    f, b = expand(fg), expand(bg)
    return "#%02x%02x%02x" % tuple(
        round(alpha * cf + (1 - alpha) * cb) for cf, cb in zip(f, b)
    )


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


# Comments are stripped before parsing: a rule introduced by a comment block
# would otherwise carry the comment text into its selector prelude and never
# match. Grouped selectors (".a,\n.b {") are split and matched member-wise, so
# one rule can serve several surfaces.
COMPONENTS = re.sub(r"/\*.*?\*/", "", (ROOT / "src/styles/components.css").read_text(), flags=re.S)


def rule_value(selector, prop):
    """The value a selector last sets for a property, or None if it sets none.

    Scans rule blocks rather than searching for the selector text, so a bare
    ".btn--ghost" cannot match the ".cta-band .btn--ghost" that follows it.
    """
    val = None
    for m in re.finditer(r"(?m)^([^{}]+)\{([^}]*)\}", COMPONENTS):
        if selector not in [s.strip() for s in m.group(1).split(",")]:
            continue
        d = re.search(rf"(?m)^\s*{prop}\s*:\s*([^;]+);", m.group(2))
        if d:
            val = d.group(1).strip()
    return val


def to_spec(value, surface):
    """Rewrite a raw CSS colour value into the spec syntax resolve() reads.

    color-mix(in srgb, <colour> N%, transparent) becomes <colour>@N/<surface>,
    since the layer is laid over the surface it is being scored against.
    """
    v = value.strip()
    mix = re.fullmatch(r"color-mix\(in srgb,\s*(.+?)\s+(\d+)%\s*,\s*transparent\)", v)
    if mix:
        return f"{mix.group(1)}@{mix.group(2)}/{surface}"
    ref = re.fullmatch(r"var\((--[\w-]+)\)", v)
    if ref:
        return ref.group(1)
    return v


# Text and edges that are only correct because of where they sit.
#
# A pair written as ("#ffffff", "--brand-800") scores the value, not the rule: it
# keeps reporting 11.8:1 after someone deletes the override that produces it, so
# it cannot fail. These read the declaration out of components.css instead, and
# fall back to the base selector when the override is gone -- which is what the
# browser actually renders, and what puts the label back to 1.39:1.
#
# (label, surface, base selector, scoped selector, property, minimum, where)
PLACEMENTS = [
    ("cta band heading",  "--brand-800", None,                    ".cta-band h2",              "color",        4.5, "components: .cta-band h2"),
    ("cta band body",     "--brand-800", None,                    ".cta-band p",               "color",        4.5, "components: .cta-band p (color-mix 85%)"),
    ("cta band ghost label",  "--brand-800", ".btn--ghost",      ".cta-band .btn--ghost",     "color",        4.5, "components: .cta-band .btn--ghost label"),
    ("cta band ghost border", "--brand-800", ".btn--ghost",      ".cta-band .btn--ghost",     "border-color", 3.0, "components: .cta-band .btn--ghost border"),
    ("cta band ghost hover",  "--brand-800", ".btn--ghost",      ".cta-band .btn--ghost:hover", "color",      4.5, "components: .cta-band .btn--ghost:hover label"),
    # The accent panel is the same brand-800 surface carrying the same button,
    # which is why both bands share one rule. It was previously an inline style
    # in SidebarCta.astro, which no static check could see.
    ("accent panel ghost label",  "--brand-800", ".btn--ghost",   ".panel--accent .btn--ghost",     "color",        4.5, "components: .panel--accent .btn--ghost label"),
    ("accent panel ghost border", "--brand-800", ".btn--ghost",   ".panel--accent .btn--ghost",     "border-color", 3.0, "components: .panel--accent .btn--ghost border"),
    ("accent panel ghost hover",  "--brand-800", ".btn--ghost",   ".panel--accent .btn--ghost:hover", "color",      4.5, "components: .panel--accent .btn--ghost:hover label"),
]
# The hover *background* is deliberately not scored. A 14% tint over the band is
# a state hint, not the boundary that identifies the control, and WCAG 1.4.11
# does not ask it for 3:1 -- the border pair above is what carries that.


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
    ("footer legal",           "--footer-text-muted","--footer-bg", 4.5, "components: .footer__legal"),
    ("panel on brand",         "--brand-300", "--brand-800",  4.5, "components: .panel--accent a"),
    ("success icon",           "--success-600","--white",     3.0, "components: .features svg"),
    ("success text",           "--success-600","--white",     4.5, "components: .pill--success"),
    ("focus ring",             "--brand-500", "--white",      3.0, "base.css: :focus-visible"),
    # Fixed light surfaces. The payment card and the Bitcoin Cash chips keep a
    # white background whatever the page is doing, so their text is pinned to a
    # literal too -- a token would invert with the page and put near-white text
    # on white. Scored with literals because that is what ships.
    ("payment card address",   "#0f172a",    "#ffffff",     4.5, "components: .pay-card__addr on .pay-card"),
    ("payment card label",     "#475569",    "#ffffff",     4.5, "components: .pay-card__label on .pay-card"),
]


def resolve(spec, toks, what=""):
    """Resolve a colour spec to a flat hex, or None if it cannot be resolved.

    A spec is a token name or a hex literal, optionally with an alpha suffix:

        #2280c4          an opaque colour
        #ffffff@60       that colour at 60% opacity (the color-mix form)
        #ffffff@14/--brand-800
                         14% white laid over the brand-800 surface

    The backdrop is written out rather than inferred from the other side of the
    pair. A hover background does not sit on the label, it sits on the surface
    behind it, and guessing wrong scores a pair against the wrong pixels.
    """
    backdrop = None
    if "/" in spec:
        spec, _, backdrop = spec.partition("/")

    alpha = 1.0
    if "@" in spec:
        spec, _, pct = spec.partition("@")
        alpha = int(pct) / 100

    val = spec if spec.startswith("#") else toks.get(spec)
    if not val:
        return None
    if alpha == 1:
        return val

    if backdrop is None:
        raise SystemExit(
            f"FAIL: {what or spec!r} is {int(alpha * 100)}% opaque but names no backdrop.\n"
            "Write it as <colour>@<pct>/<surface> so the blend lands on the right pixels."
        )
    under = resolve(backdrop, toks, what=spec)
    if not under:
        raise SystemExit(f"FAIL: backdrop {backdrop!r} in {spec!r} is not a colour this audit knows.")
    return composite(val, alpha, under)


def main():
    modes = resolve_tokens()
    rows = []
    for label, fg, bg, minimum, where in PAIRS:
        for mode, toks in modes.items():
            f = resolve(fg, toks, what=f"{label} fg")
            b = resolve(bg, toks, what=f"{label} bg")
            if not f or not b:
                continue
            r = ratio(f, b)
            rows.append((label, mode, fg, f, bg, b, r, minimum, where, r >= minimum))

    # Placements score the rule as written, so a deleted override fails.
    for label, surface, base, scoped, prop, minimum, where in PLACEMENTS:
        raw = rule_value(scoped, prop) or (rule_value(base, prop) if base else None)
        if not raw:
            print(
                f"FAIL  {label:<{max(len(r[0]) for r in rows)}}  --    "
                f"no {prop} found for {scoped} in components.css"
            )
            rows.append((label, "both", f"{scoped} {{{prop}}}", "?", surface, "?", 0.0,
                         minimum, where, False))
            continue
        spec = to_spec(raw, surface)
        for mode, toks in modes.items():
            f = resolve(spec, toks, what=f"{label} fg")
            b = resolve(surface, toks, what=f"{label} bg")
            if not f or not b:
                continue
            r = ratio(f, b)
            rows.append((label, mode, spec, f, surface, b, r, minimum, where, r >= minimum))

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
