terraform {
  required_version = ">= 1.8.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.6"
    }
  }

  # State management: state lives in a local file at an explicit path. It is
  # gitignored (*.tfstate) and encrypted at rest by the block below.
  backend "local" {
    path = "terraform.tfstate"
  }

  # Native OpenTofu state + plan encryption (AES-GCM, key derived via PBKDF2).
  # The passphrase comes from TF_VAR_state_passphrase and is never committed.
  # `enforced = true` refuses to ever write unencrypted state or plan files.
  encryption {
    key_provider "pbkdf2" "main" {
      passphrase = var.state_passphrase
    }

    method "aes_gcm" "main" {
      keys = key_provider.pbkdf2.main
    }

    state {
      method   = method.aes_gcm.main
      enforced = true
    }

    plan {
      method   = method.aes_gcm.main
      enforced = true
    }
  }
}

provider "docker" {
  host = var.docker_host
}
