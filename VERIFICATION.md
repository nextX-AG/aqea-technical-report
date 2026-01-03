---
title: "AQEA API Verification Guide"
status: "public"
last_updated: "2026-01-02"
---

# AQEA API Verification Guide (Public)

This document describes a **reproducible verification path** for AQEA Compress that does **not** require any private data.
It is designed so that third parties can independently validate:

- the public API surface is reachable (`/health`, `/api/v1/models`)
- authenticated endpoints work with an **Account API key** (`/api/v1/auth/verify`, `/api/v1/compress/batch`)
- requests are executed on **real embeddings** (no synthetic dummy vectors)

## Security model (important)

- **Do not paste API keys into documents or code.**
- The verification script reads the key from an environment variable: `AQEA_API_KEY`.
- The script never prints the key.

## Prerequisites

- Python 3 (stdlib only; no additional packages required)
- An **Account API key** (free keys can be created in the Platform UI)

## Data source (real vectors)

By default, verification uses the same demo dataset referenced by the Platform UI:

- AQED export (Range-enabled): `https://demo.aqea.ai/api/export/text-demo?file=embeddings_original`

This is an AQED v1 binary file containing **original-space** embeddings (e.g., 1024D for the E5-Large demo).

> For long-term reproducibility (papers / citations), we recommend mirroring this dataset to a stable public artifact store
> (e.g. HuggingFace Datasets or a GitHub Release) and pinning a revision + checksum.

## Run the verification (recommended)

### 1) Public endpoints (no key required)

```bash
python3 repro/api_smoketest.py --base-url https://api.aqea.ai --sample 2
```

Expected: `OK` lines for:
- `GET /health`
- `GET /api/v1/models`
- `DATA AQED sample` (dim + sample size)

### 2) Authenticated endpoints (Account API key required)

```bash
export AQEA_API_KEY="aqea_..."
python3 repro/api_smoketest.py --base-url https://api.aqea.ai --sample 8
```

Expected: additional `OK` lines for:
- `GET /api/v1/auth/verify`
- `POST /api/v1/compress/batch`

The script prints the output dimension and metadata (`compressionRatio`, `originalDim`, `compressedDim`).

### 3) Optional: PQ compression smoke test

```bash
python3 repro/api_smoketest.py --pq
```

Note: `/api/v1/compress-pq` may fail if the required PQ codebook for the selected model is not available on the server.
This is not necessarily a product failure; it can be an availability/configuration issue.

## What this verifies (and what it does not)

### Verifies

- API reachability and JSON contract stability for key endpoints
- authentication correctness for Account keys
- basic compression execution on **real embeddings**

### Does NOT verify

- full benchmark reproduction (quality metrics like Spearman/Recall@K)
- training workflows / Lens learning
- performance at large scale (latency/memory projections)

## Local benchmark reproduction (separate)

For scientifically grounded claims, use the benchmark artifacts and scripts documented in:

- `docs/FINAL_BENCHMARK_TRUTH.md`
- `benchmark/`
- `benchmark_results/`

The public technical report should reference those artifacts directly and separate:
- **intrinsic** (vs original embeddings) from
- **extrinsic** (vs human labels)

