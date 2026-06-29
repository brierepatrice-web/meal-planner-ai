# Operating System

Ce dossier contient les conventions de la v1 du systeme.

## Source De Verite

Toutes les donnees modifiables vivent dans `data/`.

- `data/profile/` decrit la maison, les equipements et les modes actifs.
- `data/recipes/` contient les recettes principales, accompagnements et lunchs.
- `data/inventory/` contient l'inventaire alimentaire.
- `data/planning/` contient les contraintes hebdomadaires et achats recurrents.
- `data/history/` conserve les semaines consommees.
- `data/drafts/` conserve les plans en brouillon et les recettes pending non encore actives.
- `data/plans/` et `data/grocery_lists/` conservent les sorties generees.

## Regle D'Ecriture De L'Inventaire

Un seul composant peut modifier `data/inventory/`: le Consumption Agent, via `scripts/consume_plan.py`.

Les autres agents peuvent lire l'inventaire pour planifier, scorer ou eviter des achats inutiles, mais ils ne doivent jamais deduire, supprimer ou modifier des articles d'inventaire.

Le Grocery Agent retire seulement des articles de la liste d'epicerie proposee lorsqu'ils sont deja disponibles; il ne retire rien de l'inventaire.

## Recettes

Chaque recette utilise un frontmatter YAML simple suivi de sections Markdown.

Champs requis:

- `title`
- `portions`
- `meal_family`
- `protein_type`
- `prep_time`
- `cook_time`
- `active_time`
- `equipment_required`
- `preferred_seasons`
- `effort_level`
- `leftover_friendly`
- `freezes_well`
- `suggested_side_dishes`
- `category`

Champs requis pour `category: main`:

- `contains_vegetable`
- `contains_starch`
- `leftover_lunch_portions`: nombre de lunchs individuels possibles avec les restants, de `0` a `4`
- `leftover_lunch_style`: `none`, `wrap`, `bol froid`, `restants rechauffes`, `sandwich` ou `salade froide`
- `kids_leftover_ok`
- `adult_leftover_ok`

Champ requis pour `category: lunch`:

- `lunch_temperature`: `cold`, `reheatable` ou `both`

Champ optionnel:

- `mode_tags`
- `lunch_type`: type de lunch comme `wrap`, `sandwich`, `bento`, `salade froide`, `bol froid`, `restants rechauffes` ou `autonome`

Les ingredients sont lus dans la section `## Ingredients`, au format:

```text
- nom de l'ingredient | categorie | quantite
```

Les accompagnements vivent dans `data/recipes/sides/` avec `category: side`. Le champ `suggested_side_dishes` des recettes principales et la colonne `Side` des plans doivent utiliser les titres exacts de ces recettes. Les ingredients des accompagnements sont inclus dans la liste d'epicerie, le score du plan, le HTML des repas et la deduction d'inventaire.

## Restrictions Alimentaires

Le profil maison definit les restrictions alimentaires dans `data/profile/household.md`.

Regle active:

- Crustaces interdits: crevettes, crabe, homard, langoustine, ecrevisse.
- Quinoa interdit.
- Poisson permis.
- Moules permises.
- `protein_type: seafood` est interdit dans les recettes actives parce que le terme est ambigu.
- Les recettes contenant des crustaces doivent etre exclues du bassin actif.

## Modes

Les modes actifs sont listes dans `data/profile/modes.md`.

Les effets de chaque mode sont definis dans `data/profile/mode_definitions.md` avec ces champs:

- `requires_lunches`
- `requires_child_lunches`
- `avoid_lunches`
- `max_active_time_bias`
- `prefer_meal_tags`
- `avoid_meal_tags`
- `prefer_equipment`
- `avoid_equipment`
- `leftover_strategy`
- `grocery_bias`
- `notes`

Les recettes peuvent declarer `mode_tags: []` pour etre favorisees ou evitees selon les modes actifs.

Les seuls modes supportes sont:

- `ecole`: lunchs enfants requis.
- `pas_ecole`: aucun lunch enfant requis; les diners adultes restent generes.

## Brouillon, Commit Et Generation Des Plans

`scripts/plan_week.py` genere un brouillon dans `data/drafts/` avec `status: draft`. Il ne genere pas de liste d'epicerie et n'ajoute pas les nouvelles recettes a `data/recipes/mains/`.

Les recettes nouvelles proposees restent pending dans `data/drafts/<week>_recipes/` jusqu'au commit. Elles peuvent etre modifiees ou remplacees avant approbation.

`scripts/commit_plan.py` publie le brouillon approuve dans `data/plans/`, active les recettes pending utilisees par le plan, puis genere la liste d'epicerie.

Le planificateur privilegie les recettes principales existantes. Quand il y a au moins quatre recettes admissibles, il choisit quatre soupers existants et propose un nouveau souper local deterministe en pending. Si la banque est insuffisante, il genere seulement le minimum necessaire pour remplir cinq soupers.

Les plans utilisent des positions flexibles (`Jour 1` a `Jour 5`) plutot que des jours de semaine fixes. L'utilisateur peut ensuite assigner chaque repas au vrai jour qui convient.

Chaque plan contient toujours les diners adultes. En mode `ecole`, les lunchs enfants doivent etre froids. En mode `pas_ecole`, aucun lunch enfant n'est requis.

`leftover_friendly` ne suffit pas a lui seul pour produire un lunch de restants. Le planificateur utilise les restants seulement si la recette declare des portions leftover disponibles, un style compatible et au moins un public admissible (`kids_leftover_ok` ou `adult_leftover_ok`). Une portion leftover represente un lunch pour une personne.

Un meme type de lunch ne doit pas apparaitre plus de deux fois par semaine dans la colonne enfants ni plus de deux fois dans la colonne adultes. Si les restants produisent trop de wraps ou de lunchs rechauffes, le planificateur alterne avec des options froides autonomes.

Les soupers qui n'ont pas deja un legume ou un feculent selon `contains_vegetable` et `contains_starch` recoivent un accompagnement depuis `suggested_side_dishes` ou un fallback concret. Les fallbacks standards sont `Legumes de saison` pour les legumes et `Riz` pour les feculents.

## Saison

La v1 utilise deux saisons:

- `saison_chaude`: mai, juin, juillet, aout
- `saison_froide`: septembre a avril

En `saison_chaude`, le planificateur favorise BBQ, griddle propane, grillades, repas legers, tacos, burgers et salades-repas, sans forcer tout le plan a utiliser le BBQ. Il evite les repas typiques d'hiver comme les longs mijotes, braises, rotis, fondues et raclettes.
