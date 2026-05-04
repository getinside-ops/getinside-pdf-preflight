# Getinside · Print Preflight Checker

A Streamlit app that validates print-bound PDFs and images (PNG/JPEG) for
Getinside ad campaigns against:

- **Technical print specs** — dimensions, bleed, DPI, colour space, QR
  presence and minimum size, QR URL alignment with the configured
  campaign.
- **Mandatory legal/commercial mentions** — advertiser identification
  (company, legal form, address, share capital, RCS), commercial offer
  (end date, promo code), printer mention, and industry-specific
  regulatory phrases (alcohol, food, drugs, gambling, automotive,
  consumer credit, financial products, insurance, toys).

## Architecture

```
preflight/                  # all business logic
  formats.py                # FormatSpec registry (A5, A6, Carte cadeau, 15×10, Custom)
  industries.py             # IndustryRule registry (11 sectors)
  text_normalize.py         # OCR-tolerant normalization + fuzzy matching
  document.py               # PDF / image abstraction (Document, Page)
  extract.py                # text-layer first, OCR fallback (lang='fra')
  qr.py                     # cv2.QRCodeDetector wrapper
  logos.py                  # phash matching against assets/logos/
  pipeline.py               # CheckContext + run_all_checks orchestrator
  checks/
    dimensions.py / colorspace.py / qrcode.py / logos.py
    advertiser.py / offer.py / printer.py / industry.py
assets/logos/<category>/    # reference logos (PNG/JPEG/SVG accepted)
app.py                      # Streamlit UI — pure plumbing
tests/                      # pytest suite (unit + integration)
```

Each check returns `list[CheckResult]` with one of three severities:

- `ERROR` — blocks print
- `WARNING` — needs human review
- `INFO` — advisory / detected value (e.g. extracted QR URL)

## Local development

### macOS

```bash
brew install tesseract tesseract-lang
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
streamlit run app.py
```

### Debian/Ubuntu

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-fra libgl1 libglib2.0-0
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
streamlit run app.py
```

## Deployment — Streamlit Community Cloud

1. Push to GitHub.
2. Connect the repo at <https://streamlit.io/cloud>.
3. Set the entrypoint to `app.py`.
4. `packages.txt` installs Tesseract + French language data + GL libs;
   `requirements.txt` is installed in the Python environment automatically.
5. Default upload size is set to 50 MB via `.streamlit/config.toml`.

## Logo library

`assets/logos/` is the reference library used by the perceptual-hash
(phash) check. Subdirectory names are the category, e.g.:

```
assets/logos/
  cartouche_info_tri/
    Logo triman + Info-tri.svg
  getinside/
    Logo getinside.svg
  imprim_vert/
    Logo Imprim_vert.svg
    Logo Imprim_vert_simple.svg
```

Accepted file types: `.png`, `.jpg`, `.jpeg`, `.svg` (SVGs are rasterized
on load via PyMuPDF). Add a logo variant by dropping a new file into the
appropriate category directory and restarting the app.

The phash check is intentionally honest about its limits:

- It compares the whole rendered page hash against each variant — this
  confirms similar imagery is present, not the precise size or position.
- The 8 mm minimum size for the Cartouche Info-tri is surfaced as an
  `INFO`-level reminder for visual confirmation.
- If the library is empty the check returns `INFO` and asks for manual
  verification, rather than silently passing.

## Known limitations (v1)

- **TAC (taux d'encrage ≤ 300 %)** and **ICC profile (FOGRA39)** are
  *advisory only*: the app reminds the operator to verify them in the
  prepress tool. Per-pixel TAC computation is intentionally out of scope.
- **Multi-page PDFs > 2 pages** are rejected — the tool targets recto or
  recto-verso flyers / cards.
- **Mixed PDF + image uploads** are rejected.
- **Vector-level overprint, trapping, transparency flattening** are not
  checked.
- The phash logo check provides confirmation, not localization (see above).

## Tests

```bash
pytest -q                       # full suite (~85 tests)
pytest tests/test_pipeline_integration.py -v
```

OCR-dependent tests are auto-skipped if `tesseract` is not on the host.
