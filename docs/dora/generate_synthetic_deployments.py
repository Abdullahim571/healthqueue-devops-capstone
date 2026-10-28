"""Generate 90 days of SYNTHETIC HealthQueue production deployments for a DORA baseline.

Every row is labelled synthetic=true. The model is anchored on timings measured in this
project on 2026-10-23/24 (see docs/dora-baseline.md, "Verified project data"):
  - CI pipeline duration (push -> image signed + digest committed): 2.4-3.1 min
  - Argo CD pickup (digest commit -> deployed):                     1.5-2.2 min
Everything else (how often the team ships, review wait, failure and recovery behaviour)
is an assumption, listed in ASSUMPTIONS below.

Usage:  python generate_synthetic_deployments.py   ->  synthetic_deployments.csv
Standard library only; the fixed seed makes the output reproducible.
"""
import csv
import math
import random
from datetime import UTC, datetime, timedelta

SEED = 571
START = datetime(2026, 7, 26, tzinfo=UTC)  # 90 days ending 2026-10-23
DAYS = 90

# Measured in this project (minutes).
CI_MINUTES = (2.4, 3.1)
ARGO_PICKUP_MINUTES = (1.5, 2.2)

# Assumptions (illustrative, not measured).
ASSUMPTIONS = {
    "deploys_per_weekday_mean": 1.6,  # small team, trunk-based, auto-deploy on merge
    "deploys_per_weekend_day_mean": 0.15,
    "review_wait_median_hours": 2.5,  # first commit -> merged to main (log-normal)
    "review_wait_sigma": 0.9,
    "change_failure_probability": 0.08,
    "detection_median_minutes": 12,  # burn-rate alert fires / user report (log-normal)
    "rollback_minutes": (3, 6),  # git revert + Argo CD sync (CI skipped via [skip ci])
    "fix_forward_share": 0.25,  # failures fixed forward instead of rolled back
    "fix_forward_median_hours": 3.0,
}


def poisson(rng: random.Random, lam: float) -> int:
    """Knuth's algorithm (fine for small lambda)."""
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def lognormal_median(rng: random.Random, median: float, sigma: float) -> float:
    return rng.lognormvariate(math.log(median), sigma)


def iso(t: datetime | None) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ") if t else ""


def main() -> None:
    rng = random.Random(SEED)
    a = ASSUMPTIONS
    rows = []
    for day in range(DAYS):
        date = START + timedelta(days=day)
        weekend = date.weekday() >= 5
        lam = a["deploys_per_weekend_day_mean"] if weekend else a["deploys_per_weekday_mean"]
        for _ in range(poisson(rng, lam)):
            # Deploys happen during working hours, 09:00-17:00 UTC.
            deployed = date + timedelta(hours=9, minutes=rng.uniform(0, 8 * 60))
            pipeline = rng.uniform(*CI_MINUTES) + rng.uniform(*ARGO_PICKUP_MINUTES)
            review = lognormal_median(rng, a["review_wait_median_hours"], a["review_wait_sigma"]) * 60
            committed = deployed - timedelta(minutes=review + pipeline)

            failed = rng.random() < a["change_failure_probability"]
            restored, recovery, method = None, None, ""
            if failed:
                detect = lognormal_median(rng, a["detection_median_minutes"], 0.6)
                if rng.random() < a["fix_forward_share"]:
                    method = "fix-forward"
                    recovery = detect + lognormal_median(rng, a["fix_forward_median_hours"], 0.5) * 60
                else:
                    method = "rollback"
                    recovery = detect + rng.uniform(*a["rollback_minutes"])
                restored = deployed + timedelta(minutes=recovery)
            rows.append((deployed, committed, failed, restored, recovery, method))

    rows.sort(key=lambda r: r[0])
    with open("synthetic_deployments.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["deploy_id", "commit_sha", "first_commit_at", "deployed_at", "lead_time_minutes",
                    "change_failed", "recovery_method", "restored_at", "recovery_minutes", "synthetic"])
        for i, (deployed, committed, failed, restored, recovery, method) in enumerate(rows, 1):
            w.writerow([f"SYN-{i:04d}", f"{rng.getrandbits(28):07x}", iso(committed), iso(deployed),
                        f"{(deployed - committed).total_seconds() / 60:.1f}", str(failed).lower(), method,
                        iso(restored), f"{recovery:.1f}" if recovery else "", "true"])
    print(f"wrote {len(rows)} synthetic deployments to synthetic_deployments.csv (seed {SEED})")


if __name__ == "__main__":
    main()
