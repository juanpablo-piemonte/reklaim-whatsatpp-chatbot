variable "project" {
  description = "The project name"
  type        = string
}

variable "aws_region" {
  description = "The AWS region"
  type        = string
}

variable "environment" {
  description = "The environment (e.g., qa, production)"
  type        = string
}

variable "availability_zones" {
  description = "A list of availability zones"
  type        = list(string)
  default     = ["us-west-1b", "us-west-1c"]
}

variable "public_subnets" {
  description = "A list of public subnet CIDR blocks"
  type        = list(string)
  default     = []
}

variable "private_subnets" {
  description = "A list of private subnet CIDR blocks"
  type        = list(string)
  default     = []
}

variable "cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "172.31.0.0/16"
}

variable "public_subnets_ids" {
  description = "A list of public subnet IDs"
  type        = list(string)
}

variable "private_subnets_ids" {
  description = "A list of private subnet IDs"
  type        = list(string)
}

variable "existing_vpc_id" {
  description = "The existing VPC ID"
  type        = string
}

variable "chatbot_image" {
  description = "ECR image URI for the chatbot service"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the ACM certificate"
  type        = string
}

variable "containerPort" {
  description = "Container port for ECS port mapping"
  type        = number
}

variable "hostPort" {
  description = "Host port for ECS port mapping"
  type        = number
}

variable "container_port" {
  description = "Container port for the load balancer"
  type        = number
}

variable "existing_log_group_id" {
  description = "ID of an existing CloudWatch Log Group (use null if none)"
  type        = string
  default     = null
}
