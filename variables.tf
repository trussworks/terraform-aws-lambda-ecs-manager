variable "app_name" {
  type        = "string"
  description = "Name of the application the Lambda is associated with."
}

variable "environment" {
  type        = "string"
  description = "Name of the environment the Lambda is deployed into."
}

# variable "task_role_arn" {
#   type        = "string"
#   description = "ARN of the IAM role assumed by Amazon ECS container tasks."
# }
#
# variable "task_execution_role_arn" {
#   type        = "string"
#   description = "ARN of the task execution role the Amazon ECS container agent and Docker daemon can assume."
# }

variable "logs_retention" {
  type        = "string"
  description = "Number of days to retain lambda events."
  default     = "365"
}
