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

export default function rehypeBasePath(options = {}) {
  const base = (options.base ?? "").replace(/\/+$/, "");

  return (tree) => {
    if (!base) return;

    const visit = (node) => {
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
