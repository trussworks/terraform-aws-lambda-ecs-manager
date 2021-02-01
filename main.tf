/**
 * Creates a Lambda to manage ECS services in Fargate.
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
 * module "lambda_ecs_manager" {
 *   source = "../../../modules/aws-lambda-ecs-manager"
 *
 *   app_name    = var.app_name
 *   environment = var.environment
 *
 *   task_role_arns           = [module.ecs_service_app.task_role_arn]
 *   task_execution_role_arns = [module.ecs_service_app.task_execution_role_arn]
 * }
 * ```
 */

locals {
  log_group = "/aws/lambda/${var.app_name}"
}

#
# CloudWatch
#

resource "aws_cloudwatch_log_group" "main" {
  name              = local.log_group
  retention_in_days = var.logs_retention

  tags = {
    Name        = var.app_name
    Environment = var.environment
    Automation  = "Terraform"
  }
}

#
# IAM
#

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "main" {
  description        = "Allows Lambda functions to update ECS services."
  name               = "lambda-${var.app_name}-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "main" {
  # allow writing cloudwatch logs
  statement {
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["${aws_cloudwatch_log_group.main.arn}:*"]
  }

  # allow the lambda to assume the task roles
  statement {
    actions = ["iam:PassRole"]

    resources = concat(var.task_role_arns, var.task_execution_role_arns)
  }

  # allow reading ECS service details and creating task definitions
  # NOTE: these don't support resource level permissions
  #   https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-supported-iam-actions-resources.html
  statement {
    actions = [
      "ecs:DescribeServices",
      "ecs:DescribeTaskDefinition",
      "ecs:DescribeTasks",
      "ecs:RegisterTaskDefinition",
      "ecs:RunTask",
      "ecs:UpdateService",
      "ssm:DescribeParameters",
      "ssm:GetParameters",
      "ssm:ListTagsForResource",
    ]

    resources = ["*"]
  }

}

resource "aws_iam_role_policy" "main" {
  name   = "lambda-ecs-manager-${var.app_name}-${var.environment}-policy"
  role   = aws_iam_role.main.name
  policy = data.aws_iam_policy_document.main.json
}

#
# Lambda
#

data "archive_file" "main" {
  type        = "zip"
  output_path = "${path.module}/functions/manager.zip"

  source {
    content  = file("${path.module}/functions/manager.py")
    filename = "manager.py"
  }
}

resource "aws_lambda_function" "main" {
  filename      = data.archive_file.main.output_path
  function_name = var.app_name
  description   = "Updates an ECS service"

  role             = aws_iam_role.main.arn
  handler          = "manager.lambda_handler"
  source_code_hash = data.archive_file.main.output_base64sha256
  runtime          = "python3.7"
  timeout          = 120
  publish          = var.publish
  package_type     = var.package_type

  tags = {
    Environment = var.environment
    Automation  = "Terraform"
  }

  lifecycle {
    # ignore local filesystem differences
    ignore_changes = [
      filename,
      last_modified,
    ]
  }
}
