"""Compute the four DORA metrics from a deployments CSV and print a Markdown report.

Usage:  python dora_metrics.py [synthetic_deployments.csv]
Standard library only. Percentiles use statistics.quantiles (inclusive method: p90 never exceeds the largest value).
"""
import csv
import statistics
import sys
from datetime import datetime, timedelta

DAYS = 90
WINDOW_START = datetime(2026, 7, 26)  # same window as generate_synthetic_deployments.py

# Performance bands adapted from the DORA "Accelerate State of DevOps" 2023 report.
# Thresholds differ between report editions - check the edition your course uses.
# Each list is evaluated top-down; the first matching band wins.
BANDS = {
    "deploys_per_day": [
        ("Elite", lambda v: v >= 1), ("High", lambda v: v >= 1 / 7),
        ("Medium", lambda v: v >= 1 / 30), ("Low", lambda v: True)],
    "lead_time_hours": [
        ("Elite", lambda v: v < 24), ("High", lambda v: v < 24 * 7),
        ("Medium", lambda v: v < 24 * 30), ("Low", lambda v: True)],
    "change_failure_rate": [
        ("Elite", lambda v: v <= 0.05), ("High", lambda v: v <= 0.10),
        ("Medium", lambda v: v <= 0.15), ("Low", lambda v: True)],
    "recovery_hours": [
        ("Elite", lambda v: v < 1), ("High", lambda v: v < 24),
        ("Medium", lambda v: v < 24 * 7), ("Low", lambda v: True)],
}


def band(metric: str, value: float) -> str:
    return next(name for name, test in BANDS[metric] if test(value))


def p90(values: list[float]) -> float:
    return statistics.quantiles(values, n=10, method="inclusive")[8] if len(values) >= 2 else values[0]


def fmt_minutes(m: float) -> str:
    return f"{m:.0f} min" if m < 120 else f"{m / 60:.1f} h"


def deployed_at(row: dict) -> datetime:
    return datetime.strptime(row["deployed_at"], "%Y-%m-%dT%H:%M:%SZ")


def summarize(rows: list[dict], days: int) -> dict:
    lead = [float(r["lead_time_minutes"]) for r in rows]
    failed = [r for r in rows if r["change_failed"] == "true"]
    rec = [float(r["recovery_minutes"]) for r in failed]
    return {
        "deploys": len(rows), "per_day": len(rows) / days,
        "active_days": len({r["deployed_at"][:10] for r in rows}),
        "lead_median": statistics.median(lead), "lead_p90": p90(lead),
        "failed": len(failed), "cfr": len(failed) / len(rows),
        "rec_median": statistics.median(rec) if rec else None,
        "rec_p90": p90(rec) if rec else None,
        "rollbacks": sum(r["recovery_method"] == "rollback" for r in failed),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    path = sys.argv[1] if len(sys.argv) > 1 else "synthetic_deployments.csv"
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    start = WINDOW_START
    s = summarize(rows, DAYS)
    synthetic = all(r["synthetic"] == "true" for r in rows)

    print(f"Source: `{path}` · {s['deploys']} deployments · {DAYS} days from {start:%Y-%m-%d}"
          f"{' · **SYNTHETIC DATA**' if synthetic else ''}\n")
    print("| DORA metric | Result | Band |")
    print("|---|---|---|")
    print(f"| Deployment frequency | {s['per_day']:.2f} deploys/day ({s['per_day'] * 7:.1f}/week); "
          f"deployed on {s['active_days']} of {DAYS} days | {band('deploys_per_day', s['per_day'])} |")
    print(f"| Lead time for changes | median {fmt_minutes(s['lead_median'])}, "
          f"p90 {fmt_minutes(s['lead_p90'])} | {band('lead_time_hours', s['lead_median'] / 60)} |")
    print(f"| Change failure rate | {s['failed']} of {s['deploys']} = {s['cfr']:.1%} "
          f"| {band('change_failure_rate', s['cfr'])} |")
    if s["rec_median"] is not None:
        print(f"| Failed deployment recovery time | median {fmt_minutes(s['rec_median'])}, "
              f"p90 {fmt_minutes(s['rec_p90'])} ({s['rollbacks']} of {s['failed']} by rollback) "
              f"| {band('recovery_hours', s['rec_median'] / 60)} |")

    print("\n**By 30-day period**\n")
    print("| Period | Deploys | Deploys/day | Median lead time | CFR | Median recovery |")
    print("|---|---|---|---|---|---|")
    for i in range(DAYS // 30):
        lo, hi = start + timedelta(days=30 * i), start + timedelta(days=30 * (i + 1))
        p = summarize([r for r in rows if lo <= deployed_at(r) < hi], 30)
        rec = fmt_minutes(p["rec_median"]) if p["rec_median"] is not None else "n/a"
        print(f"| {lo:%Y-%m-%d} – {hi - timedelta(days=1):%Y-%m-%d} | {p['deploys']} "
              f"| {p['per_day']:.2f} | {fmt_minutes(p['lead_median'])} | {p['cfr']:.1%} | {rec} |")


if __name__ == "__main__":
    main()
