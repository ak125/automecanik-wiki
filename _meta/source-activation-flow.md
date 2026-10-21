# Activation gouvernée des sources

Une source `active` signifie que son archive et les ancres canoniques ont passé le contrôle croisé natif. Elle ne vaut ni relecture éditoriale, ni autorisation juridique, ni promotion de fiche. Le décideur natif et les obligations humaines restent inchangés.

## Commande owner

Depuis une branche propre basée sur le `main` WIKI courant, avec un checkout RAW propre au `main` courant :

```bash
python3 _scripts/activate-sources.py --raw-root /chemin/RAW --key /chemin/prive/ed25519 --slugs source_a source_b
```

La commande vérifie les origines et la CI des deux SHA, prépare un arbre temporaire, puis exécute `quality-gates.py --cross-repo` avec `AUTOMECANIK_RAW_PATH` explicitement fixé. Elle revérifie les bases et leur propreté après le contrôle. Seulement après succès, elle signe un reçu et modifie les statuts demandés. Elle ne pousse rien et ne promeut aucune fiche. Toute source doit déjà exister avec `status: to_capture` et une référence RAW.

Le reçu JSON sous `_audit/source-activations/` contient les transitions exactes, les SHA des bases, la sortie du contrôle et une empreinte de tous les fichiers de travail suivis ou non ignorés, hors reçus. Tout changement de contenu ou de code après qualification invalide ce reçu. Refaire la qualification depuis des bases propres si main avance ; ne pas retoucher le reçu.

## Confiance et CI

La signature utilise [OpenSSH ssh-keygen -Y sign/verify](https://man.openbsd.org/ssh-keygen), avec un espace de noms dédié. La clé privée reste hors dépôts, accessible à son propriétaire uniquement. La CI possède seulement la clé publique dans `_meta/source-activation-trust.json` et ne reçoit aucun accès au RAW privé.

Le garde lit les clés autorisées dans la **base Git**, jamais dans la nouvelle version proposée. Une nouvelle clé doit donc être intégrée et examinée dans une PR distincte avant de servir à une activation. Le signataire owner atteste le contrôle exécuté sur l’hôte ; la CI vérifie son authenticité et sa correspondance exacte aux entrées actuelles, elle ne prétend pas relire RAW.

Après génération, exécuter le garde avec la base main, les contrôles natifs et le dry-run de promotion, puis soumettre le catalogue et le reçu ensemble en PR normale. Les hooks utilisent HEAD comme base ; la CI de PR utilise origin/main ; les pushes main utilisent le commit avant le push. Une activation directe sans reçu valide est refusée.

## Révocation et limites

Retirer une clé autorisée par un commit examiné empêche son utilisation à partir de la nouvelle base. Aucun reçu historique ni archive n’est supprimé. Le garde ne transforme pas un reçu en validation humaine et ne change pas la substance, la diversité, la sécurité, la fraîcheur ou les seuils de promotion.

Le propriétaire de la clé est une autorité de qualification : protéger cette clé comme la capacité d’attester un contrôle. Elle n’est enregistrée auprès d’aucun serveur SSH ou service GitHub et ne donne pas d’accès réseau supplémentaire.
