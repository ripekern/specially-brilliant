import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import rehypeBasePath from "./src/plugins/rehype-base-path.mjs";

/**
 * Pages that must never appear in the sitemap: transactional, payment, lending
 * and lender-vetting URLs. They are `noindex` in the template, and a sitemap
 * listing them would contradict that.
 */
const EXCLUDE = [
  "/pay-online",
  "/payment-success",
  "/fees",
  "/lender",
  "/loan-vetting-worksheet",
  "/bitcoin-cash-co-op",
  "/404",
];

/** The sitemap integration passes full URLs, so compare on pathname. */
function isExcluded(url) {
  const path = new URL(url).pathname.replace(/\/$/, "");
  return EXCLUDE.includes(path);
}

/**
 * `site` stays pinned to the real domain even for preview deploys: canonicals,
 * Open Graph URLs and the sitemap should always point at the production address,
 * so search engines treat a preview build as a duplicate rather than the origin.
 * `base` is the one thing that must change per deployment, because a GitHub
 * project page is served from a subpath.
 */
const SITE_URL = "https://speciallybrilliant.com";
const BASE_PATH = process.env.BASE_PATH || "/";

export default defineConfig({
  site: SITE_URL,
  base: BASE_PATH,
  output: "static",
  // The sitemap lists production URLs under the real domain. When serving from a
  // subpath the generated paths would be wrong, and a preview build should not
  // advertise itself as canonical anyway, so it ships without one.
  integrations:
    BASE_PATH === "/" ? [sitemap({ filter: (page) => !isExcluded(page) })] : [],
  build: {
    // Inline small CSS to cut render-blocking requests. The stylesheet is a few KB
    // after minification, so inlining beats an extra round trip on a cold cache.
    inlineStylesheets: "auto",
  },
  image: {
    // Modern formats with a JPEG fallback for anything older.
    responsiveStyles: true,
  },
  markdown: {
    shikiConfig: {
      theme: "github-dark",
    },
    // Content authors write plain /images/...; the base prefix is applied here so
    // the Markdown itself never has to know where the site is deployed.
    rehypePlugins: BASE_PATH === "/" ? [] : [[rehypeBasePath, { base: BASE_PATH }]],
  },
});
