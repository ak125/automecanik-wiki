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

L'exemple MAHLE a été évalué séparément avec les évaluateurs réels : candidat bloqué pour diversité de sources, substance insuffisante et niveau L3. Un candidat bloqué reste un travail à compléter, sans approbation humaine systématique ajoutée au flux. Le dépôt dans le sas existant, son index et son journal restent une opération ultérieure ; l'outil ne remplace aucune proposition canonique.

Les appels du producteur sans `--document-selection` gardent leur comportement précédent. Pas de migration de corpus, d'ajout au catalogue des sources, de nouvelle extraction réseau ni d'export SEO/RAG/chatbot dans ce mode.
