// Parse every ```mermaid block in kb/ with the real mermaid parser.
//
// This is the one job that needs Node. It runs in CI only, and only when a
// diagram changed, so the day-to-day build stays pure Python with no install
// step. Without it a malformed diagram ships silently as unrendered text.
//
//   npm install mermaid@11 jsdom
//   node tools/check_mermaid.mjs

import fs from "node:fs";
import path from "node:path";
import { JSDOM } from "jsdom";

const dom = new JSDOM("<!DOCTYPE html><body></body>", { pretendToBeVisual: true });
for (const key of ["window", "document", "navigator", "Element", "SVGElement",
                   "HTMLElement", "DocumentFragment", "Node"]) {
  const value = key === "window" ? dom.window : dom.window[key];
  // Node 22 defines some of these (navigator) as getter-only on globalThis, and
  // ESM is always strict, so plain assignment throws. defineProperty works for
  // both the getter-only and the undefined cases.
  Object.defineProperty(globalThis, key, {
    value, writable: true, configurable: true, enumerable: false,
  });
}

const { default: mermaid } = await import("mermaid");

function* markdownFiles(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) yield* markdownFiles(full);
    else if (entry.name.endsWith(".md")) yield full;
  }
}

const FENCE = /```mermaid\n([\s\S]*?)```/g;
let checked = 0;
const failures = [];

for (const file of markdownFiles("kb")) {
  const text = fs.readFileSync(file, "utf8");
  for (const match of text.matchAll(FENCE)) {
    checked++;
    try {
      await mermaid.parse(match[1]);
    } catch (error) {
      failures.push({ file, message: String(error.message || error).split("\n")[0] });
    }
  }
}

for (const { file, message } of failures) {
  console.error(`FAIL ${file}\n     ${message}`);
}
console.log(`Checked ${checked} mermaid block(s); ${failures.length} failed.`);
process.exit(failures.length ? 1 : 0);
