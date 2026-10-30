// Preuve d'ADR-117 D5 b côté Node : sous un slug, check-slug-uniqueness.mjs n'admet que le canon
// et une proposition de proposals/ dont `revision_of.path` le désigne ; toute autre collision échoue.
// Le script calcule sa racine depuis son propre emplacement : chaque cas en exécute une copie
// octet pour octet dans un dépôt temporaire, dont node_modules pointe vers celui du dépôt.
// Un cas en collision exige aussi le motif de la sortie : un échec de chargement (js-yaml absent)
// sort lui aussi en 1 et ne doit pas passer pour une collision.
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const SCRIPT = join(REPO_ROOT, "_scripts", "check-slug-uniqueness.mjs");
const SLUG = "filtre-a-huile";
const CANON = `wiki/gamme/${SLUG}.md`;

function fiche(revisionOf) {
  const lines = ["---", "entity_type: gamme", `slug: ${SLUG}`];
  if (revisionOf) lines.push("revision_of:", `  path: ${revisionOf}`, `  sha256: "${"0".repeat(64)}"`);
  return [...lines, "---", "body", ""].join("\n");
}

function run(files) {
  const root = mkdtempSync(join(tmpdir(), "slug-uniqueness-"));
  try {
    mkdirSync(join(root, "_scripts"));
    copyFileSync(SCRIPT, join(root, "_scripts", "check-slug-uniqueness.mjs"));
    symlinkSync(join(REPO_ROOT, "node_modules"), join(root, "node_modules"), "dir");
    for (const [path, text] of Object.entries(files)) {
      mkdirSync(dirname(join(root, path)), { recursive: true });
      writeFileSync(join(root, path), text);
    }
    return spawnSync(process.execPath, [join(root, "_scripts", "check-slug-uniqueness.mjs")],
      { encoding: "utf8" });
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

const ADMITTED = [
  ["canon seul", { [CANON]: fiche() }],
  ["canon et proposition qui le déclare", { [CANON]: fiche(), [`proposals/${SLUG}.md`]: fiche(CANON) }],
];
const COLLISIONS = [
  ["proposition sans déclaration", { [CANON]: fiche(), [`proposals/${SLUG}.md`]: fiche() }],
  ["proposition qui déclare un autre canon",
    { [CANON]: fiche(), [`proposals/${SLUG}.md`]: fiche("wiki/gamme/autre.md") }],
  ["fiche déclarante hors de proposals/", { [CANON]: fiche(), "wiki/gamme/doublon.md": fiche(CANON) }],
  ["deux propositions sans canon",
    { "proposals/ancienne.md": fiche(CANON), [`proposals/${SLUG}.md`]: fiche(CANON) }],
  ["trois fichiers",
    { [CANON]: fiche(), "proposals/ancienne.md": fiche(CANON), [`proposals/${SLUG}.md`]: fiche(CANON) }],
];

for (const [name, files] of ADMITTED) {
  test(`admis : ${name}`, () => {
    const r = run(files);
    assert.equal(r.status, 0, r.stdout + r.stderr);
    assert.match(r.stdout, /^check-slug-uniqueness: OK /);
  });
}

for (const [name, files] of COLLISIONS) {
  test(`collision : ${name}`, () => {
    const r = run(files);
    assert.equal(r.status, 1, r.stdout + r.stderr);
    assert.match(r.stderr, /^check-slug-uniqueness: 1 collision\(s\)\n {2}gamme:filtre-a-huile\n/);
  });
}
