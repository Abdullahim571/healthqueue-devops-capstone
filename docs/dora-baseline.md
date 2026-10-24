# HealthQueue DORA Metrics Baseline

A baseline of the four DORA delivery metrics for the HealthQueue appointment scheduling API.

> **Read this first: data sources**
> - **§1 Verified project data:** real measurements from GitHub Actions, Git and Argo CD (2026-10-22 → 2026-10-24). Only 2 change deployments exist, which is far too few for a baseline.
> - **§2–§4 SYNTHETIC data:** 90 days of *generated* deployments, as the assignment requires. The pipeline timings in the model come from §1; everything else (deploy cadence, review wait, failure and recovery behaviour) is an **assumption**. **None of the synthetic numbers describe real HealthQueue history.**

| File | Purpose |
|---|---|
| [`dora/generate_synthetic_deployments.py`](dora/generate_synthetic_deployments.py) | Seeded generator (seed 571, standard library only) |
| [`dora/synthetic_deployments.csv`](dora/synthetic_deployments.csv) | The 83 generated deployments. Every row has `synthetic=true` |
| [`dora/dora_metrics.py`](dora/dora_metrics.py) | Computes the four metrics and their bands from any CSV in this format |

```bash
cd docs/dora
python generate_synthetic_deployments.py   # wrote 83 synthetic deployments ... (seed 571)
python dora_metrics.py                     # prints the tables in §3
```

The generator is deterministic: two runs produced byte-identical CSVs (MD5 `5a2cd16d…`).

---

## 1. Verified project data (real)

**Production deployments** (Argo CD sync history, `kind-healthqueue` cluster):

| Argo CD revision | Code change deployed | Change committed (UTC) | Digest commit by CI | Deployed by Argo CD | **Lead time** |
|---|---|---|---|---|---|
| `5975284` | Initial Application creation (image built from `819c191`) | — | — | 2026-10-24 00:01:30 | *excluded: bootstrap, not a change* |
| `8e01182` | `5975284` Kubernetes manifests + Argo CD | 00:01:16 | 00:04:13 | 00:06:21 | **5 min 05 s** |
| `a3307f0` | `03b6be0` CI paths-ignore change | 00:23:45 | 00:26:09 | 00:27:40 | **3 min 55 s** |

**CI pipeline** (GitHub Actions push runs on `main`):

| Commit | Result | Duration |
|---|---|---|
| `03b6be0` | success | 2.4 min |
| `5975284` | success | 2.9 min |
| `819c191` | success | 3.1 min |
| `4c22014` | success | 3.1 min |
| `2b0e5de` | **failure**: `ModuleNotFoundError: No module named 'app'` in unit tests | 0.6 min |

What the real data shows:

| DORA metric | Real value | Note |
|---|---|---|
| Deployment frequency | 2 change deployments, both on 2026-10-24 | Kubernetes delivery has existed for one day, so no meaningful rate yet |
| Lead time for changes | **3 min 55 s and 5 min 05 s** (commit → running in the cluster) | ~2.4–3.1 min CI + ~1.5–2.1 min Argo CD pickup |
| Change failure rate | **0 of 2** | No deployment caused a failure |
| Failed deployment recovery time | **n/a** (no production failures) | The only failure was a CI run, caught **before** deployment. CI went from red to green in 53.7 min (failed run finished 15:06:56 UTC, fix `4c22014` green at 16:00:40 UTC). That's pipeline recovery, not a production incident |

The broken commit was stopped by the test gate and never deployed. That's the pipeline doing its job.

---

## 2. Synthetic data model

| Input | Value | Source |
|---|---|---|
| Window | 2026-07-26 → 2026-10-23 (90 days) | assignment |
| CI duration | uniform 2.4–3.1 min | **measured** (§1) |
| Argo CD pickup | uniform 1.5–2.2 min | **measured** (§1) |
| Deploys per day | Poisson, mean **1.6** on weekdays and **0.15** on weekend days, 09:00–17:00 UTC | *assumption*: small team, trunk-based, auto-deploy on merge |
| Review / wait time (first commit → merge) | log-normal, median **2.5 h** | *assumption* |
| Change failure probability | **8 %** per deployment | *assumption* |
| Detection time | log-normal, median **12 min** | *assumption*: burn-rate alerts from the [monitoring plan](monitoring-plan.md) |
| Recovery | **75 %** rolled back (`git revert` of the deploy commit, 3–6 min); **25 %** fixed forward (log-normal, median 3 h) | *assumption*, following the rollback-first runbook |

