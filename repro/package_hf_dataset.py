#!/usr/bin/env python3
"""
Package reproducibility datasets for HuggingFace upload.

Security:
- This script never reads tokens/keys.
- Upload is handled separately by huggingface-cli / huggingface_hub with user-provided auth.

Inputs (expected to exist locally):
- training/data/stsb_intfloat_e5_large_v2_1024d_pairs.json
- training/data/sts12_e5large_1024d_pairs.json ... sts16_e5large_1024d_pairs.json

Outputs:
- aqea-technical-report/hf_package/
  - README.md   (dataset card)
  - data/*.json (copied pair files)
  - MANIFEST.sha256
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import List


HERE = Path(__file__).resolve()
REPORT_DIR = HERE.parents[1]  # aqea-technical-report/
REPO_ROOT = REPORT_DIR.parent

SRC_DIR = REPO_ROOT / "training" / "data"
HF_TEMPLATE = REPORT_DIR / "hf" / "README.md"
OUT_DIR = REPORT_DIR / "hf_package"
OUT_DATA = OUT_DIR / "data"


EXPECTED_FILES: List[str] = [
    "stsb_intfloat_e5_large_v2_1024d_pairs.json",
    "sts12_e5large_1024d_pairs.json",
    "sts13_e5large_1024d_pairs.json",
    "sts14_e5large_1024d_pairs.json",
    "sts15_e5large_1024d_pairs.json",
    "sts16_e5large_1024d_pairs.json",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    missing = [name for name in EXPECTED_FILES if not (SRC_DIR / name).exists()]
    if missing:
        print("ERROR: Missing required input files in training/data/")
        for m in missing:
            print(f"  - {m}")
        print("")
        print("Generate them first (see aqea-technical-report/TECHNICAL_REPORT.md Appendix D and aqea-technical-report/DATASETS.md).")
        return 2

    OUT_DATA.mkdir(parents=True, exist_ok=True)

    # Dataset card
    if not HF_TEMPLATE.exists():
        print(f"ERROR: Missing HF dataset card template: {HF_TEMPLATE}")
        return 2
    shutil.copy2(HF_TEMPLATE, OUT_DIR / "README.md")

    # Copy data files
    copied: List[Path] = []
    for name in EXPECTED_FILES:
        src = SRC_DIR / name
        dst = OUT_DATA / name
        shutil.copy2(src, dst)
        copied.append(dst)

    # Write manifest
    manifest = OUT_DIR / "MANIFEST.sha256"
    lines = []
    for p in sorted(copied):
        digest = sha256_file(p)
        rel = p.relative_to(OUT_DIR).as_posix()
        lines.append(f"{digest}  {rel}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    total_bytes = sum(p.stat().st_size for p in copied)
    print(f"Packaged {len(copied)} files to: {OUT_DIR}")
    print(f"Total size: {total_bytes/1024/1024:.1f} MB")
    print(f"Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

