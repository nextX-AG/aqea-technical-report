---
license: mit
language:
  - en
task_categories:
  - text-classification
  - sentence-similarity
tags:
  - embeddings
  - compression
  - semantic-search
  - sts
  - mteb
pretty_name: "AQEA Verification Pairs (STS-B + STS12–16, E5-Large)"
---

# AQEA Verification Pairs (STS-B + STS12–16, E5-Large)

This dataset package is a **public reproducibility artifact** for the AQEA technical report.
It contains **embedding pairs + human similarity scores** for STS benchmarks, generated deterministically from public sources.

## What’s inside

The intended upload contains JSON files in the format:

```json
{
  "dataset": "sts12",
  "model": "intfloat/e5-large-v2",
  "dimension": 1024,
  "n_pairs": 3108,
  "baseline_spearman": 0.77,
  "embeddings1": [[...], ...],
  "embeddings2": [[...], ...],
  "scores": [0.0, 1.0, ...]
}
```

Files (E5-Large 1024D):
- `stsb_intfloat_e5_large_v2_1024d_pairs.json`
- `sts12_e5large_1024d_pairs.json`
- `sts13_e5large_1024d_pairs.json`
- `sts14_e5large_1024d_pairs.json`
- `sts15_e5large_1024d_pairs.json`
- `sts16_e5large_1024d_pairs.json`

Additionally, the package includes:
- `MANIFEST.sha256` — checksums for all files in the package

## Sources

Datasets (HuggingFace):
- `mteb/stsbenchmark-sts` (STS-B)
- `mteb/sts12-sts`, `mteb/sts13-sts`, `mteb/sts14-sts`, `mteb/sts15-sts`, `mteb/sts16-sts`

Embedding model:
- `intfloat/e5-large-v2` (1024D)

## How this dataset is generated

This repository contains scripts to generate the exact files locally:
- STS-B: `training/scripts/generate_stsb_benchmark.py`
- STS12–16: `benchmark/scripts/generate_all_embeddings.py`

Packaging + checksum generation:
- `aqea-technical-report/repro/package_hf_dataset.py`

## Intended use

- Reproducing the AQEA generalization benchmark and “117× @ ~95% task retention” claim.
- Independent third-party verification of reported metrics.

## License / redistribution note

This package is generated from public benchmark datasets and contains **embeddings + scores** (no raw sentences).
Users should still review the upstream dataset terms for their own compliance needs.

