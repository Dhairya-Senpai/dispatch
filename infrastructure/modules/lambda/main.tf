variable "function_name" { type = string }
variable "handler"        { type = string }
variable "runtime"        { type = string }
variable "source_dir"     { type = string }
variable "environment"    { type = map(string) }
variable "layers"         { type = list(string); default = [] }
variable "timeout"        { type = number; default = 30 }
variable "memory_size"    { type = number; default = 256 }
variable "policy_arns"    { type = list(string); default = [] }

data "archive_file" "zip" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/../../.build/${var.function_name}.zip"
}

resource "aws_iam_role" "lambda" {
  name = "${var.function_name}-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "extra" {
  for_each   = toset(var.policy_arns)
  role       = aws_iam_role.lambda.name
  policy_arn = each.value
}

resource "aws_lambda_function" "this" {
  function_name    = var.function_name
  role             = aws_iam_role.lambda.arn
  handler          = var.handler
  runtime          = var.runtime
  filename         = data.archive_file.zip.output_path
  source_code_hash = data.archive_file.zip.output_base64sha256
  timeout          = var.timeout
  memory_size      = var.memory_size
  layers           = var.layers

  environment {
    variables = var.environment
  }
}

output "function_arn"  { value = aws_lambda_function.this.arn }
output "function_name" { value = aws_lambda_function.this.function_name }
