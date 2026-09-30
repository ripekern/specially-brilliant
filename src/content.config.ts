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
  }),
});

const posts = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/posts" }),
  schema: z.object({
    title: z.string(),
    slug: z.string(),
    wpId: z.coerce.number().optional(),
    description: z.string().optional(),
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
    bookingUrl: z.string().url(),
    social: z.object({
      facebook: z.string().url().optional(),
    }).optional(),
  }),
});

export const collections = { documents, posts, config };
