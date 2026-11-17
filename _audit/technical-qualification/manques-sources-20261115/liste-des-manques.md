# Manques de sources et captures — fiches `wiki/gamme` (mandat AC-11, 2026-11-15)

Audit en lecture seule, département 11 (qualification technique) avec le 09 (sources RAW).
Ce document n'est ni une révision de fiche ni une décision de promotion. Aucune fiche n'est modifiée.

## 1. Base et périmètre

- WIKI : `origin/main` à `67e49d821f17a73692ca0eb976791bcb092483ca`.
- RAW : captures sur la branche `claude/raw-qualif11-sources-gammes-20261115`, à partir de `401314c`. Commits `c852637` (tour 1) et `4b4de71` (tour 2).
- Fiches couvertes : 4 fiches `wiki/gamme`. `filtre-a-huile` est exclue (mandat T).

| Fiche                              | sha256 à 67e49d8                                                   |
| ---------------------------------- | ------------------------------------------------------------------ |
| `wiki/gamme/filtre-a-air.md`       | `3217ce282740ae50f5caadef5b78b9a8fd994680890bf09a926d632440eb8671` |
| `wiki/gamme/filtre-a-carburant.md` | `cf85c2a5e56c6a64483a5119319991398b5dfdcf81260a1e67cc753f9d9f0208` |
| `wiki/gamme/filtre-d-habitacle.md` | `28915d6cde4c6c3f88d21fd5c91541933befd2b75c37dc45bdda3447ccf66572` |
| `wiki/gamme/plaquette-de-frein.md` | `64642c141f7ac36e6fad8bf1a7c8836568c70e17bda6329e92cdcada3aa62f01` |

La fiche plaquette-de-frein a été modifiée en dernier par `35d057b`. Elle est identique à `88f9f88`, la révision citée par le mandat.

## 2. Méthode

1. Chaque fiche est découpée en affirmations : valeurs, procédures, intervalles, relations diagnostiques, consignes de sécurité. Un identifiant stable est attribué à chacune : `P` pour plaquette, `A` pour filtre à air, `C` pour filtre à carburant, `H` pour habitacle.
1. La profondeur est notée selon la règle D4 d'ADR-131, dans son état `proposed`. Elle vaut `complete` si l'affirmation relève d'une famille de sécurité, porte une valeur chiffrée, une procédure ou une relation diagnostique. Sinon elle vaut `allegee`.
1. Pour chaque affirmation, on compte les domaines d'autorité qui la portent, à partir des captures RAW : celles déjà citées par la fiche et celles du présent mandat.
1. Les captures passent par la voie existante : worklist `discovery.mode: provided`, puis `_scripts/auto-capture-runner.py --commit --rate-limit 2`, puis les gates RAW A–J. Aucun nouvel outil de scraping n'est utilisé.

### Classement provisoire des domaines d'autorité

Le complément d'ADR-131 qui définit les domaines (mandat S, WIKI #134, Vault #413) n'est pas ratifié au moment de l'audit. Ce classement est un **classement de travail**, à reconfronter au texte final.

| Domaine              | Exemples dans ce lot                                 | Compté comme autorité                             |
| -------------------- | ---------------------------------------------------- | ------------------------------------------------- |
| Constructeur         | Renault (renault.fr, user-manual.renault.com), Dacia | oui                                               |
| Équipementier        | ZF, Brembo, Delphi, FILTRON, MANN-FILTER, Valeo      | oui                                               |
| Norme technique      | ECE R90 (unece.org)                                  | oui, mais aucune capture : domaine hors allowlist |
| Formation            | aucune source dans l'allowlist                       | oui, mais aucune capture                          |
| Comparateur / réseau | Carglass, ByMyCar, Vroomly, iDGarages                | non                                               |
| Encyclopédie         | Wikipédia                                            | non, corroboration seulement                      |
| RAW recyclé          | `recycled/rag-knowledge/**`                          | non (bootstrap)                                   |

Notation dans les tableaux :

