/**
 * Prefix root-absolute URLs that come from Markdown content.
 *
 * Templates route through `withBase()`, but Astro does not apply the `base`
 * setting to URLs authored inside Markdown, nor to files served from `public/`.
 * On a subpath deploy (a GitHub project page at /specially-brilliant/) every
 * content image and in-body link would otherwise 404.
 *
 * Rewriting in the tree keeps content authors writing plain `/images/foo.webp`,
 * with no base-path knowledge leaking into the Markdown itself.
 */

const ATTRS = ["src", "href", "poster", "srcset"];

/**
 * Raw HTML written straight into Markdown does not arrive as element nodes --
 * Astro passes it through as `raw` nodes -- so the element walk below never sees
 * it and its root-absolute URLs would 404 on a subpath deploy. This matches the
 * same attributes inside a raw node's text.
 *
 * Only attribute positions are rewritten, never body text, and only paths that
 * are genuinely root-absolute.
 */
const RAW_ATTR = /(\s)(src|href|poster|srcset)(\s*=\s*)(["'])\/(?!\/)/g;

function prefixRawAttributes(value, base) {
  return value.replace(RAW_ATTR, (match, lead, attr, eq, quote) => {
    // srcset is a comma-separated candidate list, so each candidate is prefixed
    // individually rather than the whole string.
    if (attr === "srcset") {
      const list = match
        .slice(match.indexOf(quote) + 1, match.lastIndexOf(quote))
        .split(",")
        .map((c) => {
          const t = c.trim();
          if (!t.startsWith("/") || t.startsWith("//")) return t;
          return t.startsWith(`${base}/`) ? t : `${base}${t}`;
        })
        .join(", ");
      return `${lead}${attr}${eq}${quote}${list}${quote}`;
    }
    // Already-prefixed paths are left as they are, so the transform is idempotent.
    return `${lead}${attr}${eq}${quote}${base}/${quote}`;
  });
}

export default function rehypeBasePath(options = {}) {
  const base = (options.base ?? "").replace(/\/+$/, "");

  return (tree) => {
    if (!base) return;

    const visit = (node) => {
      if (node.type === "raw" && typeof node.value === "string") {
        node.value = prefixRawAttributes(node.value, base);
      }
      if (node.type === "element" && node.properties) {
        for (const attr of ATTRS) {
          const value = node.properties[attr];
          if (typeof value !== "string") continue;
          // Only rewrite true root-absolute paths. Leave protocol-relative
          // (//cdn...), absolute URLs, and already-prefixed paths alone.
          if (!value.startsWith("/") || value.startsWith("//")) continue;
          if (value.startsWith(`${base}/`)) continue;
          node.properties[attr] = `${base}${value}`;
        }
        // srcset is a comma-separated candidate list, so each candidate needs
        // its own prefix rather than one on the whole string.
        if (typeof node.properties.srcset === "string") {
          node.properties.srcset = node.properties.srcset
            .split(",")
            .map((c) => {
              const t = c.trim();
              if (!t.startsWith("/") || t.startsWith("//")) return t;
              return t.startsWith(`${base}/`) ? t : `${base}${t}`;
            })
            .join(", ");
        }
      }
      for (const child of node.children ?? []) visit(child);
    };

    visit(tree);
  };
}
