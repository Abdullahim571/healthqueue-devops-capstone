# Security Policy

HealthQueue is a DevOps portfolio project. It handles **fictional patient data only** and is
deployed to a local kind cluster, not to a public environment. Security reports are still welcome:
the pipeline, supply chain and Kubernetes configuration are meant to reflect production practice.

## Supported versions

Only the latest commit on `main` (the image digest in [`k8s/kustomization.yaml`](k8s/kustomization.yaml))
is maintained. Older images in GHCR are not patched.

## Reporting a vulnerability

Please **do not open a public issue** for a security problem.

Use GitHub's private vulnerability reporting: open the repository's **Security** tab and choose
**Report a vulnerability**. Include:

- what is affected (file, workflow, image digest, endpoint)
- steps to reproduce, and the impact you expect
- any suggested fix

You can expect an acknowledgement within **7 days**. Confirmed issues are fixed on `main` and noted
in the commit message. If you'd like to be credited, say so in your report.

## In scope

- The CI/CD workflows in `.github/workflows/` (e.g. token permissions, injection, pinning)
- Supply chain controls: image signing, SBOM and SLSA provenance verification
- The container image, Dockerfile and Python dependencies
- Kubernetes, Argo CD and OpenTofu configuration
- The API in `app/`

## Out of scope

- The lack of authentication on the API. It's a documented limitation of this capstone (see
  *Known limitations* in the [README](README.md)).
- Findings that require access to the maintainer's local machine or kind cluster.
- Denial of service against the local environment.

## How this project checks itself

Dependency, secret and IaC scanning (Trivy), image vulnerability gating, signed images with SBOM
and SLSA provenance attestations, and Dependabot updates. Details:
[docs/supply-chain-security.md](docs/supply-chain-security.md).
