/**
 * Ground-truth contrast check: renders the built site in a real browser and
 * runs axe-core's colour-contrast rule over it, in both colour schemes.
 *
 * Why this exists alongside tools/audit_contrast.py: the static audit only
 * checks pairs a human enumerated, so it missed a ghost button placed on a
 * dark band and a footer line coloured for a white page. Both are placement
 * problems -- the token is fine, the pairing is not -- and only a browser can
 * see them.
 *
 * Usage:
 *   npm run build
 *   npm run audit:contrast:browser
 *
 * Serves the build itself, mounted at whatever base path the build was made
 * with, so a BASE_PATH build is checked the way it will actually deploy.
 *
 * Needs puppeteer-core and axe-core installed, and a Chromium binary:
 *   npm i -D puppeteer-core axe-core
 *
 * This is deliberately not wired into CI: it needs a browser download on every
 * run, which is slow and heavy for a check that only needs to pass whenever
 * colours change. Run it before shipping a palette change.
 */

import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

// The package is "type": "module", but the two audit dependencies load fine
// from disk with require.resolve, so keep a require for those only.
const require = createRequire(import.meta.url);

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 8899);
const DIST = path.join(HERE, "..", "dist");

const SCHEMES = ["light", "dark"];

/**
 * Walk the build for routes instead of listing them.
 *
 * A hand-kept list silently stops covering new pages, which is how this started
 * out checking 9 of 23. Every page with an index.html is a route by
 * construction, so discovering them cannot drift.
 */
function discoverRoutes() {
  const routes = [];
  const walk = (dir, prefix) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const rel = prefix + entry.name;
      if (entry.isDirectory()) {
        walk(path.join(dir, entry.name), rel + "/");
      } else if (entry.name === "index.html") {
        routes.push(prefix || "/");
      }
    }
  };
  walk(DIST, "");
  // 404.html has no directory to be found in, but it is still a page the site
  // renders and it carries buttons like everything else.
  if (fs.existsSync(path.join(DIST, "404.html"))) routes.push("/404.html");
  return routes.sort();
}

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".xml": "application/xml",
  ".txt": "text/plain; charset=utf-8",
  ".json": "application/json",
};

/**
 * Read the deploy base out of the built HTML instead of assuming "/".
 *
 * The Pages build sets BASE_PATH and emits /<repo>/-prefixed asset URLs, so a
 * build that looks identical to a local one serves its stylesheet from a path
 * the server does not have. The page then renders unstyled, axe finds no
 * text/background pairs to complain about, and this script reports PASS on a
 * site it never actually styled.
 */
function detectBase() {
  const html = fs.readFileSync(path.join(DIST, "index.html"), "utf8");
  // Capture the base in one go. Stripping a "_astro/" suffix with a regex reads
  // like it removes the leading slash too, and silently leaves one behind.
  const m = html.match(/(?:href|src)="(\/(?:[^"]*\/)?)_astro\//);
  if (!m) return "/";
  const base = m[1];
  console.log(`build base: ${base}`);
  return base.endsWith("/") ? base : base + "/";
}

function serve(base) {
  const mount = base.endsWith("/") ? base : base + "/";
  const server = http.createServer((req, res) => {
    let rel = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
    if (mount !== "/" && rel.startsWith(mount)) {
      rel = rel.slice(mount.length - 1);
    } else if (mount !== "/") {
      res.writeHead(404, { "content-type": "text/plain" });
      return res.end("outside the deploy base");
    }
    let file = path.normalize(path.join(DIST, rel));
    if (file !== DIST && !file.startsWith(DIST + path.sep)) {
      res.writeHead(403, { "content-type": "text/plain" });
      return res.end("outside dist/");
    }
    if (rel.endsWith("/")) file = path.join(file, "index.html");
    fs.readFile(file, (err, buf) => {
      if (err) {
        res.writeHead(404, { "content-type": "text/plain" });
        return res.end("not found");
      }
      res.writeHead(200, { "content-type": TYPES[path.extname(file)] || "application/octet-stream" });
      res.end(buf);
    });
  });
  return new Promise((ok) => server.listen(PORT, "127.0.0.1", () => ok(server)));
}

