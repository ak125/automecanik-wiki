# Préparer un candidat WIKI depuis une capture documentaire

Le mode `--document-selection` de `author_from_raw.py` réutilise le lecteur documentaire RAW. Il transforme une sélection explicite de passages et de reformulations en candidat Markdown conforme aux schémas WIKI. Il ne choisit pas les faits à votre place et ne valide pas la fidélité sémantique d'une reformulation.

## Entrées et exécution

Utiliser un checkout RAW de confiance qui fournit `document_contract.read_document` (PR RAW 53, testé sur `3134ea6`) et contient la capture ainsi que ses fichiers référencés. Le module est chargé depuis ce checkout explicitement désigné. Un ancien checkout sans cette API provoque un refus, sans repli sur la lecture du corps JSON.

La sélection JSON respecte `_meta/schema/document-selection.schema.json` : version, slug, langues déclarées de la source et du candidat, date de préparation, UUIDv7 de traçabilité, empreinte du modèle existant, chemin et empreinte du reçu, puis liste des affirmations. Chaque affirmation contient `section`, `start`, `end`, `quote` et `statement`. Les sections admises sont celles de `SECTION_SPEC` dans le producteur existant.

Les positions utilisent les indices Python dans le texte Unicode : début inclus, fin exclue, premier caractère à zéro. `quote` doit être exactement égal à ce passage. Une position hors texte, un doublon de passage ou une section inconnue provoque un refus. Les reformulations trop courtes pour leur section sont refusées ; aucun texte de remplissage n'est ajouté.

```bash
python3 -B _scripts/author_from_raw.py \
  --slug thermostat \
  --raw-root /chemin/checkout-raw-de-confiance \
  --document-selection /chemin/selection.json \
  --out /chemin/dossier-isole/thermostat.md \
  --json
```

Le dossier de sortie doit déjà exister. Le mode documentaire refuse d'écrire dans le dépôt WIKI, le checkout RAW ou le répertoire des propositions d'entrée. Il publie un fichier isolé de façon atomique et exclusive : aucun écrasement, aucun lien symbolique. Sans `--out`, il calcule le candidat et retourne son rapport sans écrire. Ce mode suit le rôle actuel du producteur : préparation d'un candidat isolé, pas dépôt automatique dans le sas canonique.

## Contenu et traçabilité

L'entrée `proposals/<slug>.md` fixe l'identité de l'entité ; son empreinte est obligatoire. Le mode est limité aux gammes existantes. Il reprend le titre, l'identifiant, le `pg_id` et la famille ; il ne copie ni l'ancien corps, ni les anciennes dimensions, ni les statuts de validation. Si la fiche possède déjà un `lineage_id`, il doit être conservé. Sinon la sélection fournit le nouvel UUIDv7 une fois, puis le réutilise pour les reprises.

Le candidat contient les affirmations sélectionnées et une annexe de preuve liée à son `content_hash` : passages exacts, positions, empreintes du reçu, de l'original et du texte, URL, langue déclarée, licence et qualification constatées. Les trois références RAW désignent **une seule capture**, pas trois sources indépendantes. L'empreinte du fichier Markdown candidat figure également dans le rapport JSON.

Le résultat reste `review_status: in_review`, `truth_level: L3`, avec des blocs `inferred` et les exports à faux. Une correspondance exacte du passage ne prouve ni sa vérité, ni sa pertinence pour la gamme, ni la justesse de la traduction. La langue déclarée n'est pas détectée automatiquement. Les données textuelles restent non fiables pour les interfaces ; l'adaptateur échappe l'HTML fourni dans les reformulations et protège la clôture du bloc de preuve, mais ne remplace pas un moteur de rendu sécurisé.

## Validation et étapes suivantes

