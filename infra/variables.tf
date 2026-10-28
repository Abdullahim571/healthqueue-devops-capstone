variable "state_passphrase" {
  description = "Passphrase used to encrypt state and plan files (min 16 chars). Set via TF_VAR_state_passphrase."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.state_passphrase) >= 16
    error_message = "state_passphrase must be at least 16 characters."
  }
}

variable "docker_host" {
  description = "Docker Engine endpoint. Default is Docker Desktop on Windows; use unix:///var/run/docker.sock on Linux/macOS."
  type        = string
  default     = "npipe:////./pipe/dockerDesktopLinuxEngine"
}

variable "name_prefix" {
  description = "Prefix for every Docker resource name, keeping them apart from other projects."
  type        = string
  default     = "healthqueue"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}$", var.name_prefix))
    error_message = "name_prefix must be lowercase letters, digits or hyphens (2-31 chars, starting with a letter)."
  }
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "image_tag" {
  description = "Tag for the locally built API image (also passed to the app as APP_VERSION)."
  type        = string
  default     = "tofu"
}

variable "host_port" {
  description = "Port on 127.0.0.1 where the API is published."
  type        = number
  default     = 8000

  validation {
    condition     = var.host_port >= 1024 && var.host_port <= 65535
    error_message = "host_port must be between 1024 and 65535."
  }
}

variable "memory_limit_mb" {
  description = "Hard memory limit for the API container, in MB. Default matches the 192Mi limit in k8s/deployment.yaml."
  type        = number
  default     = 192

  validation {
    condition     = var.memory_limit_mb >= 64 && var.memory_limit_mb <= 2048
    error_message = "memory_limit_mb must be between 64 and 2048."
  }
}

variable "cpu_limit" {
  description = "Maximum CPUs the API container may use, as a decimal string (e.g. \"0.5\"). Default matches the 500m limit in k8s/deployment.yaml."
  type        = string
  default     = "0.5"

  validation {
    condition     = can(tonumber(var.cpu_limit)) && try(tonumber(var.cpu_limit) > 0 && tonumber(var.cpu_limit) <= 4, false)
    error_message = "cpu_limit must be a number greater than 0 and at most 4, e.g. \"0.5\"."
  }
}

variable "network_subnet" {
  description = "CIDR for the private bridge network."
  type        = string
  default     = "172.28.0.0/24"

  validation {
    condition     = can(cidrhost(var.network_subnet, 0))
    error_message = "network_subnet must be a valid CIDR block."
  }
}
