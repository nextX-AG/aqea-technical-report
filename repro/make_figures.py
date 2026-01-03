#!/usr/bin/env python3
"""
Generate publication-ready SVG figures for the AQEA technical report.

Design goals:
- Deterministic output (no randomness).
- No third-party dependencies (stdlib only).
- Data must be sourced from repository artifacts (no invented numbers).

Outputs (written to aqea-technical-report/assets/):
- figure_tradeoff_extrinsic_e5.svg
- figure_intrinsic_29x_models.svg
- figure_aqea_pq_task_preservation.svg
- figures_data.json (the extracted numeric data used for rendering)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


HERE = Path(__file__).resolve()
REPORT_DIR = HERE.parents[1]  # aqea-technical-report/
REPO_ROOT = REPORT_DIR.parent
ASSETS_DIR = REPORT_DIR / "assets"

FINAL_TRUTH = REPO_ROOT / "docs" / "FINAL_BENCHMARK_TRUTH.md"


def sha256_hex(data: bytes) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def find_benchmark_human_scores_artifact(repo_root: Path) -> Path:
    """
    Returns the benchmark markdown artifact that contains the section
    "Models with Human Scores".

    We intentionally avoid encoding internal pipeline framing in filenames
    or user-facing strings.
    """
    bench_dir = repo_root / "benchmark"
    if not bench_dir.exists():
        raise FileNotFoundError("benchmark/ directory not found at repo root")

    candidates = sorted(bench_dir.glob("COMPLETE_*_RESULTS.md"))
    # Fallback to any *.md if naming differs
    if not candidates:
        candidates = sorted(bench_dir.glob("*.md"))

    for p in candidates:
        try:
            txt = read_text(p)
        except Exception:
            continue
        if re.search(
            r"^###.*\bModels\s+with\s+Human\s+Scores\b",
            txt,
            flags=re.IGNORECASE | re.MULTILINE,
        ):
            return p

    raise FileNotFoundError("Could not locate benchmark artifact with 'Models with Human Scores' section")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_markdown_table(section_text: str) -> List[List[str]]:
    """
    Extracts the first markdown table found in section_text.
    Returns rows as list of cells (strings), including header row.
    """
    lines = [ln.rstrip("\n") for ln in section_text.splitlines()]
    # Find first header row with pipes.
    start = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("|") and ln.count("|") >= 2:
            # next line must be separator
            if i + 1 < len(lines) and re.match(r"^\s*\|?\s*[-:]+", lines[i + 1]):
                start = i
                break
    if start is None:
        return []

    rows: List[List[str]] = []
    for ln in lines[start:]:
        if not ln.strip().startswith("|"):
            break
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


def section_between(text: str, start_pat: str, end_pat: str) -> str:
    m1 = re.search(start_pat, text, flags=re.IGNORECASE | re.MULTILINE)
    if not m1:
        return ""
    m2 = re.search(end_pat, text[m1.end() :], flags=re.IGNORECASE | re.MULTILINE)
    return text[m1.end() : m1.end() + (m2.start() if m2 else len(text))]


def parse_percent(s: str) -> float:
    """
    Parses strings like "71.8%" into 71.8.
    """
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*%", s)
    if not m:
        raise ValueError(f"Percent not found in: {s!r}")
    return float(m.group(1))


def parse_ratio(s: str) -> float:
    """
    Parses strings like "117x" or "117×" into 117.0.
    """
    m = re.search(r"(\d+(?:\.\d+)?)\s*[x×]", s, flags=re.IGNORECASE)
    if not m:
        raise ValueError(f"Ratio not found in: {s!r}")
    return float(m.group(1))


def extract_generalization_rows(final_truth_md: str) -> List[Dict[str, float]]:
    # Find the section starting at "Ergebnisse auf ungesehenen Daten" until the next heading.
    sec = section_between(final_truth_md, r"Ergebnisse\s+auf\s+ungesehenen\s+Daten", r"^##\s+")
    if not sec:
        raise ValueError("Could not locate generalization section in FINAL_BENCHMARK_TRUTH.md")
    table = extract_markdown_table(sec)
    if not table:
        raise ValueError("Could not locate generalization table in FINAL_BENCHMARK_TRUTH.md section")

    header = table[0]
    rows = table[2:] if len(table) >= 3 else []

    # Expected columns: Dataset | Type | Original | AQEA 29x | Loss | + PQ (117x) | PQ Effect
    # We'll accept minor header variations.
    out: List[Dict[str, float]] = []
    for r in rows:
        if not r or not r[0].upper().startswith("STS"):
            continue
        dataset = r[0].strip()
        original = parse_percent(r[2])
        aqea = parse_percent(r[3])
        pq = parse_percent(r[5])
        out.append(
            {
                "dataset": dataset,
                "original": original,
                "aqea_29x": aqea,
                "aqea_29x_pq_117x": pq,
            }
        )
    if not out:
        raise ValueError("No STS12–16 rows parsed from generalization table")
    return out


def extract_intrinsic_table(final_truth_md: str) -> List[Dict[str, float]]:
    # Extract the intrinsic table from the verified intrinsic section.
    sec = section_between(
        final_truth_md,
        r"Verifizierte\s+Ergebnisse\s+\(Intrinsic\s*-\s*Spearman\s+vs\s+Original\)",
        r"^##\s+",
    )
    if not sec:
        raise ValueError("Could not locate intrinsic section in FINAL_BENCHMARK_TRUTH.md")
    table = extract_markdown_table(sec)
    if not table:
        raise ValueError("Could not locate intrinsic table in FINAL_BENCHMARK_TRUTH.md section")

    rows = table[2:] if len(table) >= 3 else []
    out: List[Dict[str, float]] = []
    for r in rows:
        if len(r) < 4:
            continue
        model = r[0].strip()
        comp = r[2].strip()
        spearman = parse_percent(r[3])
        out.append({"model": model, "compression": comp, "spearman_vs_orig": spearman})
    if not out:
        raise ValueError("No rows parsed from intrinsic table")
    return out


def extract_aqea_pq_human_table(three_md: str) -> List[Dict[str, float]]:
    sec = section_between(
        three_md,
        r"Models\s+with\s+Human\s+Scores",
        r"^###.*\bModels\s+WITHOUT\s+Human\s+Scores\b",
    )
    if not sec:
        raise ValueError("Could not locate human-scores section in benchmark artifact")
    table = extract_markdown_table(sec)
    if not table:
        raise ValueError("Could not locate human-scores table in benchmark artifact")
    rows = table[2:] if len(table) >= 3 else []
    out: List[Dict[str, float]] = []
    for r in rows:
        if len(r) < 4:
            continue
        model = r[0].strip().strip("*")
        compression = parse_ratio(r[1])
        task_pres = parse_percent(r[3])
        out.append({"model": model, "compression_x": compression, "task_preservation_pct": task_pres})
    if not out:
        raise ValueError("No rows parsed from human-scores table")
    return out


# -----------------------------------------------------------------------------
# Minimal SVG rendering helpers (no dependencies)
# -----------------------------------------------------------------------------


def svg_header(w: int, h: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<rect width="{w}" height="{h}" fill="white"/>'
    )


def svg_footer() -> str:
    return "</svg>\n"


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def draw_axes(w: int, h: int, *, left: int, top: int, right: int, bottom: int) -> str:
    x0, y0 = left, h - bottom
    x1, y1 = w - right, top
    return (
        f'<line x1="{x0}" y1="{y0}" x2="{w-right}" y2="{y0}" stroke="#111" stroke-width="1"/>'
        f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{top}" stroke="#111" stroke-width="1"/>'
        f'<text x="{x0}" y="{h-10}" font-family="Inter, Arial, sans-serif" font-size="11" fill="#333">Compression (×)</text>'
        f'<text x="12" y="{top+12}" font-family="Inter, Arial, sans-serif" font-size="11" fill="#333">Quality (%)</text>'
    )


def figure_tradeoff_extrinsic(generalization: List[Dict[str, float]]) -> str:
    """
    Scatter/line plot for E5-Large extrinsic quality at 1× vs 29× vs 117×.
    Uses the average across STS12–16 for AQEA and AQEA+PQ.
    """
    w, h = 720, 420
    left, right, top, bottom = 70, 30, 40, 50

    # Aggregate (mean)
    n = len(generalization)
    orig = sum(r["original"] for r in generalization) / n
    aqea = sum(r["aqea_29x"] for r in generalization) / n
    pq = sum(r["aqea_29x_pq_117x"] for r in generalization) / n

    points = [
        ("Original", 1.0, orig, "#111827"),
        ("AQEA 29×", 29.0, aqea, "#10b981"),
        ("AQEA+PQ 117×", 117.0, pq, "#06b6d4"),
    ]

    # Axis ranges: compression 1..140, quality 60..100 for this figure
    xmin, xmax = 1.0, 140.0
    ymin, ymax = 60.0, 100.0

    def xmap(x: float) -> float:
        # log-like spacing helps a bit; use log10
        import math

        lx = math.log10(x)
        lmin = math.log10(xmin)
        lmax = math.log10(xmax)
        return left + (lx - lmin) / (lmax - lmin) * (w - left - right)

    def ymap(y: float) -> float:
        return top + (ymax - y) / (ymax - ymin) * (h - top - bottom)

    # grid
    grid = []
    for q in (60, 70, 80, 90, 100):
        yy = ymap(float(q))
        grid.append(f'<line x1="{left}" y1="{yy}" x2="{w-right}" y2="{yy}" stroke="#e5e7eb" stroke-width="1"/>')
        grid.append(
            f'<text x="{left-10}" y="{yy+4}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="11" fill="#333">{q}</text>'
        )

    for cx in (1, 3, 10, 30, 100):
        xx = xmap(float(cx))
        grid.append(f'<line x1="{xx}" y1="{top}" x2="{xx}" y2="{h-bottom}" stroke="#f3f4f6" stroke-width="1"/>')
        grid.append(
            f'<text x="{xx}" y="{h-bottom+18}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="11" fill="#333">{cx}×</text>'
        )

    # line between points
    line = (
        f'<path d="M {xmap(points[0][1]):.2f} {ymap(points[0][2]):.2f} '
        f'L {xmap(points[1][1]):.2f} {ymap(points[1][2]):.2f} '
        f'L {xmap(points[2][1]):.2f} {ymap(points[2][2]):.2f}" '
        f'stroke="#111" stroke-width="2" fill="none" stroke-linecap="round"/>'
    )

    dots = []
    labels = []
    for name, cx, q, color in points:
        xx, yy = xmap(cx), ymap(q)
        dots.append(f'<circle cx="{xx:.2f}" cy="{yy:.2f}" r="6" fill="{color}"/>')
        labels.append(
            f'<text x="{xx+10:.2f}" y="{yy-10:.2f}" font-family="Inter, Arial, sans-serif" font-size="12" fill="#111">{esc(name)} ({q:.1f}%)</text>'
        )

    title = (
        '<text x="70" y="24" font-family="Inter, Arial, sans-serif" font-size="16" fill="#111">'
        'Extrinsic quality vs compression (E5-Large, STS12–16 unseen avg)'
        "</text>"
    )
    subtitle = (
        '<text x="70" y="40" font-family="Inter, Arial, sans-serif" font-size="11" fill="#555">'
        'Source: docs/FINAL_BENCHMARK_TRUTH.md (generalization tests)'
        "</text>"
    )

    return (
        svg_header(w, h)
        + title
        + subtitle
        + "".join(grid)
        + draw_axes(w, h, left=left, top=top, right=right, bottom=bottom)
        + line
        + "".join(dots)
        + "".join(labels)
        + svg_footer()
    )


def figure_bar_chart(
    title: str,
    subtitle: str,
    items: List[Tuple[str, float]],
    *,
    y_min: float,
    y_max: float,
    bar_color: str,
    value_fmt: str = "{:.1f}%",
) -> str:
    w, h = 820, 420
    left, right, top, bottom = 70, 30, 55, 70
    plot_w = w - left - right
    plot_h = h - top - bottom

    n = len(items)
    if n == 0:
        raise ValueError("No items for bar chart")

    gap = 12
    bar_w = (plot_w - gap * (n - 1)) / n

    def ymap(y: float) -> float:
        return top + (y_max - y) / (y_max - y_min) * plot_h

    parts = [svg_header(w, h)]
    parts.append(f'<text x="{left}" y="24" font-family="Inter, Arial, sans-serif" font-size="16" fill="#111">{esc(title)}</text>')
    parts.append(f'<text x="{left}" y="40" font-family="Inter, Arial, sans-serif" font-size="11" fill="#555">{esc(subtitle)}</text>')

    # grid + y labels
    for q in range(int(y_min), int(y_max) + 1, 5):
        yy = ymap(float(q))
        parts.append(f'<line x1="{left}" y1="{yy}" x2="{w-right}" y2="{yy}" stroke="#f3f4f6" stroke-width="1"/>')
        parts.append(
            f'<text x="{left-10}" y="{yy+4}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="11" fill="#333">{q}</text>'
        )

    parts.append(draw_axes(w, h, left=left, top=top, right=right, bottom=bottom))

    # bars
    for i, (name, val) in enumerate(items):
        x = left + i * (bar_w + gap)
        y = ymap(val)
        height = (top + plot_h) - y
        parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{height:.2f}" fill="{bar_color}"/>')
        parts.append(
            f'<text x="{x + bar_w/2:.2f}" y="{y-8:.2f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="11" fill="#111">{esc(value_fmt.format(val))}</text>'
        )
        parts.append(
            f'<text x="{x + bar_w/2:.2f}" y="{h-bottom+22}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="11" fill="#111">{esc(name)}</text>'
        )

    parts.append(svg_footer())
    return "".join(parts)


def main() -> int:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    final_text = read_text(FINAL_TRUTH)
    human_scores_path = find_benchmark_human_scores_artifact(REPO_ROOT)
    human_scores_text = read_text(human_scores_path)

    generalization = extract_generalization_rows(final_text)
    intrinsic = extract_intrinsic_table(final_text)
    aqea_pq_human = extract_aqea_pq_human_table(human_scores_text)

    # Figure 1: tradeoff (extrinsic avg, E5-Large)
    (ASSETS_DIR / "figure_tradeoff_extrinsic_e5.svg").write_text(
        figure_tradeoff_extrinsic(generalization), encoding="utf-8"
    )

    # Figure 2: intrinsic retention (pre-trained weights)
    intr_items = [(d["model"], float(d["spearman_vs_orig"])) for d in intrinsic]
    (ASSETS_DIR / "figure_intrinsic_29x_models.svg").write_text(
        figure_bar_chart(
            title="Intrinsic retention at ~29× (pre-trained weights)",
            subtitle="Source: docs/FINAL_BENCHMARK_TRUTH.md (Spearman vs original)",
            items=intr_items,
            y_min=80.0,
            y_max=100.0,
            bar_color="#10b981",
        ),
        encoding="utf-8",
    )

    # Figure 3: task preservation (human labels)
    three_items = [(d["model"].replace(" (wav2vec2)", ""), float(d["task_preservation_pct"])) for d in aqea_pq_human]
    (ASSETS_DIR / "figure_aqea_pq_task_preservation.svg").write_text(
        figure_bar_chart(
            title="AQEA+PQ task preservation (human labels only)",
            subtitle="Source: benchmark artifact (models with human scores)",
            items=three_items,
            y_min=60.0,
            y_max=100.0,
            bar_color="#06b6d4",
        ),
        encoding="utf-8",
    )

    # Record numeric data used for rendering (auditability)
    data = {
        "sources": {
            "final_benchmark_truth": str(FINAL_TRUTH.relative_to(REPO_ROOT)),
            "benchmark_human_scores_sha256": sha256_hex(human_scores_text.encode("utf-8")),
        },
        "generalization_rows": generalization,
        "intrinsic_rows": intrinsic,
        "aqea_pq_human_rows": aqea_pq_human,
    }
    (ASSETS_DIR / "figures_data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    print("Wrote figures to:", ASSETS_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