- **n** : nombre de domaines d'autorité distincts portant l'affirmation.
- **partiel** : la source porte le fond de l'affirmation, mais pas sa valeur exacte ou son contexte exact.
- **⚠ contradiction** : une source d'autorité dit le contraire.

## 3. Captures du mandat

16 captures, toutes au statut `CAPTURED_NEEDS_REVIEW`, gates RAW A–J PASS (42 auto-captures scannées). Les chemins sont relatifs à la racine RAW.

| worklist_id                                              | Domaine       | Tour | Chemin                                                                                                              | content_hash                                                              |
| -------------------------------------------------------- | ------------- | ---- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| wl-filtre-a-air-filtron-nettoyer-20261115                | équipementier | 1    | `sources/auto-captures/filtre-a-air/filtron-eu-wl-filtre-a-air-filtron-nettoyer-20261115-6cd1da29.md`               | `sha256:6cd1da291af47d8b4330830eeb63210c2a9da86aa20459f21441afc5f6fdeff3` |
| wl-filtre-a-air-renault-notice-antipollution-20261115    | constructeur  | 1    | `sources/auto-captures/filtre-a-air/user-manual-renault-com-wl-filtre-a-air-renault-notice-antip-a5204810.md`       | `sha256:a520481069dc57ce0a766526dde3fe4f496f30adbec4d16566039864a2076d3e` |
| wl-filtre-a-air-renault-notice-filtres-20261115          | constructeur  | 1    | `sources/auto-captures/filtre-a-air/user-manual-renault-com-wl-filtre-a-air-renault-notice-filtr-02aebf07.md`       | `sha256:02aebf07d6b9314413d35e9b8d9dafec612230960e5f7c970eecfea76ec1a2d7` |
| wl-filtre-a-carburant-filtron-hiver-20261115             | équipementier | 1    | `sources/auto-captures/filtre-a-carburant/filtron-eu-wl-filtre-a-carburant-filtron-hiver-20261115-607df51b.md`      | `sha256:607df51b42be9db0b5a67820e33a5f3ef8cbd5553424d7b401aac2af1e96d5fe` |
| wl-filtre-a-carburant-delphi-common-rail-20261115        | équipementier | 2    | `sources/auto-captures/filtre-a-carburant/delphiautoparts-com-wl-filtre-a-carburant-delphi-common-rail-827c5aac.md` | `sha256:827c5aacc1e786378f302b0c16de4cf0b0944d32844e004e5c8ec3ec958c9153` |
| wl-filtre-a-carburant-delphi-remplacement-20261115       | équipementier | 2    | `sources/auto-captures/filtre-a-carburant/delphiautoparts-com-wl-filtre-a-carburant-delphi-remplacemen-10616d4f.md` | `sha256:10616d4fc0437d316abde5c72271548c6d41561a47a14552d0abfc5c55710cad` |
| wl-filtre-a-carburant-renault-notice-reamorcage-20261115 | constructeur  | 2    | `sources/auto-captures/filtre-a-carburant/user-manual-renault-com-wl-filtre-a-carburant-renault-notice-48436346.md` | `sha256:48436346151898a33856efb2d398894410c58ab2c2b205f377d7f0993e22ab2c` |
| wl-filtre-a-carburant-renault-notice-eau-20261115        | constructeur  | 2    | `sources/auto-captures/filtre-a-carburant/user-manual-renault-com-wl-filtre-a-carburant-renault-notice-7ed46e83.md` | `sha256:7ed46e83bdce6375818ca5aee205fb5d3f3760bb700b4e242febeae61f27021d` |
| wl-filtre-d-habitacle-mann-produit-20261115              | équipementier | 1    | `sources/auto-captures/filtre-d-habitacle/mann-filter-com-wl-filtre-d-habitacle-mann-produit-20261115-fcfcfed6.md`  | `sha256:fcfcfed6dd0c19f47714c1a2a38af2eea310feb17850b2df7bd04cdab3559f43` |
| wl-filtre-d-habitacle-valeo-20261115                     | équipementier | 1    | `sources/auto-captures/filtre-d-habitacle/valeo-com-wl-filtre-d-habitacle-valeo-20261115-f4cdf2fe.md`               | `sha256:f4cdf2fee767bfe0a86a42551d3d9a51f83118bde122d0a7622611acf6b6d553` |
| wl-filtre-d-habitacle-renault-climatisation-20261115     | constructeur  | 1    | `sources/auto-captures/filtre-d-habitacle/renault-fr-wl-filtre-d-habitacle-renault-climatisation-20261-3618c53c.md` | `sha256:3618c53cb4bd29d8bcd6f9ac6b187b4a3c78494767d1646531048a10c3167dc4` |
| wl-filtre-d-habitacle-renault-mag-clim-20261115          | constructeur  | 1    | `sources/auto-captures/filtre-d-habitacle/renault-fr-wl-filtre-d-habitacle-renault-mag-clim-20261115-2059fa62.md`   | `sha256:2059fa6293b843e3e58b4b2f59a9f5f0228ae10f3ed9f1fac7badee6f82c6730` |
| wl-plaquette-de-frein-dacia-freinage-20261115            | constructeur  | 1    | `sources/auto-captures/plaquette-de-frein/dacia-fr-wl-plaquette-de-frein-dacia-freinage-20261115-3f125443.md`       | `sha256:3f125443404426108c19e95c65199c542ca600ecfba92272dd1d8e23e9b4342c` |
| wl-plaquette-de-frein-renault-freins-20261115            | constructeur  | 1    | `sources/auto-captures/plaquette-de-frein/renault-fr-wl-plaquette-de-frein-renault-freins-20261115-39e27e06.md`     | `sha256:39e27e065d034ad0cf1ec6df1fe4eb652b063da7c5b028578345e156aed7d11b` |
| wl-plaquette-de-frein-renault-notice-niveaux-20261115    | constructeur  | 1    | `sources/auto-captures/plaquette-de-frein/user-manual-renault-com-wl-plaquette-de-frein-renault-notice-bab909a5.md` | `sha256:bab909a536b8eb87a4cc78aca78f9c34626aeb8ca2e7f59455356cce92651b47` |
| wl-plaquette-de-frein-renault-notice-temoins-20261115    | constructeur  | 2    | `sources/auto-captures/plaquette-de-frein/user-manual-renault-com-wl-plaquette-de-frein-renault-notice-248acd34.md` | `sha256:248acd3465588a2232662b8423bc99468cff5635f4ca9b463cdc83e274ba6487` |

