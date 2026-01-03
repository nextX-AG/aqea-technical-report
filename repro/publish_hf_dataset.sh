#!/usr/bin/env bash
set -euo pipefail

# Publish the packaged dataset folder to HuggingFace.
#
# Requirements:
# - You must authenticate yourself (recommended):
#     huggingface-cli login
#   or provide a token via env var (avoid shell history leaks):
#     export HF_TOKEN="hf_..."
#
# This script does not store tokens.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${ROOT}/aqea-technical-report"
PKG_DIR="${REPORT_DIR}/hf_package"

DATASET_REPO="${1:-}"
if [[ -z "${DATASET_REPO}" ]]; then
  echo "Usage: bash aqea-technical-report/repro/publish_hf_dataset.sh <org-or-user>/<repo-name>"
  exit 2
fi

if [[ ! -d "${PKG_DIR}" ]]; then
  echo "ERROR: ${PKG_DIR} does not exist. Run:"
  echo "  python3 aqea-technical-report/repro/package_hf_dataset.py"
  exit 2
fi

if ! command -v huggingface-cli >/dev/null 2>&1; then
  echo "ERROR: huggingface-cli not found."
  echo "Install it with:"
  echo "  python3 -m pip install --user -U huggingface_hub"
  exit 2
fi

echo "Uploading folder: ${PKG_DIR}"
echo "To dataset repo:  ${DATASET_REPO}"
echo ""

# Prefer env token if provided; otherwise rely on existing login.
if [[ -n "${HF_TOKEN:-}" ]]; then
  huggingface-cli whoami --token "${HF_TOKEN}" >/dev/null
  huggingface-cli upload "${DATASET_REPO}" "${PKG_DIR}" --repo-type dataset --token "${HF_TOKEN}"
else
  huggingface-cli whoami >/dev/null
  huggingface-cli upload "${DATASET_REPO}" "${PKG_DIR}" --repo-type dataset
fi

echo "Done."

