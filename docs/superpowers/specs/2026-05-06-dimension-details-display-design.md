# Design : traduction des libellés de détails en français

Date : 2026-05-06

## Problème

Les détails techniques affichés sous chaque résultat de check utilisent des clés Python brutes (`found_mm`, `trim_box_mm`, `kind`, etc.). Ces termes sont opaques pour l'utilisateur final et certaines valeurs scalaires n'affichent pas leur unité.

## Solution retenue

Ajouter deux dicts dans `preflight/report_html.py` :

- `_DETAIL_LABELS_FR` : mappe chaque clé technique vers un libellé français affiché à la place.
- `_DETAIL_UNITS_FR` : mappe les clés scalaires vers leur unité (mm, DPI). Appliqué uniquement aux valeurs non-tuple (les tuples 2D ont déjà l'unité via `_fmt_detail_value`).

Fallback : toute clé absente de `_DETAIL_LABELS_FR` s'affiche telle quelle (comportement actuel préservé).

## Fichier modifié

`preflight/report_html.py` uniquement. Aucun changement dans les checks ni dans les tests.

## Mapping des libellés

| Clé technique | Libellé affiché |
|---|---|
| `found_mm` | Dimensions détectées |
| `expected_final_mm` | Format final attendu |
| `expected_bleed_mm` | Format avec fond perdu attendu |
| `tolerance_mm` | Tolérance |
| `kind` | Correspondance |
| `trim_box_mm` | TrimBox (zone de découpe finale) |
| `media_box_mm` | MediaBox (page entière, inclut fond perdu ou traits de coupe) |
| `violations_count` | Éléments dans la zone tranquille |
| `min_dist_mm` | Distance minimale au bord |
| `dpi` | Résolution détectée |
| `min_dpi` | Résolution minimale requise |
| `short_side_mm` | Côté le plus court |

## Traduction des valeurs pour `kind`

| Valeur brute | Valeur affichée |
|---|---|
| `final` | format final |
| `bleed` | format avec fond perdu |

## Mapping des unités (scalaires)

| Clé | Unité |
|---|---|
| `tolerance_mm` | mm |
| `min_dist_mm` | mm |
| `short_side_mm` | mm |
| `dpi` | DPI |
| `min_dpi` | DPI |

## Implémentation

Dans la boucle de rendu des détails (actuellement lignes 153-160 de `report_html.py`) :

1. Remplacer `k` par `_DETAIL_LABELS_FR.get(k, k)` pour le libellé.
2. Pour `kind`, traduire la valeur via un sous-dict avant `_fmt_detail_value`.
3. Pour les valeurs scalaires, appendre `_DETAIL_UNITS_FR.get(k, "")` si non vide.
