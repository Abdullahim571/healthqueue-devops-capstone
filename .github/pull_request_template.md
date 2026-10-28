## What and why

<!-- What does this change, and what problem does it solve? Link an issue if there is one. -->

## Type of change

- [ ] Application (`app/`, `tests/`)
- [ ] CI/CD or supply chain (`.github/`, `Dockerfile`)
- [ ] Infrastructure (`infra/`)
- [ ] Kubernetes / Argo CD (`k8s/`, `argocd/`, `cluster/`)
- [ ] Observability (`observability/`, `docs/monitoring-plan.md`)
- [ ] Documentation only

## Checklist

- [ ] `pre-commit run --all-files` passes (ruff, YAML, `tofu fmt`)
- [ ] `pytest` passes, and new behaviour has a test
- [ ] No secrets, credentials or **real patient data** added (fictional data only)
- [ ] Any new Kubernetes resource kind is added to the AppProject whitelist (`argocd/healthqueue-project.yaml`)
- [ ] Any new GitHub Action is pinned to a full commit SHA
- [ ] Docs updated if behaviour, setup or limitations changed

## Deployment impact

<!-- Merging to main deploys automatically through Argo CD. Note anything reviewers should know:
     restarts, data loss (the store is in memory), manual steps, rollback plan. -->
