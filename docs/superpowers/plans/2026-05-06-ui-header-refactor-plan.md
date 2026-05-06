# Refonte barre de contrôles et zone upload

> **Pour agentic workers:** Utiliser superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans pour implémenter ce plan tâche par tâche. Utiliser la syntaxe checkbox (`- [ ]`) pour le suivi.

**Goal:** Refaire la barre de contrôles supérieure pour: (1) réduire l'espacement, (2) zone upload permanente, (3) industrie clickable

**Architecture:** Modification de `app.py` — restructure des colonnes Streamlit, refonte de la zone upload, simplification du workflow industrie

**Tech Stack:** Streamlit, Python

---

## Structure des fichiers

**Modifié:** `app.py` (~574 lignes) — toute la logique de la barre de contrôles

---

### Tâche 1: Réduire les colonnes de 4 à 3

**Files:**
- Modifier: `app.py:136` (zone colonnes contrôle)

- [ ] **Step 1: Identifier les colonnes actuelles**

Les colonnes actuelles: `col_fmt` (Format), `col_ind` (Industrie), `col_print` (Impression), `col_file` (Fichier + boutons)

- [ ] **Step 2: Supprimer la colonne `col_file` et ses boutons**

Supprimer les lignes 213-235: le selectbox de fichier et les boutons ↺ et +

- [ ] **Step 3: Modifier les colonnes à 3**

Ligne 136: `st.columns([2, 3, 2])` au lieu de `[2, 3, 2, 3]`

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "refactor: reduce control bar to 3 columns"
```

---

### Tâche 2: Zone upload permanente

**Files:**
- Modifier: `app.py:278-306` (zone upload) et `app.py:213-235` (anciens contrôles fichier)

- [ ] **Step 1: Créer une fonction helper pour la zone upload**

Ajouter une fonction `_render_upload_zone()` qui affiche:
- Zone drag & drop
- Bouton "Choisir un fichier"
- Message d'aide "PDF (1-2 pages) ou 1-2 images PNG/JPEG"

- [ ] **Step 2: Remplacer l'ancienne zone upload conditionnelle**

La zone actuelle n'apparaît que `if not has_stored_results`. La rendre visible **toujours**:
- Déplacer le code après les colonnes de contrôle
- Faire aparecer même si `has_stored_results == True`

- [ ] **Step 3: Ajouter le bouton "Nouveau fichier" après analyse**

Après les résultats, afficher:
```
[Fichier: document.pdf] [Nouveau fichier ← redirection vers zone upload]
```

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add permanent upload zone"
```

---

### Tâche 3: Industrie clickable

**Files:**
- Modifier: `app.py:150-197` (bloc industrie)

- [ ] **Step 1: Supprimer le bouton crayon**

Supprimer les lignes 192-197 (le bouton ✏ et sa colonne)

- [ ] **Step 2: Rendre le badge clickable**

Le badge actuel (lignes 181-191) est statique. Le rendre clickable:
- Ajouter `key="industry_badge"` au conteneur du badge
- Utiliser `st.selectbox` en mode inline (affiché comme un selectbox, pas un badge statique)
- Ajouter un bouton de validation à côté du selectbox

Alternative: Utiliser `st.expander` avec "Modifier" dans le header, ou un `st.form`.

- [ ] **Step 3: Simplifier le state**

Supprimer `industry_edit_mode` de session state puisque le badge est directement editable.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: make industry badge directly editable"
```

---

### Tâche 4: Nettoyage et tests

**Files:**
- Tester: `app.py` en local

- [ ] **Step 1: Tester l'interface**

Lancer `streamlit run app.py` et vérifier:
- Les 3 colonnes sont visibles
- La zone upload est toujours visible
- Cliquer sur le badge industrie ouvre le select
- Le bouton "Nouveau fichier" fonctionne

- [ ] **Step 2: Tester le re-analyse**

Uploader un fichier, modifier les paramètres, vérifier que le re-analyse fonctionne

- [ ] **Step 3: Nettoyer les imports inutiles**

Si des variables ne sont plus utilisées après les modifications (ex: `col_file`, etc.)

- [ ] **Step 4: Commit final**

```bash
git add app.py
git commit -m "refactor: complete UI header refactor"
```

---

## Vérification finale

- [ ] Spec cover: 3 colonnes ✓, zone upload permanente ✓, industrie clickable ✓
- [ ] Pas de placeholders
- [ ] Cohérence des types