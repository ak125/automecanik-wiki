#!/usr/bin/env node
// validate-frontmatter.mjs — validate frontmatter of every .md under wiki/ and proposals/
// against _meta/schema/frontmatter.schema.json (and per-entity schemas under _meta/schema/entity-data/).
//
// Usage:
//   node _scripts/validate-frontmatter.mjs                  # validate all
//   node _scripts/validate-frontmatter.mjs <file> [<file>…] # validate listed files (pre-commit pass-filenames)
//   node _scripts/validate-frontmatter.mjs --strict-entity-data [<file>…]
//
// RATCHET entity_data (ADR-062 — aucune règle nouvelle ne démarre bloquante) :
// les écarts du bloc `entity_data` sortent par défaut en `WARN [entity_data:<type>]`
// et NE changent PAS le code de sortie. `--strict-entity-data` (opt-in, convention
// du dépôt : cf. check-coverage-map.py --strict, quality-gates.py --cross-repo)
// les passe en erreurs avec sortie non nulle. La bascule bloquante = PR distincte.
//
// Exit codes: 0 = OK, 1 = validation failure, 2 = setup error.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, dirname, basename } from "node:path";
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

const ENTITY_SCHEMA_SUFFIX = ".schema.json";

// Enregistre les schémas et MÉMORISE la clé d'enregistrement réelle de chacun.
// La clé vient du schéma lui-même (`$id`) — aucune convention d'URL n'est devinée
// ici : c'est précisément l'URL inventée côté résolution qui rendait `getSchema()`
// systématiquement `undefined` et sautait le bloc entity_data en silence.
function setupAjv() {
  const ajv = new Ajv({ allErrors: true, strict: false, allowUnionTypes: true });
  addFormats(ajv);
  ajv.addSchema(loadSchema(FM_SCHEMA_PATH), "frontmatter");
  const entitySchemaKeys = new Map(); // entity_type -> clé ajv
  for (const f of readdirSync(join(SCHEMA_DIR, "entity-data"))) {
    if (!f.endsWith(ENTITY_SCHEMA_SUFFIX)) continue;
    const schema = loadSchema(join(SCHEMA_DIR, "entity-data", f));
    const key = schema.$id || `entity-data:${f}`;
    ajv.addSchema(schema, key);
    entitySchemaKeys.set(f.slice(0, -ENTITY_SCHEMA_SUFFIX.length), key);
  }
  return { ajv, entitySchemaKeys };
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
      // Skip directories prefixed with `_` (meta containers: _quality/, _coverage/, _audit/) — D19 convention.
      if (ent.isDirectory()) {
        if (!ent.name.startsWith("_")) stack.push(p);
      }
      // Skip files prefixed with `_` (meta: _index.md, _manifest.json, etc.) — D19 convention.
      else if (ent.isFile() && ent.name.endsWith(".md") && !ent.name.startsWith("_")) out.push(p);
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

function validateOne({ ajv, entitySchemaKeys }, file) {
  const rel = relative(REPO_ROOT, file);
  const text = readFileSync(file, "utf8");
  const { fm, error } = parseFrontmatter(text, file);
  if (error) return { errors: [`${rel}: ${error}`], entityDeviations: [] };

  const errors = [];
  const validateFm = ajv.getSchema("frontmatter");
  if (!validateFm(fm)) {
    for (const e of validateFm.errors || []) {
      errors.push(`${rel} [frontmatter]: ${e.instancePath || "/"} ${e.message}`);
    }
  }

  const entityDeviations = [];
  if (fm.entity_data !== undefined && fm.entity_data !== null) {
    const entityType = typeof fm.entity_type === "string" ? fm.entity_type : null;
    const schemaKey = entityType ? entitySchemaKeys.get(entityType) : undefined;
    if (!schemaKey) {
      // Trou de contrat : un bloc entity_data que rien ne valide. Rendu VISIBLE,
      // jamais sauté en silence (le `entity_type` manquant est déjà couvert par
      // le schéma frontmatter, mais l'absence de schéma entity-data ne l'est pas).
      entityDeviations.push({
        entityType: entityType || "<entity_type absent>",
        rel,
        instancePath: "/",
        message: `entity_data_schema_missing — aucun _meta/schema/entity-data/${
          entityType ? `${entityType}${ENTITY_SCHEMA_SUFFIX}` : "<type>.schema.json"
        } enregistré`,
      });
    } else {
      const validateEntity = ajv.getSchema(schemaKey);
      if (!validateEntity) {
        // Incohérence interne (clé mémorisée à l'enregistrement mais absente d'ajv) :
        // erreur de setup, jamais un skip.
        console.error(`ERROR: schéma entity-data enregistré sous ${schemaKey} introuvable dans ajv`);
        process.exit(2);
      }
      if (!validateEntity(fm.entity_data)) {
        for (const e of validateEntity.errors || []) {
          entityDeviations.push({
            entityType,
            rel,
            instancePath: e.instancePath || "/",
            message: e.message,
          });
        }
      }
    }
  }

  return { errors, entityDeviations };
}

// D19 : les fichiers/dossiers préfixés `_` sont les méta-conteneurs DES ARBRES DE
// CONTENU (wiki/_quality/, proposals/_index.md…). La règle est donc ancrée sur
// SCAN_ROOTS, exactement comme l'exclusion `^(wiki|proposals)/_` du hook pre-commit
// `wiki-frontmatter-schema-py`. Un fichier explicitement listé hors de ces arbres
// (fixture de test sous _scripts/tests/) est validé, pas écarté en silence.
function isMetaContentPath(rel) {
  const parts = rel.split(/[\\/]/);
  if (!SCAN_ROOTS.includes(parts[0])) return false;
  return parts.some((part) => part.startsWith("_"));
}

function parseArgv(argv) {
  const opts = { strictEntityData: false };
  const positional = [];
  for (const a of argv) {
    if (a === "--strict-entity-data") {
      opts.strictEntityData = true;
      continue;
    }
    if (a.startsWith("--")) {
      console.error(`ERROR: unknown flag ${a} (known: --strict-entity-data)`);
      process.exit(2);
    }
    positional.push(a);
  }
  return { opts, positional };
}

function main() {
  const ctx = setupAjv();
  const { opts, positional } = parseArgv(process.argv.slice(2));
  const skipped = [];
  const files = positional.length
    ? positional
        .map((a) => (a.startsWith("/") ? a : join(REPO_ROOT, a)))
        .filter((f) => {
          const keep = f.endsWith(".md") && !isMetaContentPath(relative(REPO_ROOT, f)) && safeStat(f);
          if (!keep) skipped.push(relative(REPO_ROOT, f));
          return keep;
        })
    : SCAN_ROOTS.flatMap(walkMd);

  if (files.length === 0) {
    // Ne jamais rendre 0 en silence sur des arguments écartés : dire lesquels.
    console.log("validate-frontmatter: no .md files to check");
    if (skipped.length) console.log(`  skipped (non-.md, meta D19, or missing): ${skipped.join(", ")}`);
    return 0;
  }

  let failed = 0;
  const allErrors = [];
  const allWarnings = [];
  const warnFiles = new Set();
  for (const file of files) {
    const { errors, entityDeviations } = validateOne(ctx, file);
    const fileErrors = [...errors];
    if (opts.strictEntityData) {
      for (const d of entityDeviations) {
        fileErrors.push(`${d.rel} [entity_data:${d.entityType}]: ${d.instancePath} ${d.message}`);
      }
    } else if (entityDeviations.length) {
      allWarnings.push(...entityDeviations);
      for (const d of entityDeviations) warnFiles.add(d.rel);
    }
    if (fileErrors.length) {
      failed += 1;
      allErrors.push(...fileErrors);
    }
  }

  if (allWarnings.length) {
    // RATCHET : report-only, le code de sortie ne change pas (ADR-062).
    console.error(
      `validate-frontmatter: ${allWarnings.length} entity_data deviation(s) in ${warnFiles.size}/${files.length} file(s) — RATCHET report-only, exit code unchanged (use --strict-entity-data to enforce)`,
    );
    for (const w of allWarnings) {
      console.error(`  WARN [entity_data:${w.entityType}] ${w.rel}: ${w.instancePath} ${w.message}`);
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
