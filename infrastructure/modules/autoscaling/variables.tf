
variable "aws_ecs_cluster_name" {
  description = "The ecs cluster name"
  type        = string
}
variable "aws_ecs_service_worker_name" {
  description = "The ecs service worker name"
  type        = string
}
variable "project" {
  description = "The project name"
  type        = string
}

variable "aws_region" {
  description = "The AWS region"
  type        = string
}

variable "environment" {
  description = "The environment (e.g., staging, production)"
  type        = string
}
