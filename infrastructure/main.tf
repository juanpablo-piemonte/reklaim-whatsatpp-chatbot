terraform {
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
    }
  }
}

module "reklaim-whatsapp-chatbot" {
  source                = "./services/chatbot"
  project               = var.project
  environment           = var.environment
  existing_vpc_id       = var.existing_vpc_id
  image                 = var.chatbot_image
  aws_region            = var.aws_region
  domain_name           = var.domain_name
  containerPort         = var.containerPort
  hostPort              = var.hostPort
  container_port        = var.container_port
  existing_log_group_id = var.existing_log_group_id
  public_subnets_ids    = var.public_subnets_ids
  private_subnets_ids   = var.private_subnets_ids
  public_subnets        = var.public_subnets
}
