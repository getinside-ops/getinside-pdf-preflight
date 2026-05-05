# Preflight Print Checks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter 10 nouveaux checks de validation preflight pour couvrir tous les aspects techniques des fichiers print avant production.

**Architecture:** Chaque check sera un nouveau module dans `preflight/checks/` suivant le pattern existant (`CheckResult`, `Severity`, etc.). Les checks seront intégrés dans le pipeline principal via `run_all_checks()`.

**Tech Stack:** PyMuPDF (fitz) pour l'analyse PDF bas-niveau, ajout de nouvelles fonctions de check dans `preflight/checks/`.

---

## Overview des fichiers à créer/modifier

### Nouveaux fichiers (10 modules de check)
- `preflight/checks/font_embedding.py` - Vérification embedding polices
- `preflight/checks/linked_images.py` - Détection images manquantes/chemins cassés
- `preflight/checks/spot_colors.py` - Détection couleurs spot
- `preflight/checks/overprint.py` - Validation surimpression
- `preflight/checks/optional_content.py` - Détection contenu caché (OC)
- `preflight/checks/corrupted_objects.py` - Détection objets malformés
- `preflight/checks/metadata_stripping.py` - Nettoyage métadonnées
- `preflight/checks/linearized.py` - Vérification PDF linearisé
- `preflight/checks/crop_marks.py` - Détection marques de corte
- `preflight/checks/page_boxes.py` - Validation TrimBox/BleedBox

### Fichiers existants à modifier
- `preflight/pipeline.py` - Ajouter les 10 nouveaux checks à `run_all_checks()`
- `preflight/checks/__init__.py` - Exporter les nouveaux modules
- `preflight/report_html.py` - Ajouter les nouveaux checks à l'affichage HTML

---

## Task 1: Font Embedding Check

**Files:**
- Create: `preflight/checks/font_embedding.py`
- Test: `tests/test_checks_font_embedding.py`
- Modify: `preflight/pipeline.py:60-80`

---

## Task 2: Linked Images Check

**Files:**
- Create: `preflight/checks/linked_images.py`
- Test: `tests/test_checks_linked_images.py`
- Modify: `preflight/pipeline.py:60-80`

---

## Task 3: Spot Colors Check

**Files:**
- Create: `preflight/checks/spot_colors.py`
- Test: `tests/test_checks_spot_colors.py`
- Modify: `preflight/pipeline.py:60-80`

---

## Task 4: Overprint Check

**Files:**
- Create: `preflight/checks/overprint.py`
- Test: `tests/test_checks_overprint.py`
- Modify: `preflight/pipeline.py:60-80`

---

## Task 5: Optional Content (OC) Check

**Files:**
- Create: `preflight/checks/optional_content.py`
- Test: `tests/test_checks_optional_content.py`
- Modify: `preflight/pipeline.py:60-80`

---

## Task 6: Corrupted Objects Check

**Files:**
- Create: `preflight/checks/corrupted_objects.py`
- Test: `tests/test_checks_corrupted_objects.py`
- Modify: `preflight/pipeline.py:60-80`

---

## Task 7: Metadata Stripping

**Files:**
- Create: `preflight/checks/metadata_stripping.py`
- Test: `tests/test_checks_metadata_stripping.py`
- Modify: `preflight/pipeline.py:60-80`

---

## Task 8: Linearized PDF Check

**Files:**
- Create: `preflight/checks/linearized.py`
- Test: `tests/test_checks_linearized.py`
- Modify: `preflight/pipeline.py:60-80`

---

## Task 9: Crop/Registration Marks Check

**Files:**
- Create: `preflight/checks/crop_marks.py`
- Test: `tests/test_checks_crop_marks.py`
- Modify: `preflight/pipeline.py:60-80`

---

## Task 10: Page Boxes Validation

**Files:**
- Create: `preflight/checks/page_boxes.py`
- Test: `tests/test_checks_page_boxes.py`
- Modify: `preflight/pipeline.py:60-80`

---

## Task 11: Integration Pipeline

**Files:**
- Modify: `preflight/pipeline.py:60-80`
- Modify: `preflight/checks/__init__.py`
- Modify: `preflight/report_html.py:53`

---

## Task 12: End-to-End Test

**Files:**
- Create: `tests/test_pipeline_full.py`
- Run: Full test suite

---

## Plan Summary

| Task | Feature | Complexity |
|------|---------|------------|
| 1 | Font Embedding | Medium |
| 2 | Linked Images | Medium |
| 3 | Spot Colors | Medium |
| 4 | Overprint | Low |
| 5 | Optional Content | Low |
| 6 | Corrupted Objects | Low |
| 7 | Metadata Stripping | Low |
| 8 | Linearized | Low |
| 9 | Crop Marks | Low |
| 10 | Page Boxes | Low |
| 11 | Pipeline Integration | Medium |
| 12 | End-to-End Test | Low |

**Total estimated tasks:** 12 tasks
**Estimated time:** 2-4 heures selon l'infrastructure de test existante