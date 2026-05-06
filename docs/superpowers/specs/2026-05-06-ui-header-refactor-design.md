# Design: Refonte barre de contrôles et zone upload

**Date:** 2026-05-06
**Statut:** Approuvé

## Objectif

Refaire la barre de contrôles supérieure pour:
1. Rapprocher les contrôles entre eux (4 colonnes → 3)
2. Rendre l'upload plus intuitif — zone toujours visible
3. Rendre le changement d'industrie plus evident (badge clickable)

## Design accepté

### Structure: 3 colonnes compactes

| Colonne | Contenu |
|---------|---------|
| Format | Selectbox "Format" avec options (A5, A6, etc.) |
| Industrie | Badge clickable → ouvre selectbox inline |
| Impression | Selectbox "Impression" (getinside/marque) |

### Zone upload permanente

- **Toujours visible** — meme apres analyse d'un fichier
- **Zone drag & drop** avec bouton "Choisir un fichier"
- **Remplace** l'ancienne colonne "Fichier" avec boutons reanalyse/+

### Aprés analyse

- Le badge "Fichier: nom.pdf" reste affiche (lecture seule)
- Bouton "Nouveau fichier" explicite sous la barre → ramene vers zone upload

### Industrie clickable

- Le badge "Général" est clickable directement
- Au clic: affiche un selectbox inline pour choisir l'industrie
- Confiance % affichee a cote du badge
- Supprime le petit bouton crayon

## Implementation

Pas de refactoring architecture — modifications concentrees dans `app.py`:
1. Reduire les colonnes de 4 a 3
2. Remplacer la colonne "Fichier" par la zone upload permanente
3. Rendre le badge industrie clickable (supprimer bouton crayon)
4. Ajouter le bouton "Nouveau fichier" apres analyse