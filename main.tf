/**
 * Creates a lambda to run an ECS task.
 *
 * Creates the following resources:
 *
 * * CloudWatch log group for the lambda.
 * * IAM role for the lambda.
 *
 * ## Usage
 *
 * ```hcl
 *
 * module "lambda_runtask" {
 *   source = "../../../modules/aws-lambda-runtask"
 *
 *   app_name    = var.name
 *   environment = var.environment
 *
 *   task_role_arn           = module.ecs_service_app.task_role_arn
 *   task_execution_role_arn = module.ecs_service_app.task_execution_role_arn
 * }
 * ```
 */

locals {
  service_name   = "ecs-runtask-${var.app_name}-${var.environment}"
  log_group      = "/aws/lambda/${local.app_name}"
  taskdef_family = "${var.app_name}-lambda-${var.environment}"
}

#
# Lambda
#

data "archive_file" "main" {
  type        = "zip"
  source_file = "${substr("${path.module}/functions/runtask.py", length(path.cwd) + 1, -1)}"
  output_path = "${substr("${path.module}/functions/runtask.zip", length(path.cwd) + 1, -1)}"
}

resource "aws_lambda_function" "main" {
  filename      = data.archive_file.main.output_path
  function_name = var.app_name
  description   = "Updates an ECS service"

  role             = aws_iam_role.main.arn
  handler          = "deploy.lambda_handler"
  source_code_hash = data.archive_file.main.output_base64sha256
  runtime          = "python3.6"
  timeout          = 10

  environment {
    variables = {
      ECS_CLUSTER    = var.environment
      ECS_WEBSERVICE = var.app_name
      ENVIRONMENT    = var.environment
    }
  }

  tags = {
    Environment = var.environment
    Automation  = "Terraform"
  }

  lifecycle {
    # ignore local filesystem differences
    ignore_changes = [
      "filename",
      "last_modified",
    ]
  }
}
