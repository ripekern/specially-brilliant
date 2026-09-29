/**
 * Site data helpers: load config, classify content, and answer the questions the
 * templates ask often enough to be worth naming.
 */

import { getCollection, getEntry, render } from "astro:content";

/** The single source of truth for business details. */
export async function getSite() {
  const entry = await getEntry("config", "site");
  if (!entry) throw new Error("src/data/site.json is missing or unreadable");
  return entry.data;
}

export type Doc = {
  id: string;
  data: {
    title: string;
    slug: string;
    description?: string;
    date?: string;
    type: "service" | "core" | "transactional" | "side-project" | "post";
    order: number;
    draft: boolean;
    noindex: boolean;
    tags: string[];
  };
};

/** All pages, excluding drafts, in editorial order. */
export async function getPages(): Promise<Doc[]> {
  const pages = await getCollection("documents", ({ data }) => !data.draft);
  return pages
    .map((p) => ({ id: p.id, data: p.data }))
    .sort((a, b) => a.data.order - b.data.order || a.data.title.localeCompare(b.data.title));
}

export async function getPosts(): Promise<Doc[]> {
  const posts = await getCollection("posts", ({ data }) => !data.draft);
  return posts
    .map((p) => ({ id: p.id, data: p.data }))
    .sort((a, b) => (b.data.date ?? "").localeCompare(a.data.date ?? ""));
}

export async function getServices(): Promise<Doc[]> {
  return (await getPages()).filter((p) => p.data.type === "service");
}

export async function getCorePages(): Promise<Doc[]> {
  return (await getPages()).filter((p) => p.data.type === "core");
}

/** Render a content entry's Markdown to HTML. */
export async function renderDoc(id: string) {
  const entry = await getEntry("documents", id) ?? await getEntry("posts", id);
  if (!entry) throw new Error(`No content entry for id "${id}"`);
  return render(entry);
}

/**
 * Render a stored phone number for humans without changing the tel: href.
 * Accepts any of the forms a number might be typed in, so editing site.json
 * cannot silently produce "(509" or leave a raw +1 on the page.
 */
export function formatPhone(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  const local = digits.length === 11 && digits.startsWith("1") ? digits.slice(1) : digits;
  if (local.length !== 10) return raw;
  return `(${local.slice(0, 3)}) ${local.slice(3, 6)}-${local.slice(6)}`;
}
