
variable "project" {
  description = "The project name"
  type        = string
}

variable "environment" {
  description = "The environment (e.g., staging, production)"
  type        = string
}

variable "public_subnets" {
  description = "A list of public subnets inside the VPC"
  type        = list(string)
  default     = ["192.168.101.0/24", "192.168.102.0/24"]
}

variable "public_subnets_ids" {
  description = "A list of public subnets inside the VPC"
  type        = list(string)
}

variable "existing_vpc_id" {
  description = "The VPC Id"
  type        = string
}

# variable "security_groups" {
#   description = "security group id for the rds database"
#   type        = list(any)
# }

variable "health_endpoint" {
  description = "health endpint"
  default     = "/health"
  type        = string
}

variable "certificate_arn" {
  description = "Certificate ARN for https"
  type        = string
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 3000
}
