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

output "version" {
  description = "Published version of the lambda function."
  value       = aws_lambda_function.main.version
}

output "qualified_arn" {
  description = "The Amazon Resource Name (ARN) identifying your Lambda Function Version (if versioning is enabled via publish = true)."
  value       = aws_lambda_function.main.qualified_arn
}

output "name" {
  description = "Name of the lambda function."
  value       = var.app_name
}

output "last_modified" {
  description = "The date this resource was last modified."
  value       = aws_lambda_function.main.last_modified
}

output "source_code_hash" {
  description = "Base64-encoded representation of raw SHA-256 sum of the zip file."
  value       = aws_lambda_function.main.source_code_hash
}

output "source_code_size" {
  description = "The size in bytes of the function .zip file."
  value       = aws_lambda_function.main.source_code_size
}
