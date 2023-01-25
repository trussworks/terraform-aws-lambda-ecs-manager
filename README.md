# DEPRECIATION NOTICE
 
This module has been deprecated and is no longer maintained. Should you need to continue to use it, please fork the repository. Thank you.
 
 # terraform-aws-lambda-ecs-manager

## Terraform Versions

Terraform 0.13. Pin module version to `~> 2.X`. Submit pull-requests to `master` branch.

Terraform 0.12. Pin module version to `~> 1.X`. Submit pull-requests to `terraform012` branch.

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
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

## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 0.13.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | >= 3.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_archive"></a> [archive](#provider\_archive) | n/a |
| <a name="provider_aws"></a> [aws](#provider\_aws) | >= 3.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_cloudwatch_log_group.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group) | resource |
| [aws_iam_role.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_lambda_function.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function) | resource |
| [archive_file.main](https://registry.terraform.io/providers/hashicorp/archive/latest/docs/data-sources/file) | data source |
| [aws_iam_policy_document.lambda_assume_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | Name of the application the Lambda is associated with. | `string` | n/a | yes |
| <a name="input_environment"></a> [environment](#input\_environment) | Name of the environment the Lambda is deployed into. | `string` | n/a | yes |
| <a name="input_image_uri"></a> [image\_uri](#input\_image\_uri) | (Optional) The ECR image URI containing the function's deployment package. | `string` | `null` | no |
| <a name="input_logs_retention"></a> [logs\_retention](#input\_logs\_retention) | Number of days to retain lambda events. | `string` | `"365"` | no |
| <a name="input_package_type"></a> [package\_type](#input\_package\_type) | (Optional) The Lambda deployment package type. Valid values are `Zip` and `Image`. | `string` | `"Zip"` | no |
| <a name="input_publish"></a> [publish](#input\_publish) | Whether to publish creation/change as new Lambda Function Version. | `bool` | `false` | no |
| <a name="input_task_execution_role_arns"></a> [task\_execution\_role\_arns](#input\_task\_execution\_role\_arns) | ARN of the task execution role the Amazon ECS container agent and Docker daemon can assume. | `list(string)` | n/a | yes |
| <a name="input_task_role_arns"></a> [task\_role\_arns](#input\_task\_role\_arns) | ARNs of the IAM roles assumed by Amazon ECS container tasks. | `list(string)` | n/a | yes |
| <a name="input_timeout"></a> [timeout](#input\_timeout) | How long a lambda call can execute before it is timed out, in seconds. | `number` | `120` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_iam_role_name"></a> [iam\_role\_name](#output\_iam\_role\_name) | Name of the IAM role the lambda assumes. |
| <a name="output_lambda_function_arn"></a> [lambda\_function\_arn](#output\_lambda\_function\_arn) | ARN of the lambda function. |
| <a name="output_last_modified"></a> [last\_modified](#output\_last\_modified) | The date this resource was last modified. |
| <a name="output_log_group"></a> [log\_group](#output\_log\_group) | CloudWatch log group the lambda logs to. |
| <a name="output_name"></a> [name](#output\_name) | Name of the lambda function. |
| <a name="output_qualified_arn"></a> [qualified\_arn](#output\_qualified\_arn) | The Amazon Resource Name (ARN) identifying your Lambda Function Version (if versioning is enabled via publish = true). |
| <a name="output_source_code_hash"></a> [source\_code\_hash](#output\_source\_code\_hash) | Base64-encoded representation of raw SHA-256 sum of the zip file. |
| <a name="output_source_code_size"></a> [source\_code\_size](#output\_source\_code\_size) | The size in bytes of the function .zip file. |
| <a name="output_version"></a> [version](#output\_version) | Published version of the lambda function. |
<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->

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

To find if any containers are unhealthy, exited non-zero, or reported any
failures, this `jq` query can help:

```console
jq '.data.response.message.tasks |
    any(
        (.failures | length > 0)
        or (
            .containers | any(.exitCode > 0 or .healthStatus == "UNHEALTHY")
        )
    )' < output.json
```

It will print a boolean indicating if errors were found: `false` means the
queried services' statuses are OK, while `true` means at least one problem was
found.

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

#### SSM Parameters

ecs-manager can add (or remove) secrets in an ECS task definition. Using the
`secrets` key, pass in a list of regular expressions:

```json
{
    "command": "deploy",
    "body": {
        "cluster_id": "app-cluster",
        "service_ids": ["app-service1"],
        "secrets": ["^/app-service1/secrets/\\S+$"]
    }
}
```

For each of the SSM Parameters with names that match any regular expression in the list,
the `ENV_VAR_NAME` object tag will be read. If it is found, the Parameter's value
will be added to the container definitions. For example, a Parameter with this tag:

```console
$ aws ssm list-tags-for-resource --resource-type "Parameter" --resource-id 'secrets/test'
{
    "TagList": [
        {
            "Key": "ENV_VAR_NAME",
            "Value": "TEST"
        }
    ]
}
```

Will appear in the task definition like so:

```json
"secrets": [
    {
        "name": "TEST",
        "valueFrom": "secrets/test"
    }
]
```

For more information, see [Tagging SSM documents], and the [Amazon ECS Developer
Guide] on _Specifying Sensitive Data Using Systems Manager Parameter Store_.

[tagging ssm documents]: https://docs.aws.amazon.com/systems-manager/latest/userguide/tagging-documents.html
[amazon ecs developer guide]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data-parameters.html

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
