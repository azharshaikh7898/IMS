#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def post_signal(base_url: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{base_url.rstrip('/')}/api/signals",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=10) as response:
        response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay IMS sample failure scenarios into /api/signals")
    parser.add_argument("--base-url", default="http://127.0.0.1:5173", help="Base URL (frontend proxy or backend)")
    parser.add_argument("--scenario", choices=["rdbms_failure_p0", "cache_failure_p2", "burst_signals", "all"], default="all")
    parser.add_argument("--burst-repeat", type=int, default=40, help="How many times to repeat burst_signals payloads")
    parser.add_argument("--delay-ms", type=int, default=40, help="Delay between posts in milliseconds")
    args = parser.parse_args()

    samples_file = Path(__file__).with_name("failure_scenarios.json")
    payloads = json.loads(samples_file.read_text(encoding="utf-8"))

    selected: list[dict] = []
    if args.scenario == "all":
        selected.extend(payloads["rdbms_failure_p0"])
        selected.extend(payloads["cache_failure_p2"])
        for _ in range(args.burst_repeat):
            selected.extend(payloads["burst_signals"])
    elif args.scenario == "burst_signals":
        for _ in range(args.burst_repeat):
            selected.extend(payloads["burst_signals"])
    else:
        selected.extend(payloads[args.scenario])

    success = 0
    for index, payload in enumerate(selected, start=1):
        try:
            post_signal(args.base_url, payload)
            success += 1
        except HTTPError as exc:
            print(f"[{index}] HTTP error: {exc.code} {exc.reason}", file=sys.stderr)
        except URLError as exc:
            print(f"[{index}] URL error: {exc.reason}", file=sys.stderr)
        time.sleep(args.delay_ms / 1000)

    print(f"Sent {success}/{len(selected)} signals to {args.base_url}")
    return 0 if success > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
