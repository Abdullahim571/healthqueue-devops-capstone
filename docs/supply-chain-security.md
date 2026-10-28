# HealthQueue Supply Chain Security Summary

How the HealthQueue pipeline protects the path from source code to the container running in
Kubernetes, and how it lines up with the **SLSA v1.0 Build track**.

> **What is verified vs assessed**
> - **§1 Verified results:** commands run on 2026-10-24 against the image currently deployed by Argo CD, with their actual outcomes.
> - **§3 SLSA level and §5 maturity:** a **self-assessment** by the project author, not an independent audit or certification. SLSA levels are not certified by anyone for this project.

---

## 1. Verified results (2026-10-24)

Image under test: the digest **currently running** in the `healthqueue` namespace (deployed by Argo CD from commit `a3307f0`):

```
ghcr.io/abdullahim571/healthqueue-devops-capstone@sha256:e86c8d49fa81008619797ba4e91c38a20a0d3911e39f8b8ebdb8c0e0903d236b
```

Verified with **cosign v3.1.4**, run in a throwaway container (no install):

| Check | Expected signer identity | Result |
|---|---|---|
| Image signature (`cosign verify`) | `…/healthqueue-devops-capstone/.github/workflows/ci.yml@refs/heads/main`, issuer `token.actions.githubusercontent.com` | ✅ Verified: claims valid, Rekor transparency-log entry verified, Fulcio certificate chain valid |
| SBOM attestation, SPDX (`cosign verify-attestation --type spdxjson`) | same CI workflow identity | ✅ Verified |
| SLSA provenance (`cosign verify-attestation --type slsaprovenance`) | `slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@refs/tags/v…` | ✅ Verified. Provenance records repository `Abdullahim571/healthqueue-devops-capstone`, ref `refs/heads/main`, workflow `ci`, commit `03b6be0f693b9fc39998e4868e39f3cf89ae2cec` |

The provenance is signed by the **SLSA generator's** identity, not by `ci.yml`. The build job
can't forge it, and that's the key L3 property (§3).

Other verified facts:

| Fact | How it was checked |
|---|---|
| All 7 CI jobs passed on the last three pushes to `main` (`819c191`, `5975284`, `03b6be0`) | GitHub Actions API |
| Trivy source scan (dependencies, secrets, config) and image scan gate on HIGH/CRITICAL | CI job results; local Trivy run of `k8s/`, `argocd/`, `cluster/` + Dockerfile: 0 HIGH/CRITICAL |
| A broken commit (`2b0e5de`) was stopped by the test job and never published or deployed | GitHub Actions API (run failed after 0.6 min) |
| The cluster runs the image **by digest**, not by tag | Pod `imageID` = the digest in `k8s/kustomization.yaml` |
| Each image's signature and attestations are stored in GHCR next to it (`sha256-<digest>.att`, and OCI referrers) | GHCR tag listing |
| Branch protection on `main` is **off** | GitHub API: `"protected": false` |
| Commits are **not signed** | `git log --format=%G?` → `N` for all 9 commits |

---

## 2. Controls in place

| Stage | Control | Where |
|---|---|---|
| **Source** | Every third-party GitHub Action pinned to a full commit SHA (the SLSA generator is pinned by tag, which it requires for self-verification) | `.github/workflows/ci.yml` |
| | Dependabot weekly updates for GitHub Actions, pip and Docker | `.github/dependabot.yml` |
| | Secret scanning of the repo on every run (Trivy `secret` scanner) | `scan-source` job |
| | Least-privilege workflow token (`contents: read` by default; jobs request only what they need) | `ci.yml` `permissions:` |
| **Dependencies** | Exact version pins (`fastapi==0.159.1`, `uvicorn==0.54.0`, `prometheus-client==0.26.0`) | `requirements.txt` |
| | Trivy dependency scan, failing on fixable HIGH/CRITICAL | `scan-source` job |
| **Build** | Ephemeral GitHub-hosted runners; multi-stage Docker build | `build` job, `Dockerfile` |
| | Image hardening: non-root UID 10001, pip removed from runtime image | `Dockerfile` |
| | **Scan before publish**: image built locally, scanned by Trivy, pushed only if the gate passes | `build` job |
| | **Build once, publish the scanned artifact** (added Week 8): no second build; the push step checks that the registry manifest references the scanned image ID before the digest is signed or deployed | `build` job, `push` step |
| **Artifacts** | SBOM in SPDX and CycloneDX (Syft); SPDX attached as a signed in-toto attestation | `build` job |
| | Keyless signing with cosign (GitHub OIDC → Fulcio certificate → Rekor log); no long-lived keys | `build` job |
| | Signature + SBOM attestation **verified inside the pipeline** before it continues | `build` job, last step |
| | SLSA provenance from the isolated `slsa-github-generator` reusable workflow | `provenance` job |
| **Deploy** | Image referenced **by immutable digest**, updated by CI in Git (`gitops-bump`) | `k8s/kustomization.yaml` |
| | GitOps: Argo CD applies only what is in `main`; `selfHeal` reverts manual cluster changes | `argocd/healthqueue-app.yaml` |
| | Restricted Pod Security on the namespace; read-only root filesystem, all capabilities dropped | `k8s/` |

---

## 3. SLSA v1.0 Build track alignment (SELF-ASSESSMENT)

