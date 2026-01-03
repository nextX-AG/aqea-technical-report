/**
 * Render TECHNICAL_REPORT.md to a self-contained HTML file (no Chromium/Puppeteer).
 *
 * This is a fallback for environments where headless Chromium dependencies are not available.
 * The generated HTML can be printed to PDF using the browser print dialog.
 */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

// md-to-pdf depends on marked; we reuse it to avoid extra deps.
import { marked } from "marked";

function usage() {
  // eslint-disable-next-line no-console
  console.error("Usage: node repro/render_html.mjs <input.md> <output.html>");
}

const input = process.argv[2];
const output = process.argv[3];
if (!input || !output) {
  usage();
  process.exit(2);
}

const md = fs.readFileSync(input, "utf-8");
const cssPath = path.join(path.dirname(new URL(import.meta.url).pathname), "pdf.css");
const css = fs.readFileSync(cssPath, "utf-8");

const body = marked.parse(md);
const title = "AQEA Technical Report";

const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${title}</title>
    <style>${css}</style>
  </head>
  <body>
    <main class="md-body">
      ${body}
    </main>
  </body>
</html>`;

fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, html, "utf-8");

// eslint-disable-next-line no-console
console.log(`Wrote HTML: ${output}`);

