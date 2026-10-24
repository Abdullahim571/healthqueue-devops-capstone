# HealthQueue — Appointment Scheduling API (DevOps Capstone)

Patient-facing appointment scheduling API with a production-grade DevOps pipeline.
**All patient data is fictional.**

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
pytest -v                          # run tests
uvicorn app.main:app --reload      # http://localhost:8000/docs
```

With Docker:

```bash
docker build -t healthqueue-api:dev .
docker run -p 8000:8000 healthqueue-api:dev
```

## API

| Method | Path | Description |
|---|---|---|
| GET | `/patients` | List (fictional) patients |
| GET | `/appointments?patient_id=` | List appointments |
| POST | `/appointments` | Book (409 on provider double-booking) |
| GET | `/appointments/{id}` | Get one |
| DELETE | `/appointments/{id}` | Cancel |
| GET | `/healthz`, `/readyz` | Liveness / readiness probes |
| GET | `/metrics` | Prometheus metrics (SLI source) |

## CI/CD pipeline (`.github/workflows/ci.yml`)

| Stage | Tool | Gate |
|---|---|---|
| Unit tests | pytest | any failure |
| Source scan | Trivy fs (deps, secrets, IaC misconfig) | HIGH/CRITICAL |
| Build | Docker Buildx (multi-stage, non-root, no pip at runtime) | — |
| Image scan | Trivy image (+ SARIF to Security tab) | HIGH/CRITICAL with a fix |
| SBOM | Syft (SPDX + CycloneDX) | — |
| Publish | GHCR, by digest | main only |
| Sign | cosign keyless (Sigstore / GitHub OIDC) | main only |
| Attest | cosign SBOM attestation + SLSA L3 provenance | main only |
| Verify | `cosign verify` / `verify-attestation` | main only |
| Deliver | Digest bump in `k8s/` → Argo CD sync | main only |

## Kubernetes + Argo CD (local kind cluster)

| Path | Contents |
|---|---|
| `cluster/kind-config.yaml` | Single-node kind cluster named `healthqueue` |
| `argocd/kustomization.yaml` | Argo CD v3.5.6, trimmed (no dex / notifications / ApplicationSet) with memory limits |
| `argocd/healthqueue-app.yaml` | Argo CD Application syncing `k8s/` from `main` (auto-sync, prune, self-heal) |
| `k8s/` | Namespace (restricted Pod Security), Deployment, Service; image pinned by digest |

```bash
kind create cluster --config cluster/kind-config.yaml
kubectl --context kind-healthqueue apply --server-side --force-conflicts -k argocd/
kubectl --context kind-healthqueue apply -f argocd/healthqueue-app.yaml

# Argo CD UI: https://localhost:8443  (user: admin)
kubectl --context kind-healthqueue -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
kubectl --context kind-healthqueue -n argocd port-forward svc/argocd-server 8443:443

# API (port 8000 is taken by the OpenTofu container)
kubectl --context kind-healthqueue -n healthqueue port-forward svc/healthqueue-api 8080:80
```

Verify a published image yourself:

```bash
cosign verify ghcr.io/<owner>/healthqueue-devops-capstone@sha256:<digest> \
  --certificate-identity https://github.com/<owner>/healthqueue-devops-capstone/.github/workflows/ci.yml@refs/heads/main \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```
