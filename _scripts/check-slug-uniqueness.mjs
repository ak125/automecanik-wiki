#!/usr/bin/env node
// check-slug-uniqueness.mjs — fail if two .md under wiki/ or proposals/ share the same slug.
// The slug field comes from frontmatter (key `slug`) when present, else falls back to filename
// without extension. Scope is per entity_type when both files declare one (a vehicle and a gamme
// can share a slug; two gammes cannot).

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";
import yaml from "js-yaml";

const __filename = fileURLToPath(import.meta.url);
const REPO_ROOT = join(dirname(__filename), "..");
const SCAN_ROOTS = ["wiki", "proposals"];
const FRONTMATTER_RE = /^---\n([\s\S]*?)\n---\n/;

function safeStat(p) { try { return statSync(p); } catch { return null; } }

function walkMd(root) {
  const out = [];
  const abs = join(REPO_ROOT, root);
  if (!safeStat(abs)) return out;
  const stack = [abs];
  while (stack.length) {
    const dir = stack.pop();
    for (const ent of readdirSync(dir, { withFileTypes: true })) {
      const p = join(dir, ent.name);
      if (ent.isDirectory()) stack.push(p);
      // Skip files prefixed with `_` (meta: _index.md, _manifest.json, etc.) — D19 convention.
      else if (ent.isFile() && ent.name.endsWith(".md") && !ent.name.startsWith("_")) out.push(p);
    }
  }
  return out;
}

function readSlug(file) {
  const text = readFileSync(file, "utf8");
  const m = FRONTMATTER_RE.exec(text);
  if (!m) return { slug: null, entity_type: null };
  try {
    const fm = yaml.load(m[1]) || {};
    const slug = fm.slug || basename(file, ".md");
    return { slug, entity_type: fm.entity_type || "_unscoped" };
  } catch {
    return { slug: basename(file, ".md"), entity_type: "_unscoped" };
  }
}

function main() {
  const files = SCAN_ROOTS.flatMap(walkMd);
  const buckets = new Map();
  for (const f of files) {
    const { slug, entity_type } = readSlug(f);
    if (!slug) continue;
    const key = `${entity_type}:${slug}`;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(f);
  }
  const collisions = [...buckets.entries()].filter(([, v]) => v.length > 1);
  if (collisions.length === 0) {
    console.log(`check-slug-uniqueness: OK (${files.length} files, ${buckets.size} unique slugs)`);
    return 0;
  }
  console.error(`check-slug-uniqueness: ${collisions.length} collision(s)`);
  for (const [key, group] of collisions) {
    console.error(`  ${key}`);
    for (const f of group) console.error(`    - ${relative(REPO_ROOT, f)}`);
  }
  return 1;
}

process.exit(main());
