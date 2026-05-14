# Terraform root module — design_doc §7.2
# Orchestrates 9 submodules:
#   sqs_llm, sqs_pdf       — task queues + DLQs
#   lambda_llm, lambda_pdf — async workers triggered by SQS
#   lambda_dlq             — DLQ handler → job_errors + SNS alert
#   rds                    — PostgreSQL multi-AZ
#   s3                     — PDF storage
#   api_gateway            — REST API + JWT Authorizer + rate limiting
#   sns                    — DLQ alert topic (email / Slack)

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  common_env_vars = {
    DJANGO_SETTINGS_MODULE = "config.settings.production"
    DB_HOST                = module.rds.endpoint
    DB_NAME                = "diagnosis_db"
    AWS_DEFAULT_REGION     = var.aws_region
    AWS_S3_BUCKET_NAME     = module.s3.bucket_name
    SQS_LLM_QUEUE_URL      = module.sqs_llm.queue_url
    SQS_PDF_QUEUE_URL      = module.sqs_pdf.queue_url
    SNS_ALERT_TOPIC_ARN    = module.sns.topic_arn
    LLM_PROVIDER           = "claude"
  }
}

# ── SQS: LLM task queue ───────────────────────────────────────────────────────
module "sqs_llm" {
  source              = "./modules/sqs"
  queue_name          = "${var.project_name}-llm"
  visibility_timeout  = 300
  max_receive_count   = 3
  environment         = var.environment
}

# ── SQS: PDF task queue ───────────────────────────────────────────────────────
module "sqs_pdf" {
  source              = "./modules/sqs"
  queue_name          = "${var.project_name}-pdf"
  visibility_timeout  = 300
  max_receive_count   = 3
  environment         = var.environment
}

# ── Lambda: LLM worker ────────────────────────────────────────────────────────
module "lambda_llm" {
  source           = "./modules/lambda"
  function_name    = "${var.project_name}-llm-worker"
  handler          = "tasks.llm_worker.handler"
  s3_bucket        = var.lambda_s3_bucket
  s3_key           = var.lambda_package_key
  timeout          = 300
  memory_size      = 512
  sqs_trigger_arn  = module.sqs_llm.queue_arn
  environment_vars = local.common_env_vars
  environment      = var.environment
}

# ── Lambda: PDF worker ────────────────────────────────────────────────────────
module "lambda_pdf" {
  source           = "./modules/lambda"
  function_name    = "${var.project_name}-pdf-worker"
  handler          = "tasks.pdf_worker.handler"
  s3_bucket        = var.lambda_s3_bucket
  s3_key           = var.lambda_package_key
  timeout          = 300
  memory_size      = 1024   # WeasyPrint needs more memory
  sqs_trigger_arn  = module.sqs_pdf.queue_arn
  environment_vars = local.common_env_vars
  environment      = var.environment
}

# ── Lambda: DLQ handler (implementation_plan.md problem-4 fix) ───────────────
module "lambda_dlq" {
  source           = "./modules/lambda"
  function_name    = "${var.project_name}-dlq-handler"
  handler          = "tasks.dlq_handler.handler"
  s3_bucket        = var.lambda_s3_bucket
  s3_key           = var.lambda_package_key
  timeout          = 60
  memory_size      = 256
  # DLQ handler triggers from both DLQs; we use the LLM DLQ as primary trigger.
  # A second event_source_mapping for pdf DLQ is added via aws_lambda_event_source_mapping below.
  sqs_trigger_arn  = module.sqs_llm.dlq_arn
  environment_vars = merge(local.common_env_vars, {
    SNS_ALERT_TOPIC_ARN = module.sns.topic_arn
  })
  environment      = var.environment
}

# Second DLQ trigger: PDF DLQ → dlq_handler Lambda
resource "aws_lambda_event_source_mapping" "pdf_dlq_to_dlq_handler" {
  event_source_arn = module.sqs_pdf.dlq_arn
  function_name    = module.lambda_dlq.function_arn
  batch_size       = 1
  enabled          = true
}

# ── RDS: PostgreSQL ───────────────────────────────────────────────────────────
module "rds" {
  source             = "./modules/rds"
  identifier         = var.project_name
  instance_class     = var.rds_instance_class
  vpc_id             = var.vpc_id
  subnet_ids         = var.private_subnet_ids
  environment        = var.environment
}

# ── S3: PDF storage ───────────────────────────────────────────────────────────
module "s3" {
  source       = "./modules/s3"
  bucket_name  = "${var.project_name}-pdfs"
  environment  = var.environment
}

# ── API Gateway ───────────────────────────────────────────────────────────────
module "api_gateway" {
  source             = "./modules/api_gateway"
  api_name           = var.project_name
  lambda_invoke_arn  = module.lambda_llm.function_arn
  lambda_arn         = module.lambda_llm.function_arn
  jwt_issuer         = var.jwt_issuer
  jwt_audience       = var.jwt_audience
  throttle_rate      = 100
  throttle_burst     = 200
  environment        = var.environment
}

# ── SNS: DLQ alert topic ──────────────────────────────────────────────────────
module "sns" {
  source       = "./modules/sns"
  topic_name   = "${var.project_name}-dlq-alerts"
  alert_email  = var.alert_email
  environment  = var.environment
}