| Level | Requirement (summary) | HealthQueue | Self-assessed |
|---|---|---|---|
| **Build L1** Provenance exists | Provenance describing how the artifact was built is generated and distributed | SLSA provenance is generated for every image built on `main` and attached to it in GHCR | ✅ Met (verified, §1) |
| **Build L2** Hosted build platform | Builds run on a hosted platform that generates and **signs** the provenance itself | GitHub-hosted runners; provenance signed keylessly by Sigstore and logged in Rekor | ✅ Met (signature verified, §1) |
| **Build L3** Hardened builds | The platform keeps builds isolated from each other, and the signing material used for provenance is out of reach of user-defined build steps | Provenance is created in the separate `generator_container_slsa3` reusable workflow. The build job can't access its OIDC identity, so it can't forge provenance (verified: the provenance signer is the generator, not `ci.yml`). Runners are ephemeral VMs | ✅ **Met, with one caveat** (below) |

**Caveat at L3:** both build steps use the shared GitHub Actions cache (`cache-from: type=gha`).
SLSA L3 expects one build to be unable to influence another, and a shared layer cache is a known way
that can happen (cache poisoning). Release builds without the cache (or with a cache scoped only to
`main`) would remove the caveat.

**Outside SLSA v1.0's Build track** (it does not cover source or dependency controls), there are
gaps worth stating openly:

| Area | Current state | Risk |
|---|---|---|
| Source protection | Branch protection **off**, no required PR review, no required status checks, unsigned commits, single maintainer | A compromised account or a mistake reaches `main` (and production) without a second person |
| Dependency integrity | Versions pinned, but **no hash pinning** (`--require-hashes`). *Week 8:* base image now pinned by digest | A tampered upstream Python package would still be accepted; builds aren't fully reproducible |
| Deploy-time verification | Argo CD deploys any digest committed to `main`. **Nothing in the cluster verifies the signature or provenance** before running the image | Signing proves where an image came from, but the cluster doesn't enforce it |
| Code scanning upload | SARIF upload to the GitHub Security tab is `continue-on-error` | Findings may not reach the Security tab; the Trivy gate still fails the build |

---

## 4. Threats and how they are handled

| Threat | Mitigation in this project | Status |
|---|---|---|
| Malicious or broken change merged to `main` | Unit tests + Trivy gates in CI | ⚠️ Partial: no required review (branch protection off) |
| Compromised third-party GitHub Action | Actions pinned to commit SHAs; Dependabot proposes updates | ✅ |
| Vulnerable dependency or base image | Trivy fs + image gates (HIGH/CRITICAL with a fix); weekly Dependabot | ✅ for known CVEs |
| Secret committed to the repo | Trivy secret scan; OpenTofu state and passphrase gitignored | ✅ |
| Build tampering / forged provenance | Isolated SLSA generator; keyless signing; Rekor log | ✅ (cache caveat, §3) |
| Image swapped in the registry after the build | Deployment pinned by digest; signature tied to that digest | ✅ (not enforced at admission, §3) |
| Unsigned or foreign image run in the cluster | — | ❌ No admission policy yet |
| Manual "hotfix" applied directly to the cluster | Argo CD `selfHeal` reverts it to the Git state | ✅ |

---

## 5. Maturity summary (SELF-ASSESSMENT, illustrative)

| Area | Self-assessed maturity | Basis |
|---|---|---|
| Build integrity and provenance | **High**: SLSA Build L3 aligned | §1 verified provenance, §3 |
| Artifact signing and SBOM | **High** | Keyless signing + SPDX attestation, verified in CI and independently |
| Vulnerability management | **Medium–High** | Gates on HIGH/CRITICAL; no runtime or continuous rescanning of deployed images |
| Dependency integrity | **Medium** | Exact pins + Dependabot; base image digest-pinned (Week 8); no Python package hashes |
| Source protection | **Low** | Branch protection off, no reviews, unsigned commits |
| Deploy-time enforcement | **Low** | Digest pinning and GitOps, but no signature verification at admission |

---

## 6. Roadmap (not implemented)

Ordered by risk reduced per unit of effort:

1. **Protect `main`:** require a pull request with review and passing `test` / `scan-source` / `build` checks; block force-pushes. (Free on public repos.) The `gitops-bump` bot needs a bypass or a dedicated deploy branch.
2. ~~**Pin the base image by digest**~~ **Done in Week 8:** `FROM python:3.13-slim@sha256:…`; Dependabot keeps the digest current.
3. **Hash-pin Python dependencies** (`pip-compile --generate-hashes`, `pip install --require-hashes`).
4. **Verify at admission:** Sigstore policy-controller or Kyverno `verifyImages` in the cluster, requiring a signature from the `ci.yml` identity **and** SLSA provenance from the generator before a pod can start.
5. **Remove the L3 caveat:** no shared GHA cache for release builds.
6. **Signed commits** and the **OpenSSF Scorecard** action for continuous posture checks.

---

## 7. Verify it yourself

No install needed, just Docker. Replace the digest with the one in `k8s/kustomization.yaml`.

```bash
REF=ghcr.io/abdullahim571/healthqueue-devops-capstone@sha256:<digest>
COSIGN="docker run --rm ghcr.io/sigstore/cosign/cosign:v3.1.4"  # the version used for §1
ISSUER=https://token.actions.githubusercontent.com
CI_ID=https://github.com/Abdullahim571/healthqueue-devops-capstone/.github/workflows/ci.yml@refs/heads/main

# 1. Signature
$COSIGN verify "$REF" --certificate-identity "$CI_ID" --certificate-oidc-issuer "$ISSUER"

# 2. SBOM attestation (SPDX)
$COSIGN verify-attestation "$REF" --type spdxjson \
  --certificate-identity "$CI_ID" --certificate-oidc-issuer "$ISSUER"

# 3. SLSA provenance. The generator stores it in the legacy attestation format,
#    so cosign v3 needs --new-bundle-format=false
$COSIGN verify-attestation "$REF" --type slsaprovenance --new-bundle-format=false \
  --certificate-identity-regexp '^https://github.com/slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@refs/tags/v[0-9].*$' \
  --certificate-oidc-issuer "$ISSUER"
```
