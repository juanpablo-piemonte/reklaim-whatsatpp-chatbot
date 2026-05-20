import os
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Populate os.environ from .env so boto3 and other libraries that read
# os.environ directly (not pydantic-settings) pick up the credentials.
load_dotenv(override=True)

# Remove session token if empty so boto3 doesn't send an invalid token.
if not os.environ.get("AWS_SESSION_TOKEN"):
    os.environ.pop("AWS_SESSION_TOKEN", None)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore", env_ignore_empty=True)

    # DB — managed by Rails monolith
    db_host: Optional[str] = None
    db_user: Optional[str] = None
    db_pass: Optional[str] = None
    db_name: Optional[str] = None
    db_ssl_cert: str = "global-bundle.pem"  # path to RDS CA bundle

    whatsapp_app_secret: str = "dev-secret"
    whatsapp_verify_token: str = "dev-verify-token"
    whatsapp_access_token: str = "dev-access-token"
    whatsapp_phone_number_id: str = "dev-phone-id"

    reklaim_api_url: str = "http://localhost:5001"
    # Shared secret presented to Rails on service-to-service callbacks
    # (e.g. POST /internal/conversations/:id/dealer_message). Must match
    # CHATBOT_INTERNAL_TOKEN on the Rails side.
    reklaim_internal_token: Optional[str] = None
    dealers_chatbot_api_key: str = "dev-chatbot-key"

    # Token Rails passes via X-Internal-Token when calling /internal/* on the chatbot.
    chatbot_internal_token: str = "dev-internal-token"

    aws_region: str = "us-east-1"
    bedrock_model_id: str = "us.amazon.nova-pro-v1:0"


settings = Settings()
