variable "topic_name" {
  type = string
}

variable "alert_email" {
  type    = string
  default = ""
}

variable "environment" {
  type = string
}

resource "aws_sns_topic" "this" {
  name = "${var.topic_name}-${var.environment}"

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.this.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

output "topic_arn"  { value = aws_sns_topic.this.arn }
output "topic_name" { value = aws_sns_topic.this.name }
