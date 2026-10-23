output "network_name" {
  description = "Docker network the API is attached to."
  value       = docker_network.app.name
}

output "volume_name" {
  description = "Docker volume mounted at /data in the API container."
  value       = docker_volume.data.name
}

output "image" {
  description = "Locally built API image (name and ID)."
  value = {
    name = docker_image.api.name
    id   = docker_image.api.image_id
  }
}

output "container_name" {
  description = "Name of the running API container."
  value       = docker_container.api.name
}

output "api_url" {
  description = "Base URL of the API."
  value       = "http://127.0.0.1:${var.host_port}"
}

output "health_url" {
  description = "Liveness probe endpoint."
  value       = "http://127.0.0.1:${var.host_port}/healthz"
}

output "docs_url" {
  description = "Interactive API docs."
  value       = "http://127.0.0.1:${var.host_port}/docs"
}
