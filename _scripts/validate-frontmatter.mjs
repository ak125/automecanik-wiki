#!/usr/bin/env node
// validate-frontmatter.mjs — validate frontmatter of every .md under wiki/ and proposals/
// against _meta/schema/frontmatter.schema.json (and per-entity schemas under _meta/schema/entity-data/).
//
// Usage:
//   node _scripts/validate-frontmatter.mjs                  # validate all
//   node _scripts/validate-frontmatter.mjs <file> [<file>…] # validate listed files (pre-commit pass-filenames)
// Exit codes: 0 = OK, 1 = validation failure, 2 = setup error.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import Ajv from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import yaml from "js-yaml";

const __filename = fileURLToPath(import.meta.url);
const REPO_ROOT = join(dirname(__filename), "..");
const SCHEMA_DIR = join(REPO_ROOT, "_meta", "schema");
const FM_SCHEMA_PATH = join(SCHEMA_DIR, "frontmatter.schema.json");

const SCAN_ROOTS = ["wiki", "proposals"];
const FRONTMATTER_RE = /^---\n([\s\S]*?)\n---\n/;

function loadSchema(path) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (e) {
    console.error(`ERROR: cannot load schema ${relative(REPO_ROOT, path)}: ${e.message}`);
    process.exit(2);
  }
}

function setupAjv() {
  const ajv = new Ajv({ allErrors: true, strict: false, allowUnionTypes: true });
  addFormats(ajv);
  ajv.addSchema(loadSchema(FM_SCHEMA_PATH), "frontmatter");
  for (const f of readdirSync(join(SCHEMA_DIR, "entity-data"))) {
    if (!f.endsWith(".schema.json")) continue;
    const schema = loadSchema(join(SCHEMA_DIR, "entity-data", f));
    ajv.addSchema(schema, schema.$id || `entity-data:${f}`);
  }
  return ajv;
}

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
      else if (ent.isFile() && ent.name.endsWith(".md")) out.push(p);
    }
  }
  return out;
}

function safeStat(p) {
  try { return statSync(p); } catch { return null; }
}

function parseFrontmatter(text, filePath) {
  const m = FRONTMATTER_RE.exec(text);
  if (!m) return { fm: null, error: "no frontmatter block (---...---) found" };
  try {
    const fm = yaml.load(m[1]);
    if (!fm || typeof fm !== "object") return { fm: null, error: "frontmatter is empty or not a mapping" };
    return { fm };
  } catch (e) {
    return { fm: null, error: `YAML parse error: ${e.message}` };
  }
}

function validateOne(ajv, file) {
  const text = readFileSync(file, "utf8");
  const { fm, error } = parseFrontmatter(text, file);
  if (error) return [`${relative(REPO_ROOT, file)}: ${error}`];

  const errors = [];
  const validateFm = ajv.getSchema("frontmatter");
  if (!validateFm(fm)) {
    for (const e of validateFm.errors || []) {
      errors.push(`${relative(REPO_ROOT, file)} [frontmatter]: ${e.instancePath || "/"} ${e.message}`);
    }
  }

  const entityType = fm.entity_type;
  if (entityType) {
    const id = `https://automecanik.com/schemas/entity-data/${entityType}.schema.json`;
    const validateEntity = ajv.getSchema(id);
    if (validateEntity && fm.entity_data) {
      if (!validateEntity(fm.entity_data)) {
        for (const e of validateEntity.errors || []) {
          errors.push(`${relative(REPO_ROOT, file)} [entity_data:${entityType}]: ${e.instancePath || "/"} ${e.message}`);
        }
      }
    }
  }

  return errors;
}

function main() {
  const ajv = setupAjv();
  const argv = process.argv.slice(2);
  const files = argv.length
    ? argv.map((a) => (a.startsWith("/") ? a : join(REPO_ROOT, a))).filter((f) => f.endsWith(".md") && safeStat(f))
    : SCAN_ROOTS.flatMap(walkMd);

  if (files.length === 0) {
    console.log("validate-frontmatter: no .md files to check");
    return 0;
  }

  let failed = 0;
  const allErrors = [];
  for (const file of files) {
    const errs = validateOne(ajv, file);
    if (errs.length) {
      failed += 1;
      allErrors.push(...errs);
    }
  }

  if (failed === 0) {
    console.log(`validate-frontmatter: OK (${files.length} files)`);
    return 0;
  }
  console.error(`validate-frontmatter: ${failed}/${files.length} file(s) failed`);
  for (const e of allErrors) console.error(`  ${e}`);
  return 1;
}

process.exit(main());
