---
title: "AQEA Technical Report — Dataset Notes"
status: "public"
last_updated: "2026-01-02"
---

# Dataset Notes (Public)

This file enumerates the **public datasets** referenced by the technical report and the expected local output files
produced by the repository’s generation scripts.

## Why this file exists

- The report is intended to be **reproducible** without private data.
- Some generated embedding pair files can be large and may not be committed to git.
- This document makes it explicit **which datasets** and **which filenames** are expected.

## Text similarity (STS)

### STS-B (training benchmark)

- **HuggingFace dataset**: `mteb/stsbenchmark-sts`
- **Split**: `test` (as used by `training/scripts/generate_stsb_benchmark.py`)
- **Model**: `intfloat/e5-large-v2` (1024D)
- **Output files (typical)**:
  - `training/data/stsb_intfloat_e5_large_v2_1024d_pairs.json`
  - `training/data/stsb_intfloat_e5_large_v2_1024d_benchmark.json`
  - `training/data/stsb_intfloat_e5_large_v2_1024d_embeddings.json` (optional, if generated)

Generation command (see report Appendix D):

```bash
python3 training/scripts/generate_stsb_benchmark.py \
  --model intfloat/e5-large-v2 \
  --split test \
  --output-dir training/data
```

### STS12–STS16 (unseen generalization tests)

- **HuggingFace datasets**:
  - `mteb/sts12-sts`
  - `mteb/sts13-sts`
  - `mteb/sts14-sts`
  - `mteb/sts15-sts`
  - `mteb/sts16-sts`
- **Split**: `test`
- **Models (supported by generator)**:
  - `intfloat/e5-large-v2` (1024D)
  - `all-mpnet-base-v2` (768D)
  - `all-MiniLM-L6-v2` (384D)
- **Output files (E5-Large expected by generalization benchmark)**:
  - `training/data/sts12_e5large_1024d_pairs.json`
  - `training/data/sts13_e5large_1024d_pairs.json`
  - `training/data/sts14_e5large_1024d_pairs.json`
  - `training/data/sts15_e5large_1024d_pairs.json`
  - `training/data/sts16_e5large_1024d_pairs.json`

Generation command:

```bash
python3 benchmark/scripts/generate_all_embeddings.py
```

Notes:
- For E5 models, the generator applies the typical E5 “query:” prefix to both sentences (see `benchmark/scripts/generate_all_embeddings.py`).
- The report’s generalization benchmark expects the exact filenames listed above.

## Mirroring / long-term reproducibility (recommended)

For paper-grade reproducibility, mirror the generated `*_pairs.json` files to a stable public location and pin:
- an immutable revision (tag / commit / dataset version)
- a checksum (e.g., sha256)

Suggested options:
- HuggingFace Datasets (best for large artifacts)
- GitHub Releases (good for versioned binary/static artifacts)

This repo includes a packaging helper:
- `aqea-technical-report/repro/package_hf_dataset.py` (creates `aqea-technical-report/hf_package/` + `MANIFEST.sha256`)
- `aqea-technical-report/repro/publish_hf_dataset.sh <org>/<repo>` (uploads via `huggingface-cli`)

