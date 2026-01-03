#!/usr/bin/env python3
"""
AQEA API smoke test (public verification path).

Goals:
- Use REAL vectors (no synthetic dummy data) by sampling from a public AQED dataset export.
- Keep secrets safe: read API key only from env var AQEA_API_KEY and never print it.
- Dependency-free: stdlib only.

Typical use:
  export AQEA_API_KEY="aqea_..."
  python3 repro/api_smoketest.py --base-url https://api.aqea.ai

If you want to use the same demo dataset as the Platform UI:
  python3 repro/api_smoketest.py --data-url "https://demo.aqea.ai/api/export/text-demo?file=embeddings_original"
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_BASE_URL = "https://api.aqea.ai"
DEFAULT_DATA_URL = "https://demo.aqea.ai/api/export/text-demo?file=embeddings_original"


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: Dict[str, str]
    body: bytes
    elapsed_ms: float


def http_request(
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[bytes] = None,
    timeout_s: float = 20.0,
) -> HttpResult:
    req_headers: Dict[str, str] = {}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url=url, method=method.upper(), headers=req_headers, data=body)

    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = resp.read()
            elapsed_ms = (time.time() - start) * 1000.0
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return HttpResult(status=int(resp.status), headers=hdrs, body=data, elapsed_ms=elapsed_ms)
    except urllib.error.HTTPError as e:
        data = e.read() if hasattr(e, "read") else b""
        elapsed_ms = (time.time() - start) * 1000.0
        hdrs = {k.lower(): v for k, v in e.headers.items()} if e.headers else {}
        return HttpResult(status=int(e.code), headers=hdrs, body=data, elapsed_ms=elapsed_ms)


def http_json(
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout_s: float = 20.0,
) -> Tuple[HttpResult, Any]:
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    body = None
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    res = http_request(method, url, headers=req_headers, body=body, timeout_s=timeout_s)
    payload = None
    if res.body:
        try:
            payload = json.loads(res.body.decode("utf-8"))
        except Exception:
            payload = None
    return res, payload


def fatal(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 2


def ok(msg: str) -> None:
    print(msg)


def warn(msg: str) -> None:
    print(f"WARNING: {msg}", file=sys.stderr)


def parse_aqed_header(buf: bytes) -> Tuple[int, int, int, int]:
    """
    Returns (header_size, n_vectors, d_orig, flags).

    AQED v1 header is 60 bytes in some writers, 64 bytes in others. We use 64 for safe Range parsing.
    Layout (little endian u32):
      0:  magic "AQED"
      4:  version (u32) == 1
      8:  n (u32)
      12: dOrig (u32)
      16: dAqea (u32)
      20: flags (u32)  bit0=has_original, bit1=has_aqea
    """
    if len(buf) < 64:
        raise ValueError("AQED header requires at least 64 bytes for safe detection")
    if buf[:4] != b"AQED":
        raise ValueError("Invalid AQED: missing magic bytes")
    version = struct.unpack_from("<I", buf, 4)[0]
    if version != 1:
        raise ValueError(f"Unsupported AQED version: {version}")
    n = struct.unpack_from("<I", buf, 8)[0]
    d_orig = struct.unpack_from("<I", buf, 12)[0]
    d_aqea = struct.unpack_from("<I", buf, 16)[0]
    flags = struct.unpack_from("<I", buf, 20)[0]
    if n <= 0 or d_orig <= 0:
        raise ValueError(f"Invalid AQED header: n={n}, dOrig={d_orig}")

    FLAG_HAS_ORIGINAL = 1 << 0
    FLAG_HAS_AQEA = 1 << 1
    dim = d_orig if (flags & FLAG_HAS_ORIGINAL) else (d_aqea if (flags & FLAG_HAS_AQEA) else 0)
    if dim <= 0:
        raise ValueError(f"Invalid AQED flags: no embeddings present (flags={flags})")

    header_size = 64
    return header_size, n, d_orig, flags


def fetch_aqed_sample_vectors(data_url: str, *, n_vectors: int, timeout_s: float) -> Tuple[int, List[List[float]]]:
    """
    Downloads only the required prefix of an AQED file using Range requests:
    header + first n_vectors of ORIGINAL embeddings.
    Returns (dim, vectors).
    """
    head = http_request("GET", data_url, headers={"Range": "bytes=0-63"}, timeout_s=timeout_s)
    if head.status not in (200, 206):
        raise ValueError(f"Dataset header fetch failed (HTTP {head.status})")
    if len(head.body) < 64:
        raise ValueError("Dataset header too small")
    header_size, total_n, d_orig, flags = parse_aqed_header(head.body[:64])

    FLAG_HAS_ORIGINAL = 1 << 0
    if (flags & FLAG_HAS_ORIGINAL) == 0:
        raise ValueError("Dataset AQED does not contain original embeddings section")

    take = min(max(1, n_vectors), total_n)
    byte_len = header_size + take * d_orig * 4
    rng = f"bytes=0-{byte_len - 1}"
    chunk = http_request("GET", data_url, headers={"Range": rng}, timeout_s=timeout_s)
    if chunk.status not in (200, 206):
        raise ValueError(f"Dataset range fetch failed (HTTP {chunk.status})")
    if len(chunk.body) < byte_len:
        raise ValueError(f"Dataset range truncated (need {byte_len}, got {len(chunk.body)})")

    vectors: List[List[float]] = []
    offset = header_size
    for _ in range(take):
        row = list(struct.unpack_from("<" + ("f" * d_orig), chunk.body, offset))
        vectors.append(row)
        offset += d_orig * 4
    return d_orig, vectors


def pick_model_id_for_dim(models_payload: Any, dim: int) -> Optional[str]:
    if not isinstance(models_payload, dict):
        return None
    models = models_payload.get("models")
    if not isinstance(models, list):
        return None
    for m in models:
        if isinstance(m, dict) and int(m.get("input_dim", -1)) == dim:
            mid = m.get("id")
            return str(mid) if mid else None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="AQEA API smoke test using real vectors from an AQED dataset export.")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"API base URL (default: {DEFAULT_BASE_URL})")
    ap.add_argument("--data-url", default=DEFAULT_DATA_URL, help="AQED dataset URL (supports Range requests)")
    ap.add_argument("--sample", type=int, default=8, help="Number of vectors to sample from the dataset (default: 8)")
    ap.add_argument("--timeout-s", type=float, default=20.0, help="HTTP timeout per request in seconds")
    ap.add_argument("--pq", action="store_true", help="Also try /api/v1/compress-pq (requires Account key)")
    args = ap.parse_args()

    base = args.base_url.rstrip("/")

    health = http_request("GET", f"{base}/health", timeout_s=args.timeout_s)
    if health.status != 200:
        return fatal(f"GET /health expected 200, got {health.status} (body={health.body[:200]!r})")
    ok(f"OK  GET  /health  ({health.elapsed_ms:.1f}ms)")

    models_res, models_payload = http_json("GET", f"{base}/api/v1/models", timeout_s=args.timeout_s)
    if models_res.status != 200:
        return fatal(f"GET /api/v1/models expected 200, got {models_res.status}")
    ok(f"OK  GET  /api/v1/models  ({models_res.elapsed_ms:.1f}ms)")

    try:
        dim, vectors = fetch_aqed_sample_vectors(args.data_url, n_vectors=args.sample, timeout_s=args.timeout_s)
    except Exception as e:
        return fatal(f"Failed to fetch AQED vectors from --data-url: {e}")
    ok(f"OK  DATA  AQED sample: dim={dim}, n={len(vectors)}  (source: {args.data_url})")

    model_id = pick_model_id_for_dim(models_payload, dim)
    if not model_id:
        warn(f"Could not infer model id from /api/v1/models for dim={dim}. Using auto targetDims.")

    api_key = os.environ.get("AQEA_API_KEY", "").strip()
    if not api_key:
        warn("AQEA_API_KEY not set. Public endpoints verified; skipping authenticated checks.")
        return 0

    auth_headers = {"X-API-Key": api_key}

    vr, vp = http_json("GET", f"{base}/api/v1/auth/verify", headers=auth_headers, timeout_s=args.timeout_s)
    if vr.status != 200:
        return fatal(f"GET /api/v1/auth/verify expected 200, got {vr.status} (body={vr.body[:200]!r})")
    ok(f"OK  GET  /api/v1/auth/verify  ({vr.elapsed_ms:.1f}ms)")
    if isinstance(vp, dict) and ("quota_limit" in vp or "quota_used" in vp):
        ok(f"     quota: used={vp.get('quota_used')} limit={vp.get('quota_limit')}")

    req = {"vectors": vectors, "options": {"targetDims": 0}}
    br, bp = http_json(
        "POST",
        f"{base}/api/v1/compress/batch",
        headers=auth_headers,
        json_body=req,
        timeout_s=args.timeout_s,
    )
    if br.status != 200:
        return fatal(f"POST /api/v1/compress/batch expected 200, got {br.status} (body={br.body[:200]!r})")
    if not isinstance(bp, dict) or "compressed" not in bp or "metadata" not in bp:
        return fatal("POST /api/v1/compress/batch returned unexpected JSON shape")
    comp = bp.get("compressed")
    meta = bp.get("metadata")
    if not isinstance(comp, list) or not comp or not isinstance(comp[0], list):
        return fatal("Compressed vectors missing/invalid")
    out_dim = len(comp[0])
    ok(f"OK  POST /api/v1/compress/batch  ({br.elapsed_ms:.1f}ms)  out_dim={out_dim}")
    if isinstance(meta, dict):
        ok(f"     ratio={meta.get('compressionRatio')} originalDim={meta.get('originalDim')} compressedDim={meta.get('compressedDim')}")

    if args.pq:
        if not model_id:
            warn("Skipping /api/v1/compress-pq because model id could not be inferred for the dataset dim.")
        else:
            pq_req: Dict[str, Any] = {"vector": vectors[0], "model": model_id}
            pr, pp = http_json(
                "POST",
                f"{base}/api/v1/compress-pq",
                headers=auth_headers,
                json_body=pq_req,
                timeout_s=args.timeout_s,
            )
            if pr.status == 200 and isinstance(pp, dict):
                codes = pp.get("codes")
                meta2 = pp.get("metadata", {})
                ok(
                    f"OK  POST /api/v1/compress-pq  ({pr.elapsed_ms:.1f}ms)  codes={len(codes) if isinstance(codes, list) else 'n/a'}  model={model_id}"
                )
                if isinstance(meta2, dict):
                    ok(f"     expectedQuality={meta2.get('expectedQuality')} ratio={meta2.get('compressionRatio')}")
            else:
                warn(
                    f"/api/v1/compress-pq did not succeed (HTTP {pr.status}). This can be normal if codebooks are missing."
                )

    ok("DONE: smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

