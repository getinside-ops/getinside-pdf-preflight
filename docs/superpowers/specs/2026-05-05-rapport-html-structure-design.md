# Design — Rapport HTML structuré (remplacement du bloc `st.code`)

**Date :** 2026-05-05  
**Contexte :** Le rapport de preflight est actuellement rendu via `st.code()`, ce qui impose la police JetBrains Mono, empêche le retour à la ligne automatique, et nuit à la lisibilité rapide. La copie en bloc n'est plus une contrainte.

---

## Objectif

Remplacer le bloc `st.code(report, language=None)` par un rendu HTML structuré utilisant Inter, avec couleurs de sévérité, retour à la ligne automatique, et tout visible d'un seul coup d'œil.

---

## Changements dans `app.py`

### Suppression

- La fonction `_build_text_report()` est supprimée (elle génère du texte brut pour `st.code`).
- L'appel `st.code(report, language=None)` est supprimé.
- L'appel à `_meta_plain()` dans le bloc `run_button` est supprimé (il n'est plus nécessaire).

### Ajout

Une nouvelle fonction `_render_html_report(results, doc_name, context)` émet directement du HTML via `st.markdown(..., unsafe_allow_html=True)`.

---

## Structure HTML du rapport

### En-tête

Une ligne de contexte compacte en Inter 12px, couleur `#6b7280` :

```
Format: A5  ·  Industrie: Général  ·  Imprimé par getinside
```

Fond `#f9fafb`, bordure `#e5e7eb`, border-radius 8px, padding 10px 14px.

### Corps — groupes de checks

Pour chaque catégorie (dans l'ordre de `_CHECK_ORDER`) :

**Ligne de titre** — Inter 13px, `font-weight: 600`, couleur `#111827` :
```
📐 DIMENSIONS — ❌ 1 erreur
```

Séparateur visuel entre groupes : `border-top: 1px solid #f3f4f6`, margin-top 10px.

**Messages** — sous le titre, indentés (padding-left 16px), Inter 12.5px, line-height 1.6, `white-space: normal` :

Chaque message est précédé d'un point coloré (`·`) selon la sévérité :

| Sévérité | Couleur texte | Couleur point |
|----------|---------------|---------------|
| ERROR    | `#dc2626`     | `#dc2626`     |
| WARNING  | `#92400e`     | `#d97706`     |
| INFO     | `#6b7280`     | `#9ca3af`     |

Si un numéro de page est disponible, il apparaît en badge gris clair (`[p.1]`) avant le message.

Les détails techniques (`[dimension: X · Y]`) restent affichés en fin de ligne, en `#9ca3af`.

---

## Ce qui ne change pas

- Le banner clé (`_render_key_info_banner`) reste identique au-dessus du rapport.
- Le verdict summary (`st.error` / `st.warning` / `st.success`) reste identique.
- Les thumbnails de pages restent identiques.
- La fonction `_meta_plain()` est conservée dans le code mais n'est plus appelée (elle peut être supprimée lors d'un cleanup ultérieur, hors scope).

---

## Périmètre

- **Dans le scope :** remplacement de `_build_text_report` + `st.code` par `_render_html_report` + `st.markdown`.
- **Hors scope :** modifier le banner clé, le verdict, les thumbnails, ou tout autre check.
