output "test_namespace" {
  description = "Name of the test namespace"
  value       = var.enable_test_deployment ? kubernetes_namespace.test[0].metadata[0].name : ""
}

output "test_deployment_name" {
  description = "Name of the test deployment"
  value       = var.enable_test_deployment ? kubernetes_deployment.test_internet_app[0].metadata[0].name : ""
}

output "metrics_server_status" {
  description = "Status of the metrics server deployment"
  value       = var.enable_metrics_server ? helm_release.metrics_server[0].status : "disabled"
}

output "aws_load_balancer_controller_status" {
  description = "Status of the AWS Load Balancer Controller deployment"
  value       = var.enable_aws_load_balancer_controller ? helm_release.aws_load_balancer_controller[0].status : "disabled"
}