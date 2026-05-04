output "lb_target_group_arn" {
  value = aws_lb_target_group.lb_target_group.arn
}

output "alb_arn" {
  value = aws_lb.load_balancer.arn
}

