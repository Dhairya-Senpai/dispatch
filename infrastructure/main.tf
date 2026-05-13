terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # Configure in environments/dev/backend.tfvars
    # bucket = "dispatch-terraform-state"
    # key    = "dev/terraform.tfstate"
    # region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "dispatch"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ── DynamoDB Tables ───────────────────────────────────────────────────────────

resource "aws_dynamodb_table" "campaigns" {
  name         = "${var.project}-campaigns"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "campaignId"

  attribute {
    name = "campaignId"
    type = "S"
  }

  point_in_time_recovery { enabled = true }
  deletion_protection_enabled = var.environment == "prod"

  dynamic "replica" {
    for_each = var.replica_regions
    content {
      region_name = replica.value
    }
  }
}

resource "aws_dynamodb_table" "contacts" {
  name         = "${var.project}-contacts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "contactId"

  attribute {
    name = "contactId"
    type = "S"
  }

  attribute {
    name = "listId"
    type = "S"
  }

  global_secondary_index {
    name            = "listId-index"
    hash_key        = "listId"
    projection_type = "ALL"
  }

  point_in_time_recovery { enabled = true }
}

resource "aws_dynamodb_table" "jobs" {
  name         = "${var.project}-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "jobId"

  attribute {
    name = "jobId"
    type = "S"
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "events" {
  name         = "${var.project}-events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }
}

# ── SQS Queue (FIFO for ordering) ─────────────────────────────────────────────

resource "aws_sqs_queue" "email_queue_dlq" {
  name                      = "${var.project}-email-dlq.fifo"
  fifo_queue                = true
  message_retention_seconds = 1209600 # 14 days
}

resource "aws_sqs_queue" "email_queue" {
  name                       = "${var.project}-email-queue.fifo"
  fifo_queue                 = true
  content_based_deduplication = true
  visibility_timeout_seconds  = 300
  message_retention_seconds   = 86400

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.email_queue_dlq.arn
    maxReceiveCount     = 3
  })
}

# ── Lambda Layer (shared utils) ───────────────────────────────────────────────

resource "aws_lambda_layer_version" "common" {
  filename            = "${path.module}/../../backend/layers/common.zip"
  layer_name          = "${var.project}-common"
  compatible_runtimes = ["python3.12"]

  lifecycle {
    create_before_destroy = true
  }
}

# ── Lambda Functions ──────────────────────────────────────────────────────────

locals {
  lambda_env = {
    CAMPAIGNS_TABLE   = aws_dynamodb_table.campaigns.name
    CONTACTS_TABLE    = aws_dynamodb_table.contacts.name
    JOBS_TABLE        = aws_dynamodb_table.jobs.name
    EVENTS_TABLE      = aws_dynamodb_table.events.name
    EMAIL_QUEUE_URL   = aws_sqs_queue.email_queue.url
    TRACKING_BASE_URL = "https://${var.domain_name}"
    AWS_REGION        = var.aws_region
  }
}

module "lambda_send_email" {
  source        = "./modules/lambda"
  function_name = "${var.project}-send-email"
  handler       = "handler.handler"
  runtime       = "python3.12"
  source_dir    = "../../backend/lambdas/send_email"
  environment   = local.lambda_env
  layers        = [aws_lambda_layer_version.common.arn]
  timeout       = 30
  memory_size   = 256

  policy_arns = [
    aws_iam_policy.dynamodb_read_write.arn,
    aws_iam_policy.sqs_send.arn,
  ]
}

module "lambda_process_queue" {
  source        = "./modules/lambda"
  function_name = "${var.project}-process-queue"
  handler       = "handler.handler"
  runtime       = "python3.12"
  source_dir    = "../../backend/lambdas/process_queue"
  environment   = local.lambda_env
  layers        = [aws_lambda_layer_version.common.arn]
  timeout       = 300
  memory_size   = 512

  policy_arns = [
    aws_iam_policy.dynamodb_read_write.arn,
    aws_iam_policy.ses_send.arn,
    aws_iam_policy.sqs_consume.arn,
  ]
}

module "lambda_track_event" {
  source        = "./modules/lambda"
  function_name = "${var.project}-track-event"
  handler       = "handler.handler"
  runtime       = "python3.12"
  source_dir    = "../../backend/lambdas/track_event"
  environment   = local.lambda_env
  layers        = [aws_lambda_layer_version.common.arn]
  timeout       = 10
  memory_size   = 128

  policy_arns = [aws_iam_policy.dynamodb_read_write.arn]
}

module "lambda_campaign_ai" {
  source        = "./modules/lambda"
  function_name = "${var.project}-campaign-ai"
  handler       = "handler.handler"
  runtime       = "python3.12"
  source_dir    = "../../backend/lambdas/campaign_ai"
  environment   = merge(local.lambda_env, {
    GEMINI_API_KEY = var.gemini_api_key
  })
  layers      = [aws_lambda_layer_version.common.arn]
  timeout     = 30
  memory_size = 256

  policy_arns = [aws_iam_policy.dynamodb_read_write.arn]
}

# ── SQS → Lambda trigger ──────────────────────────────────────────────────────

resource "aws_lambda_event_source_mapping" "sqs_to_process_queue" {
  event_source_arn                   = aws_sqs_queue.email_queue.arn
  function_name                      = module.lambda_process_queue.function_arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 5

  function_response_types = ["ReportBatchItemFailures"]
}

# ── API Gateway ───────────────────────────────────────────────────────────────

resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["https://${var.domain_name}"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization", "x-api-key"]
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}

# Route definitions
locals {
  routes = {
    "POST /campaigns/{campaignId}/send" = module.lambda_send_email.function_arn
    "GET /track/open"                   = module.lambda_track_event.function_arn
    "GET /track/click"                  = module.lambda_track_event.function_arn
    "POST /track/bounce"                = module.lambda_track_event.function_arn
    "POST /campaigns/generate"          = module.lambda_campaign_ai.function_arn
  }
}

resource "aws_apigatewayv2_integration" "lambdas" {
  for_each = local.routes

  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = each.value
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "routes" {
  for_each = local.routes

  api_id    = aws_apigatewayv2_api.main.id
  route_key = each.key
  target    = "integrations/${aws_apigatewayv2_integration.lambdas[each.key].id}"
}

# ── IAM Policies ──────────────────────────────────────────────────────────────

resource "aws_iam_policy" "dynamodb_read_write" {
  name = "${var.project}-dynamodb-rw"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
        "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan",
      ]
      Resource = [
        aws_dynamodb_table.campaigns.arn,
        aws_dynamodb_table.contacts.arn,
        aws_dynamodb_table.jobs.arn,
        aws_dynamodb_table.events.arn,
        "${aws_dynamodb_table.contacts.arn}/index/*",
      ]
    }]
  })
}

resource "aws_iam_policy" "sqs_send" {
  name = "${var.project}-sqs-send"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sqs:SendMessage"]
      Resource = aws_sqs_queue.email_queue.arn
    }]
  })
}

resource "aws_iam_policy" "sqs_consume" {
  name = "${var.project}-sqs-consume"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
      Resource = aws_sqs_queue.email_queue.arn
    }]
  })
}

resource "aws_iam_policy" "ses_send" {
  name = "${var.project}-ses-send"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ses:SendEmail", "ses:SendRawEmail"]
      Resource = "*"
    }]
  })
}
