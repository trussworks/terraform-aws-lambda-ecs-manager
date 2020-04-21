# aws-lambda-ecs-manager

Creates a lambda for managing ECS services in Fargate.

Creates the following resources:

* CloudWatch log group for the lambda.
* IAM role for the lambda.

## Usage

```hcl

module "ecs_manager" {
  source = "../../../modules/aws-lambda-ecs-manager"

  name        = "${var.name}"
  environment = "${var.environment}"

  task_role_arn           = "${module.ecs_service_app.task_role_arn}"
  task_execution_role_arn = "${module.ecs_service_app.task_execution_role_arn}"
}
```

## Providers

| Name | Version |
|------|---------|
| archive | n/a |
| aws | n/a |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:-----:|
| environment | n/a | `string` | n/a | yes |
| logs\_retention | Number of days to retain lambda events. | `string` | `"365"` | no |
| name | n/a | `string` | n/a | yes |
| task\_execution\_role\_arn | ARN of the task execution role the Amazon ECS container agent and Docker daemon can assume. | `string` | n/a | yes |
| task\_role\_arn | ARN of the IAM role assumed by Amazon ECS container tasks. | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| iam\_role | Name of the IAM role the lambda assumes. |
| lambda\_function | ARN of the lambda function. |
| log\_group | CloudWatch log group the lambda logs to. |

## Development

Set up the environment:

```console
brew install poetry pre-commit
pre-commit install --install-hooks
poetry install
```

To test the function locally:

```console
$ jq < payload.json  # run a task without changing the entryPoint command in the task definition
{
  "command": "runtask",
  "body": null
}
$ ./run_local ./payload.json
```

To test the deployed Lambda:

```console
./invoke ./payload.json "function-name"
```