### Refus respectés, sans contournement

| Cible                                 | Résultat                               | Suite                     |
| ------------------------------------- | -------------------------------------- | ------------------------- |
| citroen.fr, page freinage             | HTTP 403                               | abandonnée                |
| peugeot.fr, page révision             | HTTP 403                               | abandonnée                |
| HELLA be-fr, page plaquettes          | HTTP 404                               | abandonnée                |
| MANN-FILTER, communiqué de presse     | Gate J : PII possible (adresse e-mail) | fichier non conservé      |
| vroomly.com (item worklist antérieur) | refus robots.txt                       | reste `TODO`, hors mandat |

### Sources du 7 novembre (FILTRON S01, MANN-FILTER P01, notice MANN, P02)

Aucune n'est retrouvable dans RAW, ni sur `origin/main` ni sur une branche distante, et aucune n'est citée par une fiche. Elles sont notées **non retrouvées**. Les captures FILTRON et MANN-FILTER du présent mandat les remplacent sur leur fond, sans prétendre être les mêmes documents.

## 4. Journal des tours de capture

La boucle ADR-131 complète (qualification, reprise ciblée, requalification) n'a pas pu tourner : le skill `qualification-technique` 0.3.0 et le complément d'ADR-131 n'existent pas encore (voir §9). Seuls les tours de capture et les taux de corroboration sont journalisés.

