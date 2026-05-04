variable "project" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "environment" {
  type = string
}

variable "existing_vpc_id" {
  type = string
}

variable "image" {
  type = string
}

variable "domain_name" {
  type = string
}

variable "public_subnets_ids" {
  type = list(string)
}

variable "private_subnets_ids" {
  type = list(string)
}

variable "public_subnets" {
  type = list(string)
}

variable "containerPort" {
  type = number
}

variable "hostPort" {
  type = number
}

variable "container_port" {
  type = number
}

variable "existing_log_group_id" {
  type    = string
  default = null
}
