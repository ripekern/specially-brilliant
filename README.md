# Specially Brilliant

Static Astro rebuild of `speciallybrilliant.com`. Content and presentation are
fully separated: every page is a Markdown file with structured frontmatter, and
the templates never hardcode business copy.

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # -> dist/, a folder of static files
npm run preview
```

`dist/` is fully static. It can be served by nginx, Caddy, Netlify, Cloudflare
Pages, or any plain file server. Nothing here needs WordPress, PHP, or a database.

## Editing content

For every page except the homepage, you never need to touch a `.astro` file to
change what the site says.

| To change | Edit |
| --- | --- |
| Page copy | `src/content/pages/<slug>.md` |
| Blog post | `src/content/posts/<slug>.md` |
| Business details, phone, service areas | `src/data/site.json` |
| Service card image, label, blurb | `src/data/services.ts` |
| Colors, spacing, type scale | `src/styles/tokens.css` |

**The homepage is the exception.** `src/pages/index.astro` builds it directly from
`site.json` and `services.ts`; there is no `home.md`, because a Markdown file is
not the source of anything on that page. `[slug].astro` reserves `home` and
`services` for the same reason — both have hand-built routes that would otherwise
collide. Homepage copy therefore lives in the template, and changing it means
editing `index.astro`.

### Frontmatter

```yaml
---
title: "Window washing"        # rendered as the page H1
slug: "window-washing"         # URL segment, must match the filename
wpId: 47                       # original WordPress ID, for reference
description: "..."             # meta description + page lede
seoTitle: "..."                # optional; replaces the H1 in <title> only
seoDescription: "..."          # optional; replaces the meta description only
image: "/images/og-page.jpg"   # optional; share card image, 1200x630
ogImageWidth: 1200             # required with a custom `image`
ogImageHeight: 630
date: "2023-01-06"
modified: "2026-05-09"
source: "https://speciallybrilliant.com/window-washing/"
type: "service"                 # service | core | transactional | side-project | post
order: 10                       # sort order; lower comes first
noindex: false                 # emits <meta name="robots" content="noindex, nofollow">
tags: ["service", "exterior"]
faq:                           # optional; rendered as <details> + FAQPage schema
  - q: "How often should gutters be cleaned?"
    a: "Twice a year, before spring growth and again in late autumn."
