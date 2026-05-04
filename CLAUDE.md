# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup (macOS — Tesseract is required for OCR)
brew install tesseract tesseract-lang
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Tests
.venv/bin/pytest -q                          # full suite (~91 tests)
.venv/bin/pytest tests/test_pipeline_integration.py -v   # integration only
.venv/bin/pytest -k "advertiser" -v         # run a single test module by name

# Run the app locally
.venv/bin/streamlit run app.py --server.port 8766

# Prefix all shell commands with `rtk` for token savings (see RTK.md)
rtk git status
```

OCR-dependent tests are silently skipped if `tesseract` is not installed.

## Architecture

### Data flow

```
Upload → Document.from_upload()
       → run_all_checks(document, CheckContext, logo_library)
           ├─ check_dimensions / check_colorspace / check_qr / check_logos
           │   (visual — operate on rendered page images)
           ├─ extract.all_text()  → text-layer first, OCR fallback (Tesseract fra)
           └─ check_advertiser / check_offer / check_printer / check_industry
               (text — operate on the concatenated text of all pages)
       → list[CheckResult]  →  Streamlit UI groups by severity
```

### Key types

- **`Document` / `Page`** (`preflight/document.py`) — uniform interface over PDFs (PyMuPDF) and PNG/JPEG images (Pillow). Always construct via `Document.from_upload()`; it validates file count, size, encryption, and type mixing.
- **`CheckResult`** (`preflight/checks/__init__.py`) — `check_name`, `severity` (ERROR/WARNING/INFO), `message`, optional `details` dict, optional `page` index.
- **`CheckContext`** (`preflight/pipeline.py`) — the only user-controlled inputs remaining: `format_spec`, `industry`, `print_method`. Campaign URL, advertiser details, offer date, and promo code are all **auto-detected from the document**.

### Auto-detection vs user input

This is a compliance tool where false negatives are worse than false positives.

| Element | Approach |
|---|---|
| QR URL | Hardcoded `gtinsi.de/` — any QR in the doc must link there |
| Advertiser mentions | Auto-detected: legal form (SAS/SARL…), Capital social, RCS, postal code |
| Offer date | Auto-detected: dates near expiry keywords (valable, jusqu'au) |
| Promo code | Auto-detected: pattern after "code promo" keyword |
| Logos | phash against `assets/logos/<category>/` reference files |

### Logo detection (`preflight/logos.py`)

- `LogoLibrary` loads reference images (PNG/JPEG/SVG) from `assets/logos/` at startup; SVG files are rasterized via PyMuPDF.
- Detection uses `imagehash.phash` over a multi-scale sliding-window crop sweep (`CROP_FRACTIONS = (0.06, 0.10, 0.18, 0.30, 0.45, 0.65)` of the page's short side) — smallest fractions target tiny logos (8–15 mm).
- Two-tier result: distance ≤ `DEFAULT_THRESHOLD` (18) → INFO, ≤ `SOFT_THRESHOLD` (28) → WARNING (verify visually), above → ERROR.
- If the library is empty, all logo checks return INFO (never silently pass).
- **Calibration**: a high distance usually means the reference image doesn't visually match the logo on the document. Add a closer variant to `assets/logos/<category>/`.

### Text matching (`preflight/text_normalize.py`)

All text matching runs on a normalized form: NFKD-decomposed, accent-stripped, lowercased, whitespace-collapsed, typographic quotes/dashes replaced. `fuzzy_contains(haystack, needle, threshold=85)` uses rapidfuzz `partial_ratio` for OCR noise tolerance.

### Format registry (`preflight/formats.py`)

Registered formats: A5 (148×210 mm), A6 / Carte cadeau (105×148 mm), 15×10 cm, Custom. All include 2 mm bleed, 3 mm safe zone, ±1 mm tolerance, 300 DPI minimum.

### Industry legal mentions (`preflight/industries.py`)

11 sectors (Général, Alcool, Alimentation, Médicaments, Jeux d'argent, Automobiles, Crédit à la consommation, Produits financiers, Assurance, Jouets, Tabac). Each defines `required_phrases` and `any_of_phrases`. "Général" has no required phrases.

## Constraints

- Max upload: 50 MB, 1 PDF (1–2 pages) or 1–2 images, no mixed PDF+image.
- Encrypted PDFs are rejected upfront.
- TAC (≤ 300%) and ICC profile (FOGRA39) are advisory only — no per-pixel computation.
- `app.py` contains zero business logic — all checks are in `preflight/`.
