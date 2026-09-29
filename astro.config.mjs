import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

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

export default defineConfig({
  site: "https://speciallybrilliant.com",
  output: "static",
  integrations: [sitemap({ filter: (page) => !isExcluded(page) })],
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
  },
});