Les schémas WIKI de frontmatter et de gamme sont vérifiés avant toute sortie. Cela établit la conformité de structure. La décision de validation appartient ensuite à `promotion_decision.canonical_promotion_decision`, également utilisée par le promoteur. Le mode documentaire ne remplace pas ce décideur, ne l'appelle pas implicitement et ne modifie aucun de ses seuils.

L'exemple MAHLE a été évalué séparément avec les évaluateurs réels : candidat bloqué pour diversité de sources, substance insuffisante et niveau L3. Compléter les passages ne suffira pas à résoudre tous ces motifs : le contrôle actuel de diversité compte les `kind` de références et non les documents indépendants. Le dépôt dans le sas existant, son index et son journal restent une opération ultérieure ; l'outil ne remplace aucune proposition canonique.

Les appels du producteur sans `--document-selection` gardent leur comportement précédent. Pas de migration de corpus, d'ajout au catalogue des sources, de nouvelle extraction réseau ni d'export SEO/RAG/chatbot dans ce mode.

## Plusieurs documents et passages par affirmation

La sélection `version: 1.1.0` conserve l'identité, la langue du candidat, la date et l'empreinte du modèle. Elle remplace les trois champs source racine par `documents` : une liste de 1 à 10 entrées contenant `id`, `receipt_path`, `receipt_sha256` et `source_language`. Les identifiants sont uniques et locaux à la sélection. Le format 1.0.0 reste accepté ; sa sortie est conservée à l'octet près sur le témoin MAHLE.

Chaque affirmation conserve `section` et `statement`, mais utilise `anchors` : de 1 à 10 passages contenant `document_id`, `start`, `end` et `quote`. Une affirmation peut ainsi citer plusieurs documents sans être répétée dans le texte éditorial. Chaque rubrique reçoit uniquement les identifiants des extractions auxquelles ses affirmations se réfèrent.

Tous les reçus passent par le lecteur RAW avec leur empreinte attendue. Une seconde capture corrompue bloque tout le candidat. Les identifiants dupliqués, les alias d'un reçu, les extractions de texte identiques, les documents non utilisés et les passages répétés sont refusés. Ajouter des captures inutiles pour gonfler les références n'est donc pas accepté.

L'annexe lie au candidat les documents et les passages de chaque affirmation. Les compteurs `documents_selected`, `anchors_selected` et `claims_selected` décrivent ces objets, sans certifier leur indépendance. Deux URL peuvent provenir du même éditeur ou reprendre la même information. L'adaptateur ne qualifie pas cette indépendance et ne transforme pas une convergence apparente en fait validé.

## Limites mesurées du parcours de validation

Les contrôles et le seuil 0,85 sont inchangés. Avec le moteur `legacy`, la confiance absente vaut `medium`. Sur une entrée synthétique contenant toutes les rubriques attendues et un lien résolu, uniquement des références RAW donnent 0,74 ; avec deux types de références, 0,84. Ce sont des reproductions de la formule, pas des scores de qualité du candidat réel. Le schéma accepte une confiance `high` documentée, mais l'adaptateur ne l'attribue pas lui-même.

Le candidat réel thermostat reste à 0,24 et L3. Le mapping éditorial du producteur et les titres attendus par le score historique ne coïncident pas entièrement. Il faudra aligner les critères sur les contrats éditoriaux et la provenance réellement vérifiée avant de présenter ce raccordement comme un parcours complet de validation. Ajouter un alias `external_url`, du remplissage ou des liens artificiels pour passer les contrôles n'est pas une résolution de ce défaut.

Les deux pages supplémentaires examinées, HELLA thermostat et MAHLE guide thermostat, ont été refusées par le scan de secrets sur l'original entier. Aucun nouveau fichier source n'a été conservé lors de ces deux tentatives. Le test de plusieurs documents utilise donc des fixtures ; l'intégration réelle vérifie le format 1.1.0 sur l'unique capture MAHLE conservée. Voir `_audit/document-proposals/multiple-documents-validation.md` et ses preuves JSON.
