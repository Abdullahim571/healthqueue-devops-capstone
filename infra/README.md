# HealthQueue infrastructure (OpenTofu, local Docker)

Provisions the HealthQueue API on the local Docker Engine at **$0 cost**: no cloud account needed.

| Resource | Name | Purpose |
|---|---|---|
| `docker_network.app` | `healthqueue-dev-net` | Private bridge network (`172.28.0.0/24`) |
| `docker_volume.data` | `healthqueue-dev-data` | Persistent data, mounted at `/data` |
| `docker_image.api` | `healthqueue-api:tofu` | Built from the project `Dockerfile`; rebuilt when `app/`, `Dockerfile` or `requirements.txt` change |
| `docker_container.api` | `healthqueue-dev-api` | Hardened API container on `127.0.0.1:8000` |

## State management

- **Backend:** `local`, at `infra/terraform.tfstate` (gitignored).
- **Encryption:** OpenTofu native encryption (PBKDF2 + AES-GCM) for both state and plan files, `enforced = true`.
- **Passphrase:** supplied via `TF_VAR_state_passphrase`, never committed. Losing it makes the state unreadable.
- **Provider lock:** `.terraform.lock.hcl` is committed so every `init` installs the same provider build.

## Usage (PowerShell)

```powershell
cd infra
$env:TF_VAR_state_passphrase = Get-Content "$env:USERPROFILE\.healthqueue\tofu-state-passphrase.txt" -Raw

tofu init
tofu fmt -check
tofu validate
tofu plan "-out=healthqueue.tfplan"
tofu apply "healthqueue.tfplan"

tofu output                 # URLs, names
curl http://127.0.0.1:8000/healthz

tofu state list             # resources tracked in state
tofu state show docker_container.api
tofu plan                   # should report "No changes": state matches reality

tofu destroy                # remove everything this config created
```

Variables are documented in `variables.tf`; override them with a `terraform.tfvars` (see `terraform.tfvars.example`).
