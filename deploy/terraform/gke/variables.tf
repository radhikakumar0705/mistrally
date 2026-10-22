variable "project_id" {
  description = "Google Cloud project to create everything in"
  type        = string
}

variable "region" {
  description = "Region for the network, registry and ingress address"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zone of the cluster. A zonal cluster keeps the demo to one set of nodes; use the region for a highly available control plane and nodes in every zone"
  type        = string
  default     = "us-central1-a"
}

variable "name" {
  description = "Prefix for resource names"
  type        = string
  default     = "mistrally"
}

variable "machine_type" {
  description = "Node machine type. The API embeds and re-ranks on CPU, so 4 vCPUs is a comfortable minimum"
  type        = string
  default     = "e2-standard-4"
}

variable "min_nodes" {
  description = "Smallest node count the autoscaler may shrink to"
  type        = number
  default     = 1
}

variable "max_nodes" {
  description = "Largest node count the autoscaler may grow to"
  type        = number
  default     = 3
}

variable "spot_nodes" {
  description = "Use Spot VMs (60-90% cheaper, may be reclaimed at any time)"
  type        = bool
  default     = false
}

variable "master_authorized_cidrs" {
  description = "CIDR blocks allowed to reach the Kubernetes API, e.g. your office or home IP as x.x.x.x/32. Empty allows any address (authentication is still required)"
  type        = list(string)
  default     = []
}

variable "subnet_cidr" {
  description = "Primary range of the subnet (nodes)"
  type        = string
  default     = "10.10.0.0/20"
}

variable "pods_cidr" {
  description = "Secondary range for pod IPs"
  type        = string
  default     = "10.20.0.0/16"
}

variable "services_cidr" {
  description = "Secondary range for Service IPs"
  type        = string
  default     = "10.30.0.0/20"
}

variable "master_cidr" {
  description = "/28 range for the private control-plane endpoint"
  type        = string
  default     = "172.16.0.0/28"
}
