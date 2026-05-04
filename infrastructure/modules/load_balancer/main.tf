
data "aws_elb_service_account" "main" {}

resource "aws_lb" "load_balancer" {
  name     = "${var.project}-${var.environment}-lb"
  internal = false

  subnets = var.public_subnets_ids
  # security_groups = var.security_groups
}

resource "aws_lb_target_group" "lb_target_group" {
  name        = "${var.project}-${var.environment}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.existing_vpc_id
  target_type = "ip"

  health_check {
    timeout             = 30
    healthy_threshold   = 5
    unhealthy_threshold = 5
    interval            = 60
    path                = var.health_endpoint
    matcher             = 200
    # port                = "traffic"
  }

  tags = {
    "deregistration_delay.timeout_seconds" = 120
  }
}

resource "aws_lb_listener" "lb_listener_80" {
  load_balancer_arn = aws_lb.load_balancer.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    target_group_arn = aws_lb_target_group.lb_target_group.arn
    type             = "forward"
  }
}

resource "aws_lb_listener" "lb_listener_443" {
  load_balancer_arn = aws_lb.load_balancer.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    target_group_arn = aws_lb_target_group.lb_target_group.arn
    type             = "forward"
  }
}

resource "aws_s3_bucket" "lb_logs_bucket" {
  bucket = "${var.project}-${var.environment}-lb-logs"

  tags = {
    Name        = "${var.project}-${var.environment}-lb-logs"
    Environment = var.environment
  }
}

data "aws_iam_policy_document" "allow_lb_logging" {
  statement {
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [data.aws_elb_service_account.main.arn]
    }

    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.lb_logs_bucket.arn}/AWSLogs/*"]
  }
}
//END LOAD BALANCER
