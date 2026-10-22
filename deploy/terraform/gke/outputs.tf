output "cluster_name" {
  value = google_container_cluster.main.name
}

output "get_credentials" {
  description = "Configure kubectl for the cluster"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.main.name} --zone ${var.zone} --project ${var.project_id}"
}

output "image_registry" {
  description = "Set as images.registry in the Helm values"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "ingress_ip" {
  description = "Point your domain's A record here, and give it to ingress-nginx as its load balancer IP"
  value       = google_compute_address.ingress.address
}
