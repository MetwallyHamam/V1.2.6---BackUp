"""Run an explicit login burst against a staging or approved production URL."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def login_once(url: str, login: str, password: str, timeout: float) -> tuple[int, float]:
    payload = json.dumps({"login": login, "password": password}).encode()
    request = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - operator supplies URL
            response.read()
            return response.status, time.perf_counter() - started
    except HTTPError as exc:
        exc.read()
        return exc.code, time.perf_counter() - started
    except (TimeoutError, URLError):
        return 0, time.perf_counter() - started


def main() -> int:
    parser = argparse.ArgumentParser(description="Concurrent SupportHub login smoke/load test")
    parser.add_argument("url", help="Full /api/v1/auth/login URL")
    parser.add_argument("login", help="Dedicated load-test account")
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--password-env", default="SUPPORTHUB_LOAD_TEST_PASSWORD")
    args = parser.parse_args()
    password = os.environ.get(args.password_env)
    if not password:
        parser.error(f"Set {args.password_env} to the dedicated load-test password.")
    if args.concurrency < 1 or args.requests < 1:
        parser.error("--concurrency and --requests must be positive.")

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(login_once, args.url, args.login, password, args.timeout)
            for _ in range(args.requests)
        ]
        results = [future.result() for future in as_completed(futures)]

    statuses: dict[int, int] = {}
    for status, _ in results:
        statuses[status] = statuses.get(status, 0) + 1
    durations = [duration for _, duration in results]
    ordered = sorted(durations)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    print(json.dumps({
        "requests": len(results),
        "concurrency": args.concurrency,
        "statuses": statuses,
        "mean_seconds": round(statistics.mean(durations), 3),
        "p95_seconds": round(p95, 3),
        "max_seconds": round(max(durations), 3),
    }, indent=2))
    return 0 if all(status == 200 for status, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
