
output "aws_ecs_cluster_name" {
  value = aws_ecs_cluster.ecs_cluster.name
}


output "aws_ecs_service_worker_name" {
  value = aws_ecs_service.worker.name
}
