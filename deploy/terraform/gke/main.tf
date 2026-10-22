# GKE cluster for sockRat: a private, VPC-native cluster with Dataplane V2 (so the chart's
# NetworkPolicies are enforced), Workload Identity, a least-privilege node service account,
# Cloud NAT for outbound traffic from private nodes, Artifact Registry for the images and a
# static IP for the ingress controller.

locals {
  services = [
    "artifactregistry.googleapis.com",
    "compute.googleapis.com",
    "container.googleapis.com",
  ]
  node_roles = [
    "roles/artifactregistry.reader",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/stackdriver.resourceMetadata.writer",
  ]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.services)
  service            = each.value
  disable_on_destroy = false
}

# ---- Network ----

resource "google_compute_network" "vpc" {
  name                    = "${var.name}-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "nodes" {
  name                     = "${var.name}-nodes"
  region                   = var.region
  network                  = google_compute_network.vpc.id
  ip_cidr_range            = var.subnet_cidr
  private_ip_google_access = true # reach Google APIs (Artifact Registry, logging) without public IPs

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.pods_cidr
  }
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.services_cidr
  }
}

# Private nodes have no public IPs; NAT lets them reach the LLM API, Google sign-in and image registries
resource "google_compute_router" "router" {
  name    = "${var.name}-router"
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "${var.name}-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# The ingress-nginx LoadBalancer Service uses this address, so DNS can point at it before the cluster exists
resource "google_compute_address" "ingress" {
  name       = "${var.name}-ingress"
  region     = var.region
  depends_on = [google_project_service.apis]
}

# ---- Images ----

resource "google_artifact_registry_repository" "images" {
  repository_id = var.name
  location      = var.region
  format        = "DOCKER"
  description   = "sockRat container images"

  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 20
    }
  }
  cleanup_policies {
    id     = "delete-old-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s" # 7 days
    }
  }

  depends_on = [google_project_service.apis]
}

# ---- Cluster ----

# Nodes run as their own service account with only the roles they need, not the
# default Compute Engine account (which has Editor on the whole project)
resource "google_service_account" "nodes" {
  account_id   = "${var.name}-nodes"
  display_name = "sockRat GKE nodes"
}

resource "google_project_iam_member" "nodes" {
  for_each = toset(local.node_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.nodes.email}"
}

resource "google_container_cluster" "main" {
  name     = var.name
  location = var.zone

  network    = google_compute_network.vpc.id
  subnetwork = google_compute_subnetwork.nodes.id

  # Node pools are managed separately below
  remove_default_node_pool = true
  initial_node_count       = 1

  release_channel {
    channel = "REGULAR"
  }

  networking_mode = "VPC_NATIVE"
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  # Dataplane V2 (eBPF/Cilium) enforces NetworkPolicy, including the sandbox's deny-all egress
  datapath_provider = "ADVANCED_DATAPATH"

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false # kubectl from outside still works, limited by the authorized networks below
    master_ipv4_cidr_block  = var.master_cidr
  }

  dynamic "master_authorized_networks_config" {
    for_each = length(var.master_authorized_cidrs) > 0 ? [1] : []
    content {
      dynamic "cidr_blocks" {
        for_each = var.master_authorized_cidrs
        content {
          cidr_block = cidr_blocks.value
        }
      }
    }
  }

  # Pods get Google credentials through Kubernetes service accounts, never node keys
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  addons_config {
    http_load_balancing {
      disabled = true # ingress-nginx serves traffic (streaming answers need proxy-buffering off)
    }
  }

  maintenance_policy {
    recurring_window {
      start_time = "2026-01-03T02:00:00Z"
      end_time   = "2026-01-03T06:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SA,SU"
    }
  }

  deletion_protection = true

  depends_on = [google_project_service.apis]
}

resource "google_container_node_pool" "default" {
  name     = "default"
  cluster  = google_container_cluster.main.id
  location = var.zone

  autoscaling {
    min_node_count = var.min_nodes
    max_node_count = var.max_nodes
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }

  node_config {
    machine_type    = var.machine_type
    disk_size_gb    = 50
    disk_type       = "pd-balanced"
    spot            = var.spot_nodes
    service_account = google_service_account.nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"] # access is limited by IAM roles

    workload_metadata_config {
      mode = "GKE_METADATA" # hide the node's credentials from pods
    }

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }

    labels = {
      app = var.name
    }
  }
}
