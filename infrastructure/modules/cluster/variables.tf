
variable "project" {
  description = "The project name"
  type        = string
}

variable "environment" {
  description = "The environment (e.g., staging, production)"
  type        = string
}

variable "existing_vpc_id" {
  description = "The VPC Id"
  type        = string
}

variable "aws_region" {
  description = "The AWS region"
  type        = string
}

variable "security_groups" {
  description = "security group id for the rds database"
  type        = list(any)
}

variable "lb_target_group_arn" {
  description = "load balancer target group arn"
  type        = string
}

variable "image" {
  description = "Name of ecr image for project"
  type        = string
}

variable "public_subnets_ids" {
  description = "A list of public subnets inside the VPC"
  type        = list(string)
}

variable "secrets" {
  description = "List of env secrets for environment"
  type        = list(any)
}

variable "secrets_arn" {
  description = "Images secrets credentials secret manager arn"
  type        = string
}

variable "containerPort" {
  description = "container port for ECS port Mapping"
  type        = number
}

variable "hostPort" {
  description = "container port for ECS port Mapping"
  type        = number
}

variable "container_port" {
  description = "container port for load balancer"
  type        = number
}

variable "cpu" {
  description = "Fargate task CPU units (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Fargate task memory in MB"
  type        = number
  default     = 512
}