| Tour | Items en worklist | Capturés                        | Utiles | Questions de reprise traitées                                                   |
| ---- | ----------------- | ------------------------------- | ------ | ------------------------------------------------------------------------------- |
| 1    | 15                | 11 (4 refus ou rejets, voir §3) | 11     | second domaine pour chaque fiche ; sources constructeur absentes des 4 fiches   |
| 2    | 5                 | 5                               | 3      | C03/C05 (diagnostic colmatage), C07 (eau), C09 (amorçage), P06 (témoin d'usure) |

Au tour 2, deux captures n'apportent pas de corroboration pleine :

- Twingo (témoins) : la notice n'a pas de témoin d'usure plaquettes, seulement « Témoin d'incident sur circuit de freinage ». P06 reste à un domaine.
- Kangoo 2 ph2 (réamorçage) : procédure constructeur réelle, mais dans un autre contexte (panne sèche), voir C09 ; compte comme partiel.

### Taux de corroboration (affirmations `complete` portées par au moins deux domaines)

| Fiche              | Avant le tour 1 | Après le tour 2  |
| ------------------ | --------------- | ---------------- |
| plaquette-de-frein | 0/29            | 2/29 + 1 partiel |
| filtre-a-air       | 0/9             | 0/9 + 1 partiel  |
| filtre-a-carburant | 0/8             | 2/8 + 1 partiel  |
| filtre-d-habitacle | 0/13            | 4/13 + 1 partiel |

« Avant » compte les sources déjà citées par la fiche. Les quatre fiches ne citaient que des équipementiers, des comparateurs ou du RAW recyclé, jamais deux domaines d'autorité distincts.

## 5. Manques par fiche

### 5.1 plaquette-de-frein (famille freinage, sécurité : toutes les affirmations sont `complete`)

Sources citées par la fiche : équipementiers seulement (ZF, Brembo ×3, Delphi), plus Wikipédia.

| ID  | Affirmation (résumé)                                     | n           | Source qui la porterait                                                                                                            |
| --- | -------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| P01 | La plaquette est un composant de sécurité                | 2           | — (Dacia, Renault freins)                                                                                                          |
| P02 | Rôle de l'étrier, pistons isolants, ressorts de rappel   | 1           | manuel de réparation constructeur ; formation                                                                                      |
| P03 | Étrier flottant / fixe                                   | 1           | manuel constructeur ; formation                                                                                                    |
| P04 | Accessoires de montage                                   | 1           | notice de montage d'un second équipementier (TRW, Bosch, Textar)                                                                   |
| P05 | Un son strident signale la fin d'usure                   | 1 ⚠         | **contradiction Dacia** (voir §6) ; source constructeur de l'indicateur acoustique                                                 |
| P06 | Témoin électronique d'usure                              | 1           | notice d'un modèle équipé d'un témoin (candidats : Master 3, notice EN `warning-lights-11` ; notice `/en/notice/20176/indicators`) |
| P07 | Un montage incorrect provoque des bruits                 | 1           | second équipementier                                                                                                               |
| P08 | Les prescriptions constructeur priment                   | 1           | notice constructeur (renvoi au réseau)                                                                                             |
| P09 | Matériau de friction                                     | 1           | second équipementier ; formation                                                                                                   |
| P10 | Type et position de l'indicateur d'usure                 | 1           | manuel constructeur                                                                                                                |
| P11 | Remplacement par essieu et à chaque changement de disque | 1           | constructeur (réseau Renault/Dacia)                                                                                                |
| P12 | Homologation ECE R90                                     | 1           | **norme technique : unece.org hors allowlist** (patch proposé, non appliqué)                                                       |
| P13 | Intervention par du personnel compétent                  | 1 + partiel | notice Renault : « spécialiste » pour le circuit hydraulique ; Renault : « techniciens qualifiés »                                 |
| P14 | Respect des flèches de sens                              | 1           | second équipementier                                                                                                               |
| P15 | Côté piston                                              | 1           | second équipementier                                                                                                               |
| P16 | Plaques de guidage                                       | 1           | second équipementier                                                                                                               |
| P17 | Contrôle du coulissement                                 | 1           | second équipementier ; manuel constructeur                                                                                         |
| P18 | Graisse adaptée                                          | 1           | second équipementier                                                                                                               |
| P19 | Couples de serrage                                       | 1           | manuel de réparation constructeur (valeurs par modèle)                                                                             |
| P20 | Après montage : pédale et niveau de liquide              | 1 + partiel | notice Renault (niveau lié à l'usure des garnitures, cote MINI)                                                                    |
| P21 | Rodage                                                   | 1           | second équipementier ; constructeur                                                                                                |
| P22 | Pas d'air comprimé, poussières                           | 1           | second équipementier ; formation (hygiène atelier)                                                                                 |
| P23 | Contrôles réguliers                                      | 2           | — (Dacia, Renault, notice). Le « 2 ans / 20 000 km » de Dacia est une préconisation réseau, à citer comme telle                    |
| P24 | Facteurs de vitesse d'usure                              | 2 partiels  | Renault (VE / thermique), Dacia (frein moteur)                                                                                     |
| P25 | Quand remplacer                                          | 1 ⚠         | contradiction Dacia sur le bruit (voir §6)                                                                                         |
| P26 | Indicateurs remplacés à chaque fois                      | 1           | second équipementier                                                                                                               |
| P27 | Logo du fournisseur première monte                       | 1           | second équipementier                                                                                                               |
| P28 | Marques de qualité                                       | 1           | norme technique (R90)                                                                                                              |
| P29 | `diagnostic_relations` : `brake_noise_metallic`          | 1 ⚠         | contradiction Dacia (voir §6)                                                                                                      |

Les questions Q1 à Q5 de la FAQ reprennent P25, P11, P05, P26 et P21 et héritent de leur statut.

Faits constructeur absents de la fiche :

- Liquide de frein tous les 4 ans ou 120 000 km (Dacia, Renault).
- Le niveau baisse avec l'usure des garnitures sans jamais descendre sous la cote MINI (notice Renault).
- Toute intervention sur le circuit hydraulique impose le remplacement du liquide par un spécialiste (notice Renault).
- Le frein moteur réduit l'usure (Dacia).

**Affirmations à un seul domaine** : P02–P04, P06–P22 et P25–P28, soit 24 sur 29. P05 et P29 sont en contradiction entre deux domaines ; seules P01, P23 (et P24 en partiel) atteignent deux domaines.

### 5.2 filtre-a-air (famille filtration, `risk_level: low`)

Les deux sources de `diagnostic_relations` (`oem_filter_maintenance_general`, `bosch_fad_2020`) sont `to_capture` et n'ont jamais été capturées.

| ID  | Affirmation (résumé)                                              | Profondeur | n          | Source qui la porterait                                                                                                             |
| --- | ----------------------------------------------------------------- | ---------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| A01 | Définition                                                        | allegee    | —          | —                                                                                                                                   |
| A02 | Filtre colmaté : perte de puissance, surconsommation, imbrûlés    | complete   | 2 partiels | notice Renault (« rendement ») ; Delphi / MAHLE / Garrett selon la PR WIKI #128                                                     |
| A03 | Remplacement tous les 30 000 km                                   | complete   | 0 ⚠        | FILTRON : « dans de nombreux cas… tous les 15 000 kilomètres ou une fois par an » ; notice Renault : renvoi au document d'entretien |
| A04 | Plus fréquent en milieu poussiéreux                               | complete   | 0          | constructeur (conditions sévères du carnet) ; second équipementier                                                                  |
| A05 | Porosité progressive                                              | allegee    | 0          | équipementier                                                                                                                       |
| A06 | Filtre coton huilé : coût 3 à 5 fois supérieur, procédure stricte | complete   | 0          | fabricant du filtre réutilisable ; le chiffre « 3–5× » n'a pas de source                                                            |
| A07 | Filtre papier non nettoyable                                      | complete   | 1          | FILTRON (nettoyage à l'air : capacité réduite, médium endommagé) ; constructeur à trouver                                           |
| A08 | Pas immédiatement dangereux, encrasse les injecteurs              | complete   | 0          | équipementier injection ; constructeur                                                                                              |
| A09 | « Souffle à l'admission »                                         | complete   | 0          | aucune source repérée : à retirer ou à sourcer                                                                                      |
| A10 | Filtre à huile à chaque vidange                                   | —          | —          | hors périmètre (filtre-a-huile, mandat T)                                                                                           |
| A11 | Filtre à carburant : 60 000 km en diesel                          | complete   | 0 ⚠        | contredit la fiche filtre-a-carburant (voir §6)                                                                                     |
| A12 | 15 000 km habitacle contre 30 000 km moteur                       | complete   | 1          | partie habitacle portée (voir H05) ; partie moteur sans source                                                                      |

Le seul partiel est A02. **Affirmations à zéro ou un domaine** : A03, A04, A06–A09, A11 et A12.

Chevauchement : la PR WIKI #128 révise cette fiche (Delphi, MAHLE, Garrett, HELLA) et retire le 30 000 km. Ce chevauchement est signalé, pas arbitré.

### 5.3 filtre-a-carburant (famille filtration)

Sources citées par la fiche : comparateurs (Vroomly, iDGarages) et RAW recyclé, sans domaine d'autorité.

| ID  | Affirmation (résumé)                                                        | Profondeur | n                       | Source qui la porterait                                                                                                                                                                                             |
| --- | --------------------------------------------------------------------------- | ---------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C01 | Retient l'eau et les impuretés                                              | allegee    | 1                       | — (FILTRON, Delphi, même domaine)                                                                                                                                                                                   |
| C02 | Remplacé plus souvent en diesel                                             | complete   | 0                       | constructeur (plan d'entretien par motorisation)                                                                                                                                                                    |
| C03 | Perte de puissance en montée, à-coups, démarrage difficile                  | complete   | 2 partiels              | Delphi ×2 (équipementier) + notice Renault antipollution (rendement)                                                                                                                                                |
| C04 | Cliquetis, ratés, odeur de carburant                                        | complete   | 0                       | constructeur. L'odeur persistante de la notice Kangoo 2 est une consigne d'arrêt de sécurité, dans un autre contexte                                                                                                |
| C05 | Filtre = perte progressive, injecteur = un cylindre mort, la valise tranche | complete   | 1 partiel               | Delphi (manomètre, manuels de diagnostic) ; constructeur à trouver                                                                                                                                                  |
| C06 | Intervalles 15–20 000 km, HDI/TDI 20–30 000 km, essence 60 000 km           | complete   | 2 (cadre) / 0 (valeurs) | le principe « la préconisation constructeur prime » est porté (notice Renault, Delphi). Aucune valeur chiffrée n'est corroborée ; Delphi diverge (« tous les 30 000 miles ou tous les deux ans », donné en exemple) |
| C07 | Eau, corrosion, purge régulière                                             | complete   | 2 (eau) / 0 (corrosion) | eau : FILTRON (décanteur) + notice Kangoo (« Clean Diesel Filter » → réseau). La purge par l'utilisateur ou par le réseau reste à préciser                                                                          |
| C08 | Le diesel premium prolonge la durée de vie                                  | allegee    | 0                       | pétrolier ou équipementier                                                                                                                                                                                          |
| C09 | FAQ : purger après remplacement, « pompez jusqu'à sentir une résistance »   | complete   | 1 partiel               | notice Kangoo 2 ph2 : poire d'amorçage, mais **après une panne sèche**, pas après remplacement ; Delphi ne traite le pré-remplissage qu'en vidéo                                                                    |
| C10 | À-coups au ralenti = injecteur/bobine                                       | complete   | 0                       | la bobine ne concerne que l'essence, mélangée ici au diesel ; constructeur                                                                                                                                          |

Faits d'autorité absents de la fiche :

- Paraffine du gazole en hiver ; vider le décanteur avant l'hiver ; remplacer avant chaque hiver (FILTRON).
- Dépression maximale de 200 à 300 mbar au ralenti entre filtre et pompe (Delphi).
- Remplacement plutôt réservé aux professionnels, à cause du risque de fuite de carburant (Delphi).

**Affirmations à zéro ou un domaine** : C02, C04, C05, les valeurs de C06, la corrosion de C07, C09 et C10.

### 5.4 filtre-d-habitacle (famille filtration)

Sources citées par la fiche : comparateurs (Carglass, ByMyCar) et RAW recyclé, sans domaine d'autorité.

| ID  | Affirmation (résumé)                                       | Profondeur | n          | Source qui la porterait                                                                                                                             |
| --- | ---------------------------------------------------------- | ---------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| H01 | Filtre pollens et poussières                               | allegee    | 2          | —                                                                                                                                                   |
| H02 | Le charbon actif retient NOx et ozone                      | allegee    | 1          | — (MANN, Valeo, même domaine)                                                                                                                       |
| H03 | « Le charbon actif retient jusqu'à 90 % des allergènes »   | complete   | 0 ⚠        | **attribution erronée** : chez MANN, le 90 % porte sur les gaz et odeurs (CUK) ; c'est le filtre polyphénol qui annonce plus de 95 % des allergènes |
| H04 | Polyphénol : « jusqu'à 92 % » des particules allergisantes | complete   | 0          | non porté : MANN donne plus de 95 %, Valeo ne donne pas de chiffre                                                                                  |
| H05 | 15–20 000 km ou une fois par an, plus souvent en ville     | complete   | 2          | — (Renault climatisation à l'identique ; MANN et Valeo 15 000 km / an). Écart : le magazine Renault dit « au minimum une fois tous les deux ans »   |
| H06 | Idéalement au printemps                                    | complete   | 0          | constructeur                                                                                                                                        |
| H07 | Zone rurale ou meilleur filtre : intervalle plus long      | complete   | 1 partiel  | Valeo (« selon l'environnement ») ; constructeur                                                                                                    |
| H08 | Buée persistante                                           | complete   | 1          | MANN ; constructeur                                                                                                                                 |
| H09 | Odeurs (relation `odeur_habitacle`)                        | complete   | 2          | — (MANN + magazine Renault : champignons, bactéries, odeurs)                                                                                        |
| H10 | Débit d'air faible                                         | complete   | 2 partiels | MANN, Valeo + Renault                                                                                                                               |
| H11 | Ventilation bruyante                                       | complete   | 1          | MANN (« bruits étranges » dus aux dépôts) ; constructeur                                                                                            |
| H12 | Climatisation moins efficace                               | complete   | 2          | — (MANN + Renault climatisation)                                                                                                                    |
| H13 | Allergies                                                  | complete   | 2          | — (MANN + Renault, filtre anti-allergène)                                                                                                           |
| H14 | Erreurs de montage (sens du flux, calage)                  | complete   | 0          | notice de montage équipementier ; notice constructeur                                                                                               |
| H15 | Derrière la boîte à gants, 10 minutes sans outil           | complete   | 0          | notice constructeur par modèle. La valeur varie selon le véhicule ; telle quelle, elle se généralise mal                                            |
| H16 | Distinct du filtre à air moteur                            | allegee    | —          | —                                                                                                                                                   |

**Affirmations à zéro ou un domaine** : H03, H04, H06, H07, H08, H11, H14 et H15.

## 6. Contradictions et anomalies relevées

Elles sont signalées sans être corrigées, car aucune fiche n'est modifiée.

1. **Bruit d'usure des plaquettes (P05, P25, P29).** La fiche, d'après ZF et Delphi, dit qu'un son strident signale la fin d'usure. Dacia, constructeur, écrit au contraire : « En cas de plaquette de frein usée, lors du freinage un bruit sourd se fait entendre… Au contraire, un bruit aigu n'est pas inquiétant. » Les deux domaines se contredisent sur une famille de sécurité. Il faut une troisième source (manuel constructeur ou formation) avant tout verdict `conserver`.
1. **Intervalle du filtre à air (A03).** La fiche dit 30 000 km sans source. FILTRON dit 15 000 km ou un an « dans de nombreux cas ». Renault renvoie au document d'entretien. La PR #128 retire déjà le chiffre.
1. **Intervalle du filtre à carburant diesel, entre deux fiches (A11 et C06).** filtre-a-air dit 60 000 km en diesel ; filtre-a-carburant dit 20–30 000 km en HDI/TDI et réserve les 60 000 km à l'essence.
1. **Charbon actif et allergènes (H03).** Le 90 % est attribué au mauvais type de filtre (voir §5.4).
1. **Amorçage du filtre diesel (C09).** La procédure constructeur trouvée porte sur une panne sèche. L'appliquer au remplacement du filtre demande une source dédiée ; verdict attendu : `preciser`.
1. **Diagnostic express (C10).** La bobine n'existe qu'en essence ; l'affirmation mélange essence et diesel.
1. **Identifiant de gamme (filtre-a-air).** La fiche porte `pg_id: 510` ; l'item de worklist RAW porte 8.
1. **Export SEO des fiches non sécurité.** filtre-a-carburant et filtre-d-habitacle sont TIER A avec `exportable.seo: true`, alors que leur section « Points à vérifier » dit « exportable.seo reste false ». Elles ne citent aucune capture `sources/auto-captures/`.

## 7. Questions de reprise par fiche (entrée des tours suivants)

- **plaquette-de-frein** : trancher le bruit d'usure (aigu ou sourd) ; trouver une notice avec témoin d'usure (P06) ; trouver un second équipementier pour la procédure de montage (P14–P18, P21, P22, P26) ; couples de serrage par modèle (P19) ; norme R90, qui suppose l'allowlist unece.org.
- **filtre-a-air** : remplacer ou sourcer le 30 000 km ; sourcer A06, A08 et A09 ou les retirer ; se coordonner avec la PR #128.
- **filtre-a-carburant** : intervalles chiffrés par constructeur et par motorisation ; amorçage après remplacement (notice Renault de la procédure réseau, ou équipementier en texte) ; scinder C10 entre essence et diesel.
- **filtre-d-habitacle** : reformuler H03 et H04 d'après MANN ; source constructeur pour le printemps (H06) et l'accès au filtre (H15) ; notice de montage pour H14.

## 8. Sources candidates restantes

| Besoin                        | Candidat                                                                                      | Obstacle                                       |
| ----------------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Norme ECE R90                 | unece.org, texte du règlement R90                                                             | domaine hors allowlist : PR RAW à fusion owner |
| Formation                     | organisme de formation automobile ou manuel de formation                                      | aucun domaine de formation dans l'allowlist    |
| Témoin d'usure plaquettes     | notices user-manual.renault.com (Master 3 `warning-lights-11`, `/en/notice/20176/indicators`) | à capturer au tour suivant                     |
| Second équipementier freinage | TRW, Bosch, Textar                                                                            | domaines à vérifier dans l'allowlist           |
| Constructeurs PSA             | citroen.fr, peugeot.fr                                                                        | HTTP 403 respecté ; aucun contournement        |

## 9. Points bloqués

- **Points 3 à 6 du mandat** (jeu de référence, variance, banc, durcissements) : ils attendent le mandat S et son complément (WIKI #134, Vault #413) et le skill 0.3.0. Au moment de l'audit, Vault #413 en est à `32b644b` et WIKI #134 à `52c9bb2`, et la branche du mandat S porte le skill 0.2.0.
- **Boucle ADR-131 par gamme** : elle demande le skill dans sa révision finale et la définition des domaines d'autorité, qui ne sont pas encore ratifiés.
- **Norme technique et formation** : aucune capture n'est possible sans élargir l'allowlist, ce qui demande une PR RAW fusionnée par l'owner.
