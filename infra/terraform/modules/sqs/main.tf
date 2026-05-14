variable "queue_name" {
  type = string
}

variable "visibility_timeout" {
  type    = number
  default = 300
}

variable "max_receive_count" {
  type    = number
  default = 3
}

variable "environment" {
  type = string
}

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.queue_name}-dlq-${var.environment}"
  message_retention_seconds = 1209600

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_sqs_queue" "main" {
  name                       = "${var.queue_name}-${var.environment}"
  visibility_timeout_seconds = var.visibility_timeout
  message_retention_seconds  = 86400

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

output "queue_url" { value = aws_sqs_queue.main.url }
output "queue_arn" { value = aws_sqs_queue.main.arn }
output "dlq_url"   { value = aws_sqs_queue.dlq.url }
output "dlq_arn"   { value = aws_sqs_queue.dlq.arn }
