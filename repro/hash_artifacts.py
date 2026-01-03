#!/usr/bin/env python3
"""
Generate a deterministic SHA256 manifest for key public artifacts referenced by the technical report.

Outputs:
- aqea-technical-report/ARTIFACTS.sha256

Notes:
- This hashes files in the local git checkout (not remote URLs).
- HuggingFace dataset integrity is pinned separately via the dataset commit SHA and its MANIFEST.sha256.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, List


HERE = Path(__file__).resolve()
REPORT_DIR = HERE.parents[1]  # aqea-technical-report/
REPO_ROOT = REPORT_DIR.parent


FILES: List[str] = [
    # Report package (public)
    "aqea-technical-report/TECHNICAL_REPORT.md",
    "aqea-technical-report/VERIFICATION.md",
    "aqea-technical-report/DATASETS.md",
    "aqea-technical-report/README.md",
    "aqea-technical-report/repro/api_smoketest.py",
    "aqea-technical-report/repro/make_figures.py",
    "aqea-technical-report/repro/build_pdf.sh",
    "aqea-technical-report/repro/pdf.css",
    "aqea-technical-report/repro/md-to-pdf.config.js",
    "aqea-technical-report/assets/figure_tradeoff_extrinsic_e5.svg",
    "aqea-technical-report/assets/figure_intrinsic_29x_models.svg",
    "aqea-technical-report/assets/figure_aqea_pq_task_preservation.svg",
    "aqea-technical-report/assets/figures_data.json",
    # Source-of-truth docs / benchmarks cited by the report
    "docs/FINAL_BENCHMARK_TRUTH.md",
    "benchmark/COMPLETE_3STAGE_RESULTS.md",
    "benchmark_results/030_matrix/openai_small_1536d.md",
    "benchmark_results/030_matrix/openai_large_3072d.md",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_existing(paths: Iterable[str]) -> Iterable[Path]:
    for rel in paths:
        p = REPO_ROOT / rel
        if not p.exists():
            raise FileNotFoundError(f"Missing required file: {rel}")
        yield p


def main() -> int:
    out = REPORT_DIR / "ARTIFACTS.sha256"
    lines = []
    for p in iter_existing(FILES):
        rel = p.relative_to(REPO_ROOT).as_posix()
        lines.append(f"{sha256_file(p)}  {rel}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