function loadDeps() {
  for (const dep of ["puppeteer-core", "axe-core"]) {
    try {
      require.resolve(dep);
    } catch {
      console.error(
        `Missing ${dep}. Install with:\n  npm i -D puppeteer-core axe-core`
      );
      process.exit(2);
    }
  }
}

function findChromium() {
  const executablePath =
    process.env.CHROMIUM_PATH ||
    ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"].find(
      (p) => fs.existsSync(p)
    );
  if (!executablePath) {
    console.error("No Chromium found. Set CHROMIUM_PATH.");
    process.exit(2);
  }
  return executablePath;
}

async function main() {
  if (!fs.existsSync(path.join(DIST, "index.html"))) {
    console.error("dist/ is empty. Run `npm run build` first.");
    process.exit(2);
  }
  loadDeps();

  const base = detectBase();
  const routes = discoverRoutes();
  console.log(`auditing ${routes.length} routes`);
  const server = await serve(base);
  const origin = `http://127.0.0.1:${PORT}`;
  const puppeteer = require("puppeteer-core");
  const axeSource = fs.readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");

  const browser = await puppeteer.launch({
    executablePath: findChromium(),
    headless: "new",
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
  });

  // A stylesheet that 404s leaves the page unstyled and the audit vacuous, so
  // treat any broken subresource as a hard failure rather than an empty pass.
  const broken = new Set();
  const errors = new Set();
  const findings = new Map();

  for (const scheme of SCHEMES) {
    const page = await browser.newPage();
    await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: scheme }]);
    page.on("response", (r) => {
      if (r.status() >= 400) broken.add(`${r.status()} ${r.url()}`);
    });
    // Fonts and ad tags are external and irrelevant to contrast. Letting them
    // through leaves the audit waiting on a network it does not need, and
    // timing out on a page it never actually checked.
    await page.setRequestInterception(true);
    page.on("request", (req) => {
      if (req.url().startsWith(origin)) req.continue();
      else req.abort();
    });
    for (const route of routes) {
      try {
        await page.goto(origin + base + route.replace(/^\//, ""), { waitUntil: "load" });
        const sheets = await page.evaluate(() => document.styleSheets.length);
        if (!sheets) {
          throw new Error(
            `loaded no stylesheet under base ${base}; an unstyled page has no ` +
              "colours to audit, so this would pass falsely"
          );
        }
        await page.evaluate(axeSource);
        const res = await page.evaluate(async () =>
          // eslint-disable-next-line no-undef
          (await axe.run(document, {
            runOnly: { type: "rule", values: ["color-contrast"] },
          })).violations.flatMap((v) =>
            v.nodes.map((n) => ({
              id: v.id,
              impact: v.impact,
              target: n.target.join(" "),
              html: (n.html || "").slice(0, 140),
              detail: (n.failureSummary || "").replace(/\s+/g, " ").slice(0, 240),
            }))
          )
        );
        for (const r of res) {
          const key = `${scheme}|${r.target}`;
          if (!findings.has(key)) findings.set(key, { ...r, scheme, pages: [] });
          findings.get(key).pages.push(route);
        }
      } catch (err) {
        errors.push(`[${scheme}] ${route}: ${err.message}`);
      }
    }
    await page.close();
  }
  await browser.close();
  server.close();

  if (errors.size) {
    console.error(`\nFAIL  ${errors.size} route(s) could not be audited:`);
    for (const e of [...errors].slice(0, 10)) console.error(`  ${e}`);
    process.exit(1);
  }

  if (broken.size) {
    console.error(`\nFAIL  ${broken.size} broken subresource(s) while loading the build:`);
    for (const b of [...broken].slice(0, 10)) console.error(`  ${b}`);
    console.error("The audit did not run against the real stylesheet.");
    process.exit(1);
  }

  if (!findings.size) {
    console.log(
      `PASS  no colour-contrast violations across ${routes.length} routes x ${SCHEMES.length} schemes`
    );
    return;
  }

  console.log(`FAIL  ${findings.size} distinct violation(s)\n`);
  for (const f of findings.values()) {
    console.log(`  [${f.scheme}] ${f.target}`);
    console.log(`    html   : ${f.html}`);
    console.log(`    detail : ${f.detail}`);
    console.log(`    on     : ${[...new Set(f.pages)].join(", ")}`);
    console.log("");
  }
  process.exitCode = 1;
}

main();
