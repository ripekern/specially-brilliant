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

You never need to touch a `.astro` file to change what the site says.

| To change | Edit |
| --- | --- |
| Page copy | `src/content/pages/<slug>.md` |
| Blog post | `src/content/posts/<slug>.md` |
| Business details, phone, service areas | `src/data/site.json` |
| Service card image, label, blurb | `src/data/services.ts` |
| Colors, spacing, type scale | `src/styles/tokens.css` |

### Frontmatter

```yaml
---
title: "Window washing"        # rendered as the page H1 and <title>
slug: "window-washing"         # URL segment, must match the filename
wpId: 47                       # original WordPress ID, for reference
description: "..."             # meta description + page lede
date: "2023-01-06"
modified: "2026-05-09"
source: "https://speciallybrilliant.com/window-washing/"
type: "service"                 # service | core | transactional | side-project | post
order: 10                       # sort order; lower comes first
noindex: false                 # emits <meta name="robots" content="noindex, nofollow">
tags: ["service", "exterior"]
---
```

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

- **The six service pages are thin.** `window-washing`, `gutter-cleaning`,
  `pressure-washing`, `automobile-detailing`, `house-painting` and
  `moss-removal` each have one heading and three paragraphs, and no pricing, no
  FAQ, and no service-area detail. This is a ranking and conversion problem, and
  it is the highest-value content work outstanding.
- `coldscript` was dropped. The WordPress page is an empty `noindex` shell with
  no body text at all, so there was nothing to migrate. Delete it in WordPress.
- `pay-online` lost its WP Easy Pay form. Card details must be submitted to a
  payment processor, never stored in a static page, so the page now points to
  booking instead and shows the Bitcoin Cash address as copyable text.
- `fees` had its styled-div fee table flattened into headings by the importer.
  Rebuild it as a real `<table>` if the layout matters.
- AIOSEO titles/descriptions were written on the live site but have not been
  imported. `description` in the frontmatter is currently the only SEO copy; add
  `seoTitle`/`seoDescription` fields if you want the originals back.

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
