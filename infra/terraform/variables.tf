# Terraform input variables — design_doc §7.2
# Override defaults via terraform.tfvars or -var flags.

variable "aws_region" {
  type        = string
  description = "AWS region for all resources"
  default     = "us-east-1"
}

variable "environment" {
  type        = string
  description = "Deployment environment: staging | production"
  default     = "staging"
}

variable "project_name" {
  type        = string
  description = "Prefix for all resource names"
  default     = "ai-diagnosis"
}

# ── Lambda deployment package ─────────────────────────────────────────────────
variable "lambda_s3_bucket" {
  type        = string
  description = "S3 bucket containing Lambda deployment zip packages"
}

variable "lambda_package_key" {
  type        = string
  description = "S3 key for the main Lambda deployment package (.zip)"
  default     = "lambda/app.zip"
}

# ── RDS ───────────────────────────────────────────────────────────────────────
variable "rds_instance_class" {
  type    = string
  default = "db.t3.medium"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for RDS and Lambda networking"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for RDS placement"
}

# ── API Gateway ───────────────────────────────────────────────────────────────
variable "jwt_issuer" {
  type        = string
  description = "JWT token issuer URL (Cognito user pool or custom)"
  default     = ""
}

variable "jwt_audience" {
  type        = list(string)
  description = "Expected JWT audience values"
  default     = []
}

# ── SNS alerts ────────────────────────────────────────────────────────────────
variable "alert_email" {
  type        = string
  description = "Email address for DLQ alert notifications (leave blank to skip)"
  default     = ""
}
