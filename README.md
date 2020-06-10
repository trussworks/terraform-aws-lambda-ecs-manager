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

## Invoking the lambda

You can invoke the deployed ecs-manager lambda using aws-cli and the
`environment` input you used when importing the module:

```console
aws lambda invoke --function-name "<environment>-ecs-manager" --payload payload.json output.json
```

### Get a status report on tasks

ecs-manager can produce a report on the status of running and stopped tasks
from a given service and/or task definition family:

```json
{
    "command": "healthcheck",
    "body": {
        "cluster_id": "app-cluster",
        "service_name": "app-service1"
}
```

To find if any containers are unhealthy, exited non-zero, or reported any failures, this `jq` query can help:

```console
jq '.data.response.message.tasks |
    any(
        (.failures | length > 0)
        or (
            .containers | any(.exitCode > 0 or .healthStatus == "UNHEALTHY")
        )
    )' < output.json
```

### Deploy an image

To deploy a new image into each of the containers in a list of services:

```json
{
    "command": "deploy",
    "body": {
        "cluster_id": "app-cluster",
        "service_ids": ["app-service1", "app-service2"],
        "image": "repo.url/app-service:test"
    }
}
```

This will find the services "app-service1" and "app-service2" in "app-cluster",
registering new task definitions for each service with _all_ the images in each
container definition set to `repo.url/app-service:test`. It then restarts the
services.

If the "image" key is omitted, services will be restarted in-place without any changes
to the task definition:

```json
{
    "command": "deploy",
    "body": {
        "cluster_id": "app-cluster",
        "service_ids": ["app-service1", "app-service2"]
    }
}
```

## Development

Set up the environment:

```console
brew install poetry pre-commit
pre-commit install --install-hooks
poetry install && poetry shell
```

To test the function locally:

```console
$ jq < payload.json  # run a task without changing the entryPoint in the task definition
{
  "command": "runtask",
  "body": { "entrypoint": null }
}
$ ./run_local ./payload.json
```

To test the deployed Lambda:

```console
./invoke ./payload.json "function-name"
```
