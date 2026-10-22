terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Keep state in a versioned GCS bucket so it is shared and locked:
  # backend "gcs" {
  #   bucket = "my-project-tfstate"
  #   prefix = "mistrally/gke"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
