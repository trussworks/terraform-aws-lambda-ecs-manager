# terraform-aws-lambda-ecs-manager

Creates a Lambda to manage ECS services in Fargate.

Creates the following resources:

* CloudWatch log group for the lambda.
* IAM role for the lambda.

## Usage

```hcl

module "lambda_ecs_manager" {
  source = "../../../modules/aws-lambda-ecs-manager"

  app_name    = var.app_name
  environment = var.environment

  task_role_arns           = [module.ecs_service_app.task_role_arn]
  task_execution_role_arns = [module.ecs_service_app.task_execution_role_arn]
}
```

## Terraform Versions

Terraform 0.13. Pin module version to `~> 2.X`. Submit pull-requests to `master` branch.

Terraform 0.12. Pin module version to `~> 1.X`. Submit pull-requests to `terraform012` branch.

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->

## Requirements

| Name | Version |
|------|---------|
| terraform | ~> 0.13.0 |
| aws | ~> 3.0 |

## Providers

| Name | Version |
|------|---------|
| archive | n/a |
| aws | ~> 3.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| app\_name | Name of the application the Lambda is associated with. | `string` | n/a | yes |
| environment | Name of the environment the Lambda is deployed into. | `string` | n/a | yes |
| logs\_retention | Number of days to retain lambda events. | `string` | `"365"` | no |
| publish | Whether to publish creation/change as new Lambda Function Version. | `bool` | `false` | no |
| task\_execution\_role\_arns | ARN of the task execution role the Amazon ECS container agent and Docker daemon can assume. | `list(string)` | n/a | yes |
| task\_role\_arns | ARNs of the IAM roles assumed by Amazon ECS container tasks. | `list(string)` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| iam\_role\_name | Name of the IAM role the lambda assumes. |
| lambda\_function\_arn | ARN of the lambda function. |
| last\_modified | The date this resource was last modified. |
| log\_group | CloudWatch log group the lambda logs to. |
| name | Name of the lambda function. |
| qualified\_arn | The Amazon Resource Name (ARN) identifying your Lambda Function Version (if versioning is enabled via publish = true). |
| source\_code\_hash | Base64-encoded representation of raw SHA-256 sum of the zip file. |
| source\_code\_size | The size in bytes of the function .zip file. |
| version | Published version of the lambda function. |

<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
