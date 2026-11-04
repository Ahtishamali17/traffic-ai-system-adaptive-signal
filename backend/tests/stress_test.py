"""
tests/stress_test.py
--------------------------------------------------------------------
Lightweight concurrent load test against a running instance of the
API. Not part of the pytest suite (it needs a live server) -- run
manually against a dev/staging deployment:

    python tests/stress_test.py --url http://localhost:8000 --concurrency 20 --requests 200

Hits /api/health repeatedly (safe, side-effect-free) and reports
success rate, latency percentiles, and requests/sec. For a heavier
test, point --path at a real read endpoint like
/api/v1/detection/sessions.
--------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


def hit_endpoint(base_url: str, path: str) -> tuple[bool, float]:
    start = time.perf_counter()
    try:
        resp = httpx.get(f"{base_url}{path}", timeout=10.0)
        ok = resp.status_code == 200
    except Exception:
        ok = False
    elapsed_ms = (time.perf_counter() - start) * 1000
    return ok, elapsed_ms


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple concurrent load test for the Traffic AI API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the running API")
    parser.add_argument("--path", default="/api/health", help="Path to hit repeatedly")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent worker threads")
    parser.add_argument("--requests", type=int, default=100, help="Total requests to send")
    args = parser.parse_args()

    print(f"Hitting {args.url}{args.path} with {args.requests} requests, concurrency={args.concurrency}")

    results: list[tuple[bool, float]] = []
    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(hit_endpoint, args.url, args.path) for _ in range(args.requests)]
        for future in as_completed(futures):
            results.append(future.result())

    total_time = time.perf_counter() - start_time
    successes = [r for ok, r in results if ok]
    failures = len(results) - len(successes)

    print("\n--- Results ---")
    print(f"Total requests:   {len(results)}")
    print(f"Successful:       {len(successes)}")
    print(f"Failed:           {failures}")
    print(f"Total time:       {total_time:.2f}s")
    print(f"Requests/sec:     {len(results) / total_time:.1f}")

    if successes:
        successes.sort()
        p50 = statistics.median(successes)
        p95 = successes[int(len(successes) * 0.95) - 1]
        p99 = successes[int(len(successes) * 0.99) - 1]
        print(f"Latency p50:      {p50:.1f} ms")
        print(f"Latency p95:      {p95:.1f} ms")
        print(f"Latency p99:      {p99:.1f} ms")


if __name__ == "__main__":
    main()
