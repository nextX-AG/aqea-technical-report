#!/usr/bin/env bash
set -euo pipefail

# Build the AQEA Technical Report PDF locally.
# This script intentionally does NOT commit the resulting PDF.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${ROOT}/aqea-technical-report"
DIST_DIR="${REPORT_DIR}/dist"

mkdir -p "${DIST_DIR}"

echo "[1/3] Generating figures (SVG + figures_data.json)..."
python3 "${REPORT_DIR}/repro/make_figures.py"

echo "[2/3] Building PDF via md-to-pdf (Node)..."
echo "      Output: ${DIST_DIR}/AQEA_Technical_Report.pdf"

cd "${ROOT}"

# md-to-pdf writes the PDF next to the markdown by default.
set +e
npx md-to-pdf \
  "${REPORT_DIR}/TECHNICAL_REPORT.md" \
  --config-file "${REPORT_DIR}/repro/md-to-pdf.config.js"
RC=$?
set -e

if [[ $RC -ne 0 ]]; then
  echo ""
  echo "ERROR: PDF build failed (md-to-pdf / Puppeteer)."
  echo "This usually means missing system libraries for headless Chromium."
  echo ""
  echo "On Debian/Ubuntu, install dependencies (example minimal set):"
  echo "  sudo apt-get update && sudo apt-get install -y libnspr4 libnss3"
  echo ""
  echo "If it still fails, install the full Puppeteer dependency set:"
  echo "  https://pptr.dev/troubleshooting"
  echo ""
  echo "Fallback: generating HTML instead (no Chromium required)..."
  node "${REPORT_DIR}/repro/render_html.mjs" \
    "${REPORT_DIR}/TECHNICAL_REPORT.md" \
    "${DIST_DIR}/AQEA_Technical_Report.html" || true
  exit $RC
fi

# Move into dist/ with a stable name.
mv -f "${REPORT_DIR}/TECHNICAL_REPORT.pdf" "${DIST_DIR}/AQEA_Technical_Report.pdf"

echo "[3/3] Done."
ls -lh "${DIST_DIR}/AQEA_Technical_Report.pdf" || true

