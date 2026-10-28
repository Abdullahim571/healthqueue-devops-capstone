locals {
  project_root = abspath("${path.module}/..")

  labels = {
    "app"         = "healthqueue-api"
    "project"     = "healthqueue-devops-capstone"
    "environment" = var.environment
    "managed-by"  = "opentofu"
  }

  # Rebuild the image whenever the app source, dependencies or Dockerfile change.
  source_hash = sha1(join("", concat(
    [for f in sort(fileset(local.project_root, "app/**/*.py")) : filesha1("${local.project_root}/${f}")],
    [filesha1("${local.project_root}/Dockerfile"), filesha1("${local.project_root}/requirements.txt")],
  )))
}

# 1) Private bridge network, isolated from other projects' networks.
resource "docker_network" "app" {
  name   = "${var.name_prefix}-${var.environment}-net"
  driver = "bridge"

  # Set the gateway explicitly: Docker assigns one if omitted, which the provider
  # then reports as drift and forces a network (and container) replacement.
  ipam_config {
    subnet  = var.network_subnet
    gateway = cidrhost(var.network_subnet, 1)
  }

  dynamic "labels" {
    for_each = local.labels
    content {
      label = labels.key
      value = labels.value
    }
  }
}

# 2) Named volume reserved for the future database layer (unused by the in-memory app today;
#    mounted read-only in the container below).
resource "docker_volume" "data" {
  name = "${var.name_prefix}-${var.environment}-data"

  dynamic "labels" {
    for_each = local.labels
    content {
      label = labels.key
      value = labels.value
    }
  }
}

# 3) API image built from the project's existing multi-stage Dockerfile.
resource "docker_image" "api" {
  name         = "${var.name_prefix}-api:${var.image_tag}"
  keep_locally = false

  build {
    context    = local.project_root
    dockerfile = "Dockerfile"
    build_args = {
      APP_VERSION = var.image_tag
    }
    label = local.labels
  }

  triggers = {
    source_hash = local.source_hash
  }
}

# 4) API container, hardened: non-root (from the image), read-only rootfs,
#    all Linux capabilities dropped, no privilege escalation, loopback-only port,
#    and CPU/memory limits matching the Kubernetes Deployment (k8s/deployment.yaml).
resource "docker_container" "api" {
  name    = "${var.name_prefix}-${var.environment}-api"
  image   = docker_image.api.image_id
  restart = "unless-stopped"

  env = [
    "APP_VERSION=${var.image_tag}",
  ]

  # A runaway request or memory leak can't starve Docker Desktop (and the kind cluster beside it).
  # memory_swap is left unset on purpose: the provider may read it back as -1 and report drift.
  memory = var.memory_limit_mb
  cpus   = var.cpu_limit

  ports {
    internal = 8000
    external = var.host_port
    ip       = "127.0.0.1"
  }

  networks_advanced {
    name = docker_network.app.id
  }

  # Reserved for the future database layer. The app keeps data in memory today and never reads
  # /data, so the mount is read-only until something actually needs to write there.
  volumes {
    volume_name    = docker_volume.data.name
    container_path = "/data"
    read_only      = true
  }

  read_only     = true
  security_opts = ["no-new-privileges:true"]
  tmpfs = {
    "/tmp" = "rw,noexec,nosuid,size=16m"
  }

  capabilities {
    drop = ["ALL"]
  }

  healthcheck {
    test         = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]
    interval     = "30s"
    timeout      = "3s"
    start_period = "10s"
    retries      = 3
  }

  dynamic "labels" {
    for_each = local.labels
    content {
      label = labels.key
      value = labels.value
    }
  }
}
