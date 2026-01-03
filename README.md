---
title: "AQEA Public Technical Report Package"
status: "public"
last_updated: "2026-01-03"
---

# AQEA Public Technical Report Package

This folder is intended to be committed as a **public, self-contained** technical report package.

## Contents

- `TECHNICAL_REPORT.md`
  - The main technical report (written to be citable and evidence-backed).
- `VERIFICATION.md`
  - A reproducible verification path (no secrets, "bring your own key").
- `repro/api_smoketest.py`
  - Dependency-free API smoke test that uses **real vectors** from a public AQED export.
- `assets/`
  - Figures exported for the PDF (tradeoff curves, tables, diagrams).

## HuggingFace Dataset (Public Reproducibility Artifact)

The verification dataset is publicly available on HuggingFace:

🔗 **https://huggingface.co/datasets/nextxag/aqea-sts-verification-pairs**

Contains:
- STS-B + STS12–16 embedding pairs (E5-Large 1024D)
- Human similarity scores
- Checksums for verification

This enables third-party reproduction of our "117× @ ~95% task retention" claim without generating embeddings locally.

## Rendering to PDF

We keep sources in Markdown so they can be reviewed via git diff.

### Recommended: reproducible local PDF build (Node)

```bash
bash aqea-technical-report/repro/build_pdf.sh
```

Outputs:
- `aqea-technical-report/dist/AQEA_Technical_Report.pdf` (gitignored)
- If PDF build fails due to missing Chromium libs, the script produces:
  - `aqea-technical-report/dist/AQEA_Technical_Report.html` (print-to-PDF fallback)

#### Troubleshooting (Linux)

`md-to-pdf` uses headless Chromium (Puppeteer). If you see missing shared libraries:

```bash
sudo apt-get update && sudo apt-get install -y libnspr4 libnss3
```

If you see a Chromium error like **"No usable sandbox"**, the PDF build already applies
`--no-sandbox` in `repro/md-to-pdf.config.js` for compatibility with hardened Linux environments.

### Alternative: Pandoc

```bash
pandoc TECHNICAL_REPORT.md -o AQEA_Technical_Report.pdf
```

## Security

- Never commit API keys.
- All verification steps read the key only from `AQEA_API_KEY`.

## Regenerating Dataset Locally (optional)

```bash
python3 aqea-technical-report/repro/package_hf_dataset.py
```
