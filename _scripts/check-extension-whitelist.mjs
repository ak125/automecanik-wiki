#!/usr/bin/env node
// check-extension-whitelist.mjs — fail if a tracked file under content roots has a forbidden extension.
// Allowed under wiki/, proposals/, _meta/, _templates/, glossary/, taxonomy/, maps/, _audit/, exports/:
//   .md .json .yaml .yml .png .jpg .jpeg .svg .gitkeep
// Hidden files (starting with .) are ignored.

import { readdirSync, statSync } from "node:fs";
import { join, relative, dirname, extname, basename } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const REPO_ROOT = join(dirname(__filename), "..");

const SCAN_ROOTS = [
  "wiki", "proposals", "_meta", "_templates",
  "glossary", "taxonomy", "maps", "_audit", "exports",
];
const ALLOWED = new Set([
  ".md", ".json", ".yaml", ".yml",
  ".png", ".jpg", ".jpeg", ".svg",
]);
const ALLOWED_FILENAMES = new Set([".gitkeep"]);

function safeStat(p) { try { return statSync(p); } catch { return null; } }

function walk(root) {
  const out = [];
  const abs = join(REPO_ROOT, root);
  if (!safeStat(abs)) return out;
  const stack = [abs];
  while (stack.length) {
    const dir = stack.pop();
    for (const ent of readdirSync(dir, { withFileTypes: true })) {
      if (ent.name.startsWith(".") && ent.name !== ".gitkeep") continue;
      const p = join(dir, ent.name);
      if (ent.isDirectory()) stack.push(p);
      else if (ent.isFile()) out.push(p);
    }
  }
  return out;
}

function main() {
  const files = SCAN_ROOTS.flatMap(walk);
  const violations = [];
  for (const f of files) {
    const name = basename(f);
    if (ALLOWED_FILENAMES.has(name)) continue;
    const ext = extname(name).toLowerCase();
    if (!ALLOWED.has(ext)) violations.push(relative(REPO_ROOT, f));
  }
  if (violations.length === 0) {
    console.log(`check-extension-whitelist: OK (${files.length} files)`);
    return 0;
  }
  console.error(`check-extension-whitelist: ${violations.length} forbidden file(s)`);
  for (const v of violations) console.error(`  - ${v}`);
  return 1;
}

process.exit(main());
