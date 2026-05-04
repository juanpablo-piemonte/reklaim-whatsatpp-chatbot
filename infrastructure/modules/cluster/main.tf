data "aws_security_group" "default" {
  vpc_id = var.existing_vpc_id
  name   = "default"
}

resource "aws_ecs_cluster" "ecs_cluster" {
  name = "${var.project}-${var.environment}"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }

}

resource "aws_iam_role" "ecs_service" {
  name = "ecs-service-${var.project}-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Effect = "Allow"
      }
    ]
  })
  inline_policy {
    name = "get_secret_policy-${var.project}"
    policy = jsonencode({
      Version = "2012-10-17",
      Statement = [
        {
          Effect = "Allow",
          Action = [
            "secretsmanager:GetSecretValue"
          ],
          Resource = [
            var.secrets_arn
          ]
        },
        {
          Effect : "Allow",
          Action : [
            "ssm:GetParameters"
          ],
          Resource = [
            var.secrets_arn
          ]
        },
        {
          Effect : "Allow",
          Action : [
            "ssmmessages:CreateControlChannel",
            "ssmmessages:CreateDataChannel",
            "ssmmessages:OpenControlChannel",
            "ssmmessages:OpenDataChannel"
          ],
          Resource : "*"
        },

      ]
    })
  }
  inline_policy {
    name = "logging-${var.project}"
    policy = jsonencode({
      Version = "2012-10-17",
      Statement = [
        {
          Effect = "Allow",
          Action = [
            "logs:PutLogEvents",
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:DescribeLogStreams",
            "logs:DescribeLogGroups",
            "logs:PutRetentionPolicy",
            "xray:PutTraceSegments",
            "xray:PutTelemetryRecords",
            "xray:GetSamplingRules",
            "xray:GetSamplingTargets",
            "xray:GetSamplingStatisticSummaries",
            "cloudwatch:PutMetricData",
            "ecr:*",
            "s3:*"
          ]
          Resource = [
            "*"
          ]
        }
      ]
    })
  }
}

resource "aws_cloudwatch_log_group" "log-group" {
  name = "${var.project}-${var.environment}-logs"
}

resource "aws_ecs_task_definition" "task_definition" {
  family                   = "${var.project}-${var.environment}-task-def"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  task_role_arn            = aws_iam_role.ecs_service.arn
  execution_role_arn       = aws_iam_role.ecs_service.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      essential   = true
      memory      = var.memory
      name        = "${var.project}-${var.environment}"
      image       = var.image
      secrets     = var.secrets
      environment = []
      portMappings = [
        {
          containerPort = var.containerPort
          hostPort      = var.hostPort
          appProtocol   = "http"
          protocal      = "http"
        },
      ],
      linuxParameters = {
        initProcessEnabled = true
      }
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.log-group.name,
          "awslogs-region"        = "${var.aws_region}",
          "awslogs-stream-prefix" = "logs"
        }
      }
    }
  ])
  lifecycle {
    ignore_changes = [
    ]
  }
}

resource "aws_ecs_service" "worker" {
  name                               = "${var.project}-${var.environment}"
  cluster                            = aws_ecs_cluster.ecs_cluster.id
  task_definition                    = aws_ecs_task_definition.task_definition.id
  desired_count                      = 1
  force_new_deployment               = true
  launch_type                        = "FARGATE"
  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100
  enable_execute_command             = true
  # depends_on = [
  #   aws_db_instance.main,
  #   null_resource.build_push_dkr_img

  # ]
  network_configuration {
    subnets          = var.public_subnets_ids
    assign_public_ip = true
    security_groups  = var.security_groups
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  load_balancer {
    target_group_arn = var.lb_target_group_arn
    container_name   = "${var.project}-${var.environment}"

    container_port = var.container_port
  }
  lifecycle {
    ignore_changes = [

    ]
  }
}