---
```

`seoTitle` and `seoDescription` exist so the search copy can differ from the
visible copy. `title` and `description` are what a reader sees; the `seo*`
fields, when present, replace only what goes to search engines and social cards.
That is what lets a vague headline carry a specific keyword — "Some easy ways to
maintain your home" is a fine H1 and a poor `<title>`.

`seoTitle` is the page-name half of the tag. `Base.astro` appends
`| Specially Brilliant` to it, so leave the brand out — and keep the whole
result near 60 characters, which is roughly what a desktop search result shows
before it truncates.

A custom `image` should be 1200x630. Platforms reserve share-card layout space
from `og:image:width`/`og:image:height`, so the two must be declared alongside it
or the card renders letterboxed or cropped. Without one, `og-default.png` is used.

`faq` is a list of question/answer pairs. It is held as data rather than Markdown
so the visible accordion and the `FAQPage` JSON-LD render from one array and
cannot drift — marking up a question that is not visible on the page is how a
rich result gets revoked.

`members` lists the businesses in the Bitcoin Cash co-op. Same reasoning: the
template renders the card, the `tel:` link and the `Organization` JSON-LD from
one array, so a member cannot be listed visibly without being declared, or the
reverse. Adding a business is a frontmatter edit on
`src/content/pages/bitcoin-cash-co-op.md`.

### Placeholders for facts the owner has not supplied

Service pages carry the structure and the reasoning, but the business facts —
prices, recurring-plan discounts, repaint intervals, product brands — belong to
Sven and were deliberately left blank rather than invented. Each gap is an HTML
comment, which renders as nothing:

```markdown
<!-- TODO(owner): whether you offer a recurring seasonal plan, and at what discount -->
```

That is invisible on the rendered page, so `tools/check_todos.py` exists to make
it visible:

```bash
npm run content:todos   # lists every placeholder by file and line
```

Run it before calling a page finished. It reports rather than gates, so an
unfilled placeholder will not break a deploy — but a page can otherwise look
complete while missing a number.

### Adding a photo to a service page

Six of the eight content photos are real shots of this business's own work.
`/house-painting/` and `/moss-removal/` have none.

Stock was tried and rejected. Openverse, Pexels and Unsplash were all searched
under commercial-use licences, and what is available is either snapshot-quality
interior DIY or Habitat for Humanity volunteer crews — a group on ladders with
buckets, on a site for a solo owner-operator. Scrappy photos read worse than no
photo, so these two pages stay imageless rather than carry something that
undercuts the four services that do have good ones. Free-licence photography of
this trade is thin because trades photograph their own work for their own
marketing rather than publishing it.

Take a photo on a phone and let the tool do the sizing:

```bash
npm run content:photo -- --name house-painting-exterior painting.jpg
npm run content:photo -- --name roof-moss-removal --og moss.jpg
```

The tool keeps landscape photos, centre-crops portrait to 4:3 so they do not fill
the whole prose column, writes WebP at 1200px, and prints the Markdown to paste in
plus the frontmatter for a share card. Add `--og` for a page that should also get
its own share image; `--og` always produces an exact 1200x630, cover-cropped
rather than letterboxed, and the dimensions it prints are the ones it actually
wrote.

**Shot list**

- `house-painting-exterior` — a finished exterior wall or trim run, with enough
  context to read as a house. Straight-on, daylight, no ladder or scaffold in shot.
- `roof-moss-removal` — the roof surface with the mat still on it, or mid-job
  with cleared shingles showing next to it. The contrast between the two is the
  whole argument the page makes, so a shot showing both is worth more than a
  close-up.
- Both: landscape if possible, nothing identifying in frame (no house numbers, no
  client faces, no street names), and no competitor branding.
- Alt text must describe what is actually in the frame, not what the service is.
  `verify_build.py` fails on an empty `alt`, and a screen reader should hear what a
  sighted visitor sees.

`type` drives real behaviour, not just labels:

- **`service`** — gets a card, a header nav slot, and a sidebar CTA.
- **`core`** — linked from the header or footer, indexable.
- **`transactional`** — reachable only via direct link, `noindex`, excluded
  from the sitemap. Payment and lending pages.
- **`side-project`** — unrelated ventures kept for completeness.
- **`post`** — appears under `/journal/`, excluded from the header nav.

## Content pipeline

The `tools/` scripts are for importing from WordPress, not for normal editing.
Re-running `content:convert` **overwrites** hand-edited Markdown, so only run it
when deliberately re-importing.

```bash
npm run content:convert   # _raw/*.json  -> Markdown + frontmatter
npm run content:classify  # apply the type/order/noindex map
npm run content:media     # download + WebP-convert images, rewrite references
npm run content:headings  # normalise the heading outline (idempotent)
npm run content:todos     # list TODO(owner) facts still needed from Sven
```

`_raw/` holds the untouched WordPress REST export and is the recovery path: if
content is ever lost, re-run the pipeline from it.

## Design

Provisional, and deliberately separate from content. Tokens live in
`src/styles/tokens.css`; change the palette there and every page follows.

- Type: Fraunces (display) + Inter (body), self-hosted by Google Fonts
- Color: deep blue with an amber accent
- Dark mode follows `prefers-color-scheme`
- Respects `prefers-reduced-motion`
- Keyboard-visible focus, skip link, semantic landmarks

## Before this goes live

Contact details were recovered from the exported content, not from WordPress
settings, and are worth a quick confirmation:

- `src/data/site.json` → `phone` `+15099035116` and `email`
  `sven@speciallybrilliant.com` were found in `lender.md` and
  `bitcoin-cash-co-op.md`, where they appear consistently. Confirm them anyway.
- No Facebook URL could be found, so `social` is omitted entirely rather than
  guessed.
- `owner` reads "Sven Bergman"; the legal page spells it differently. Check which
  is correct for public use.
- `url` is the old domain. Update it if the site moves — it drives canonicals,
  the sitemap, and Open Graph tags.

Content gaps that came from WordPress, not from the import:

- **The six service pages were expanded** to roughly 800–1,250 words each with an
  urgency-led opening, a scope list, a cadence section, service-area coverage, a
  price-lock section and 6–10 FAQs. The original prose is preserved under the new
  sections. Owner-supplied facts now in place: average prices (window washing
  ~$119, gutter cleaning ~$150, auto detailing ~$180), a multi-year price lock on
  the five fixed-price services, moss retreatment intervals, repaint intervals by
  surface, and Sherwin-Williams / Benjamin Moore as the paint.
- `coldscript` was dropped. The WordPress page is an empty `noindex` shell with
  no body text at all, so there was nothing to migrate. Delete it in WordPress.
- `pay-online` lost its WP Easy Pay form. Card details must be submitted to a
  payment processor, never stored in a static page, so the page now points to
  booking instead and shows the Bitcoin Cash address as copyable text.
- `fees` had its styled-div fee table flattened into headings by the importer.
  Rebuild it as a real `<table>` if the layout matters.
- AIOSEO titles/descriptions were written on the live site but have not been
  imported. `seoTitle`/`seoDescription` frontmatter fields are the path back —
  they override the `<title>` and meta description without changing the visible
  H1 and lede. All three posts have a `seoTitle` set.

## Layout

```
src/
  components/     Header, Footer, ServiceCard, SidebarCta
  content/        pages/ and posts/  <- the editable content
  data/           site.json (business facts), services.ts (card presentation)
  layouts/        Base.astro  <- <head>, SEO, JSON-LD, header/footer
  lib/            content.ts  <- collection queries used by every template
  pages/          routes: index, [slug], services/, journal/, 404
  styles/         tokens.css, base.css, components.css
public/images/    images, converted to WebP and sized to their render slot
tools/            one-off import scripts
_raw/             verbatim WordPress export
```