Lead time = review wait + CI + Argo CD pickup. Recovery time = detection + rollback (or fix-forward).

---

## 3. Baseline results (SYNTHETIC)

Output of `python dora_metrics.py`:

Source: `synthetic_deployments.csv` · 83 deployments · 90 days from 2026-07-26 · **SYNTHETIC DATA**

| DORA metric | Result | Band |
|---|---|---|
| Deployment frequency | 0.92 deploys/day (6.5/week); deployed on 49 of 90 days | High |
| Lead time for changes | median 2.6 h, p90 7.3 h | Elite |
| Change failure rate | 5 of 83 = 6.0% | High |
| Failed deployment recovery time | median 16 min, p90 2.1 h (4 of 5 by rollback) | Elite |

**By 30-day period**

| Period | Deploys | Deploys/day | Median lead time | CFR | Median recovery |
|---|---|---|---|---|---|
| 2026-07-26 – 2026-08-24 | 24 | 0.80 | 3.3 h | 8.3% | 18 min |
| 2026-08-25 – 2026-09-23 | 29 | 0.97 | 3.1 h | 6.9% | 12 min |
| 2026-09-24 – 2026-10-23 | 30 | 1.00 | 2.1 h | 3.3% | 3.3 h |

The last period's median recovery is 3.3 h because it contains a single failure, and that one was
fixed forward. With such small counts, one incident moves a 30-day median a lot. That's why the
baseline uses the full 90 days.

**Performance bands** used by `dora_metrics.py`. They're adapted from the DORA *Accelerate State
of DevOps* 2023 report. Thresholds vary between report editions, so check the one your course uses.

| Metric | Elite | High | Medium | Low |
|---|---|---|---|---|
| Deployment frequency | ≥ 1/day (on demand) | ≥ 1/week | ≥ 1/month | < 1/month |
| Lead time for changes | < 1 day | < 1 week | < 1 month | ≥ 1 month |
| Change failure rate | ≤ 5 % | ≤ 10 % | ≤ 15 % | > 15 % |
| Failed deployment recovery time | < 1 hour | < 1 day | < 1 week | ≥ 1 week |

---

## 4. What the baseline says (SYNTHETIC; interpretation)

1. **The pipeline is not the bottleneck.** Of a 2.6 h median lead time, only ~5 min (measured) is CI + GitOps. The rest is the *assumed* review wait. Faster delivery would come from smaller PRs and faster review, not from faster CI.
2. **Deployment frequency is just short of Elite** (0.92/day vs ≥ 1/day). Weekends barely deploy (by design). Shipping changes individually instead of batching them would cross the line.
3. **Change failure rate of 6 % (High).** Getting to ≤ 5 % means catching more before production: PR checks with required reviews, and a canary or `/readyz` smoke test after sync.
4. **Rollback is much faster than fixing forward.** The 4 rollbacks recovered in 11.7–19.2 min; the one fix-forward took 200.6 min (3.3 h). This ties directly to the error budget: the 99.5 % availability SLO allows **216 min** of downtime per 30 days. A 16-min full outage uses 7.4 % of that, while the 200.6-min fix-forward, if it had been a full outage, would use **93 %** of the monthly budget in one incident. This supports the runbook's "roll back first, diagnose later" rule.

| Improvement target (next 90 days) | Baseline (synthetic) | Target |
|---|---|---|
| Deployment frequency | 0.92/day | ≥ 1/day |
| Lead time (median) | 2.6 h | < 2 h |
| Change failure rate | 6.0 % | ≤ 5 % |
| Recovery time (median) | 16 min | < 15 min, and **always** roll back before fixing forward |

---

## 5. Measuring the real metrics from now on

All four metrics can be collected from data the project already produces:

| Metric | Real data source |
|---|---|
| Deployment frequency | Argo CD history (`kubectl -n argocd get application healthqueue-api -o jsonpath='{.status.history}'`) or `argocd_app_sync_total` in Prometheus |
| Lead time | Author time of the code commit named in each `deploy: healthqueue-api <sha>` commit → `deployedAt` of that revision in Argo CD history |
| Change failure rate | Deployments followed within 24 h by a `Revert "deploy: …"` commit or a SEV1/SEV2 incident |
| Recovery time | Incident start (first burn-rate alert) → resolved (alert cleared / SLI back within SLO), from the postmortem |

Export those events in this CSV format with `synthetic=false`, and `dora_metrics.py` will report them
the same way, without the "SYNTHETIC DATA" label.
