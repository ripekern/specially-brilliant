import { defineCollection, z } from "astro:content";
import { glob, file } from "astro/loaders";

/**
 * Pages and posts share a schema: they are the same kind of thing (a URL with prose),
 * differing only in `type`. The WordPress distinction (page vs post) carried no real
 * behavior on this site, so the model drops it and keeps `type` for URL and menuing.
 */
const documents = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/pages" }),
  schema: z.object({
    title: z.string(),
    slug: z.string(),
    wpId: z.coerce.number().optional(),
    description: z.string().optional(),
    // Search copy, used verbatim for <title> and the description meta when present.
    // `title` stays the visible H1 so the on-page headline and the search result
    // can differ. The brand suffix is appended by Base.astro, so do not include it.
    seoTitle: z.string().optional(),
    seoDescription: z.string().optional(),
    // Lead image, reused as og:image. Should be 1200x630 (og:imageWidth/Height).
    image: z.string().optional(),
    ogImageWidth: z.number().optional(),
    ogImageHeight: z.number().optional(),
    date: z.string().optional(),
    modified: z.string().optional(),
    source: z.string().url().optional(),
    // Editorial classification, used for navigation and ordering.
    type: z.enum(["service", "core", "transactional", "side-project"]).default("core"),
    order: z.number().default(100),
    draft: z.boolean().default(false),
    noindex: z.boolean().default(false),
    showHours: z.boolean().default(false),
    tags: z.array(z.string()).default([]),
    /**
     * Businesses in the Bitcoin Cash co-op. Data rather than prose so the
     * template can render a name, a trade, a working tel: link and a service
     * area consistently, and so adding a member is a frontmatter edit.
     */
    members: z
      .array(
        z.object({
          name: z.string(),
          trade: z.string().optional(),
          url: z.string().url().optional(),
          phone: z.string().optional(),
          area: z.string().optional(),
          note: z.string().optional(),
        }),
      )
      .default([]),
    /**
     * Google reviews, republished by hand rather than pulled from the Places API.
     * That API forbids caching its content, and a static site has nowhere to keep
     * a key that would not be exposed, so the reviews are entered here and the
     * page links out to Google for the authoritative, complete set.
     *
     * Held as data for the same reason as `members`: the visible cards, the
     * average and the count all render from this one array, so a review cannot be
     * listed without being counted or shown.
     */
    reviews: z
      .array(
        z.object({
          /** First name and last initial only, e.g. "Deb A." */
          author: z.string(),
          rating: z.number().min(1).max(5),
          /**
           * The reviewer's own words, verbatim. Not edited, not trimmed.
           * Optional because a rating can be left without a comment, and those
           * still count -- they are shown as a rating rather than a quote, never
           * as words the reviewer did not write.
           */
          text: z.string().optional(),
          /**
           * Year of the review, derived from the relative date Google shows
           * ("a year ago"), which is the only precision available. Held as a year
           * rather than a full date so it is never more specific than the source.
           */
          when: z.number().optional(),
          /** Slug of a service page this review mentions, if any. */
          service: z.string().optional(),
        }),
      )
      .default([]),
    /**
     * Questions the page answers in prose. Held as data rather than Markdown so
     * the visible list and the FAQPage JSON-LD are rendered from one source and
     * cannot drift apart -- a schema claim the page does not visibly support is
     * the kind of thing that gets a rich result revoked.
     */
    faq: z
      .array(z.object({ q: z.string(), a: z.string() }))
      .default([]),
  }),
});

const posts = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/posts" }),
  schema: z.object({
    title: z.string(),
    slug: z.string(),
    wpId: z.coerce.number().optional(),
    description: z.string().optional(),
    seoTitle: z.string().optional(),
    seoDescription: z.string().optional(),
    image: z.string().optional(),
    ogImageWidth: z.number().optional(),
    ogImageHeight: z.number().optional(),
    date: z.string().optional(),
    modified: z.string().optional(),
    source: z.string().url().optional(),
    type: z.literal("post"),
    order: z.number().default(100),
    draft: z.boolean().default(false),
    noindex: z.boolean().default(false),
    tags: z.array(z.string()).default([]),
  }),
});

const config = defineCollection({
  loader: file("src/data/site.json"),
  schema: z.object({
    name: z.string(),
    tagline: z.string(),
    legalName: z.string(),
    owner: z.string(),
    phone: z.string(),
    email: z.string(),
    url: z.string().url(),
    area: z.array(z.string()),
    serviceArea: z.array(z.string()),
    geo: z.object({
      latitude: z.number(),
      longitude: z.number(),
    }),
    serviceAreaRadius: z.number(),
    hours: z
      .array(
        z.object({
          days: z.array(z.enum([
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
          ])),
          opens: z.string().regex(/^\d{2}:\d{2}$/),
          closes: z.string().regex(/^\d{2}:\d{2}$/),
        }),
      )
      .refine(
        (blocks) => {
          const seen = new Set<string>();
          for (const block of blocks) {
            for (const day of block.days) {
              if (seen.has(day)) return false;
              seen.add(day);
            }
          }
          return true;
        },
        { message: "a day may only appear in one hours block" },
      ),
    since: z.number(),
    currency: z.string(),
    /**
     * The Google Business Profile. Optional because the reviews section is
     * useful without it, but it is what lets a visitor see the complete set of
     * reviews rather than only the ones republished here -- so it should be set.
     */
    googleProfile: z.string().url().optional(),
    bookingUrl: z.string().url(),
    social: z.object({
      facebook: z.string().url().optional(),
    }).optional(),
  }),
});

export const collections = { documents, posts, config };
