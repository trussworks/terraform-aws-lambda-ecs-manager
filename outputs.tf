output "lambda_function_arn" {
  description = "ARN of the lambda function."
  value       = aws_lambda_function.main.arn
}

output "iam_role_name" {
  description = "Name of the IAM role the lambda assumes."
  value       = aws_iam_role.main.name
}

output "log_group" {
  description = "CloudWatch log group the lambda logs to."
  value       = local.log_group
}
