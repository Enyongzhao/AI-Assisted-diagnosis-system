# Terraform outputs — key resource identifiers after apply.
# design_doc §7.2

output "api_gateway_url" {
  description = "API Gateway invoke URL (base URL for all /api/v1/* endpoints)"
  value       = module.api_gateway.invoke_url
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (host:port)"
  value       = module.rds.endpoint
  sensitive   = true
}

output "rds_secret_arn" {
  description = "Secrets Manager ARN for the RDS password"
  value       = module.rds.secret_arn
}

output "pdf_bucket_name" {
  description = "S3 bucket name for PDF storage"
  value       = module.s3.bucket_name
}

output "llm_queue_url" {
  description = "SQS URL for LLM task queue"
  value       = module.sqs_llm.queue_url
}

output "pdf_queue_url" {
  description = "SQS URL for PDF task queue"
  value       = module.sqs_pdf.queue_url
}

output "sns_alert_topic_arn" {
  description = "SNS topic ARN for DLQ alerts"
  value       = module.sns.topic_arn
}

output "lambda_llm_arn" {
  description = "ARN of the LLM worker Lambda"
  value       = module.lambda_llm.function_arn
}

output "lambda_pdf_arn" {
  description = "ARN of the PDF worker Lambda"
  value       = module.lambda_pdf.function_arn
}

output "lambda_dlq_arn" {
  description = "ARN of the DLQ handler Lambda"
  value       = module.lambda_dlq.function_arn
}
