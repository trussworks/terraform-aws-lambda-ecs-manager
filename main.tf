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
  log_group      = "/aws/lambda/${var.app_name}"
  taskdef_family = "${var.app_name}-lambda-${var.environment}"
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
  description        = "Allows Lambda functions to update ${local.taskdef_family} service container definitions."
  name               = "lambda-${var.name}-${var.environment}"
  assume_role_policy = "${data.aws_iam_policy_document.lambda_assume_role.json}"
}

data "aws_arn" "task_arn" {
  arn = "${var.task_role_arn}"
}

data "aws_iam_policy_document" "main" {
  # allow writing cloudwatch logs
  statement {
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["${aws_cloudwatch_log_group.main.arn}"]
  }

  # allow the lambda to assume the task roles
  statement {
    actions = ["iam:PassRole"]

    resources = [
      "${var.task_role_arn}",
      "${var.task_execution_role_arn}",
    ]
  }

  # allow reading ECS service details and creating task definitions
  # NOTE: these don't support resource level permissions
  #   https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-supported-iam-actions-resources.html
  statement {
    actions = [
      "ecs:DescribeServices",
      "ecs:DescribeTaskDefinition",
      "ecs:RegisterTaskDefinition",
      "ecs:UpdateService",
    ]

    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "main" {
  name   = "lambda-ecs-deploy-${var.name}-${var.environment}-policy"
  role   = "${aws_iam_role.main.name}"
  policy = "${data.aws_iam_policy_document.main.json}"
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
  handler          = "runtask.lambda_handler"
  source_code_hash = data.archive_file.main.output_base64sha256
  runtime          = "python3.7"
  timeout          = 10

  environment {
    variables = {
      ECS_CLUSTER = var.environment
      ECS_SERVICE = var.app_name
      ENVIRONMENT = var.environment
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
