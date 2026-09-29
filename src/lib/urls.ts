/**
 * Base-path-aware URL helper.
 *
 * Astro's `base` setting does not rewrite `href="/services/"` in templates, so a
 * build served from a subpath (a GitHub project page at /specially-brilliant/)
 * would 404 on every absolute link. Routing every internal URL through `withBase`
 * keeps one source of truth for the prefix and makes the same source deploy to a
 * root domain or a subpath with no edits.
 *
 * Local builds have BASE_URL "/", so this is a no-op there.
 */
const BASE = (import.meta.env.BASE_URL ?? "/").replace(/\/+$/, "");

/** Prefix a root-absolute path with the deploy base. */
export function withBase(path: string): string {
  if (!path.startsWith("/")) return path; // already relative or absolute URL
  return `${BASE}${path}`;
}
