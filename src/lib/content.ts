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

export type SiteConfig = Awaited<ReturnType<typeof getSite>>;

export function areaServedSchema(site: SiteConfig) {
  return [
    ...site.serviceArea.map((name) => ({ "@type": "City", name })),
    {
      "@type": "GeoCircle",
      geoMidpoint: {
        "@type": "GeoCoordinates",
        latitude: site.geo.latitude,
        longitude: site.geo.longitude,
      },
      geoRadius: String(site.serviceAreaRadius),
    },
  ];
}

export function geoSchema(site: SiteConfig) {
  return {
    "@type": "GeoCoordinates",
    latitude: site.geo.latitude,
    longitude: site.geo.longitude,
  };
}

const DAY_ORDER = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];

const DAY_ABBR: Record<string, string> = {
  Sunday: "Su",
  Monday: "Mo",
  Tuesday: "Tu",
  Wednesday: "We",
  Thursday: "Th",
  Friday: "Fr",
  Saturday: "Sa",
};

function dayRange(days: string[]) {
  const idx = days
    .map((d) => DAY_ORDER.indexOf(d))
    .filter((i) => i >= 0)
    .sort((a, b) => a - b);
  const runs: number[][] = [];
  for (const i of idx) {
    const last = runs[runs.length - 1];
    if (last && i === last[last.length - 1] + 1) last.push(i);
    else runs.push([i]);
  }
  return runs
    .map((run) => {
      const first = DAY_ABBR[DAY_ORDER[run[0]]];
      const last = DAY_ABBR[DAY_ORDER[run[run.length - 1]]];
      return run.length > 1 ? `${first}-${last}` : first;
    })
    .join(",");
}

export function openingHoursSpecification(site: SiteConfig) {
  return site.hours.map((block) => ({
    "@type": "OpeningHoursSpecification",
    dayOfWeek: block.days,
    opens: block.opens,
    closes: block.closes,
  }));
}

export function openingHours(site: SiteConfig) {
  return site.hours
    .map((block) => `${dayRange(block.days)} ${block.opens}-${block.closes}`)
    .join(", ");
}

const DAY_SHORT: Record<string, string> = {
  Sunday: "Sun",
  Monday: "Mon",
  Tuesday: "Tue",
  Wednesday: "Wed",
  Thursday: "Thu",
  Friday: "Fri",
  Saturday: "Sat",
};

export function formatTime(hhmm: string) {
  const [h, m] = hhmm.split(":").map(Number);
  const period = h >= 12 ? "pm" : "am";
  const hour = h % 12 === 0 ? 12 : h % 12;
  return m === 0 ? `${hour}${period}` : `${hour}:${String(m).padStart(2, "0")}${period}`;
}

export function humanHours(site: SiteConfig) {
  return site.hours.map((block) => {
    const ordered = [...block.days].sort(
      (a, b) => DAY_ORDER.indexOf(a) - DAY_ORDER.indexOf(b),
    );
    const labels = ordered.map((d) => DAY_SHORT[d]);
    const days =
      labels.length > 1 ? `${labels[0]}–${labels[labels.length - 1]}` : labels[0];
    return `${days} ${formatTime(block.opens)}–${formatTime(block.closes)}`;
  });
}

export type Doc = {
  id: string;
  data: {
    title: string;
    slug: string;
    description?: string;
    seoTitle?: string;
    seoDescription?: string;
    image?: string;
    ogImageWidth?: number;
    ogImageHeight?: number;
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
