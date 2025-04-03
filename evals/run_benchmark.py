#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def post_json(url: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the DocPilot curated retrieval benchmark.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email", default="maya.chen@docpilot.health")
    parser.add_argument("--password", default="demo-clinical")
    parser.add_argument("--out", default="evals/latest_report.json")
    args = parser.parse_args()

    try:
        login = post_json(
            f"{args.base_url}/auth/login",
            {"email": args.email, "password": args.password},
        )
        report = post_json(f"{args.base_url}/benchmarks/run", {}, login["access_token"])
    except urllib.error.URLError as exc:
        print(f"Benchmark failed: {exc}", file=sys.stderr)
        return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        f"Acceptance: {report['acceptance_rate']}% "
        f"({report['accepted']}/{report['total']}), "
        f"improvement from baseline: +{report['improvement_from_baseline']}%"
    )
    print(f"Saved report to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
