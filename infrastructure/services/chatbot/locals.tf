locals {
  secrets = [
    {
      "name"      : "WHATSAPP_APP_SECRET",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:WHATSAPP_APP_SECRET::"
    },
    {
      "name"      : "WHATSAPP_VERIFY_TOKEN",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:WHATSAPP_VERIFY_TOKEN::"
    },
    {
      "name"      : "WHATSAPP_ACCESS_TOKEN",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:WHATSAPP_ACCESS_TOKEN::"
    },
    {
      "name"      : "WHATSAPP_PHONE_NUMBER_ID",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:WHATSAPP_PHONE_NUMBER_ID::"
    },
    {
      "name"      : "AWS_REGION",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:AWS_REGION::"
    },
    {
      "name"      : "AWS_ACCESS_KEY_ID",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:AWS_ACCESS_KEY_ID::"
    },
    {
      "name"      : "AWS_SECRET_ACCESS_KEY",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:AWS_SECRET_ACCESS_KEY::"
    },
    {
      "name"      : "AWS_SESSION_TOKEN",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:AWS_SESSION_TOKEN::"
    },
    {
      "name"      : "BEDROCK_MODEL_ID",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:BEDROCK_MODEL_ID::"
    },
    {
      "name"      : "REKLAIM_API_URL",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:REKLAIM_API_URL::"
    },
    {
      "name"      : "DEALERS_CHATBOT_API_KEY",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:DEALERS_CHATBOT_API_KEY::"
    },
    {
      "name"      : "DB_HOST",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:DB_HOST::"
    },
    {
      "name"      : "DB_USER",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:DB_USER::"
    },
    {
      "name"      : "DB_PASS",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:DB_PASS::"
    },
    {
      "name"      : "DB_NAME",
      "valueFrom" : "${aws_secretsmanager_secret.secret.arn}:DB_NAME::"
    },
  ]
}
