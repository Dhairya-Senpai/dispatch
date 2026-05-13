variable "project" {
  description = "Project name used for resource naming"
  type        = string
  default     = "dispatch"
}

variable "environment" {
  description = "Deployment environment (dev, prod)"
  type        = string
}

variable "aws_region" {
  description = "Primary AWS region"
  type        = string
  default     = "us-east-1"
}

variable "replica_regions" {
  description = "Additional regions for DynamoDB Global Tables replication"
  type        = list(string)
  default     = []
}

variable "domain_name" {
  description = "Custom domain for the platform"
  type        = string
}

variable "gemini_api_key" {
  description = "Google Gemini API key"
  type        = string
  sensitive   = true
}
