variable "app_name" {
  type        = string
  description = "Name of the application the Lambda is associated with."
}

variable "environment" {
  type        = string
  description = "Name of the environment the Lambda is deployed into."
}

variable "task_role_arns" {
  type        = list(string)
  description = "ARNs of the IAM roles assumed by Amazon ECS container tasks."
}

variable "task_execution_role_arns" {
  type        = list(string)
  description = "ARN of the task execution role the Amazon ECS container agent and Docker daemon can assume."
}

variable "logs_retention" {
  type        = string
  description = "Number of days to retain lambda events."
  default     = "365"
}

variable "publish" {
  type        = bool
  description = "Whether to publish creation/change as new Lambda Function Version."
  default     = false
}

variable "package_type" {
  type        = string
  description = "(Optional) The Lambda deployment package type. Valid values are `Zip` and `Image`. Defaults to `Zip`."
  default     = "Zip"
}

variable "image_uri" {
  type        = string
  description = "(Optional) The ECR image URI containing the function's deployment package."
  default     = ""
}
