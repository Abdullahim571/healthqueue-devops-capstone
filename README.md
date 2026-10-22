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

Verify a published image yourself:

```bash
cosign verify ghcr.io/<owner>/healthqueue-devops-capstone@sha256:<digest> \
  --certificate-identity https://github.com/<owner>/healthqueue-devops-capstone/.github/workflows/ci.yml@refs/heads/main \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```
