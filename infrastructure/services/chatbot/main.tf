resource "aws_ecr_repository" "chatbot" {
  name                 = "${var.project}-dev"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

resource "aws_acm_certificate" "cert" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_secretsmanager_secret" "secret" {
  name        = "${var.environment}/${var.project}"
  description = "Environment variables for ${var.environment} ${var.project}"
}

module "load_balancer_public" {
  source             = "../../modules/load_balancer"
  project            = var.project
  environment        = var.environment
  existing_vpc_id    = var.existing_vpc_id
  health_endpoint    = "/health"
  certificate_arn    = aws_acm_certificate.cert.arn
  public_subnets     = var.public_subnets
  public_subnets_ids = var.public_subnets_ids
  container_port     = var.container_port
}

module "cluster" {
  source              = "../../modules/cluster"
  aws_region          = var.aws_region
  project             = var.project
  environment         = var.environment
  public_subnets_ids  = var.public_subnets_ids
  existing_vpc_id     = var.existing_vpc_id
  secrets             = local.secrets
  image               = var.image
  lb_target_group_arn = module.load_balancer_public.lb_target_group_arn
  security_groups     = []
  secrets_arn         = aws_secretsmanager_secret.secret.arn
  depends_on          = [module.load_balancer_public]
  container_port      = var.container_port
  hostPort            = var.hostPort
  containerPort       = var.container_port
  cpu                 = 256
  memory              = 512
}

module "autoscaling" {
  source                      = "../../modules/autoscaling"
  project                     = var.project
  environment                 = var.environment
  aws_region                  = var.aws_region
  aws_ecs_cluster_name        = module.cluster.aws_ecs_cluster_name
  aws_ecs_service_worker_name = module.cluster.aws_ecs_service_worker_name
  depends_on                  = [module.cluster]
}
