from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Populate os.environ from .env so boto3 and other libraries that read
# os.environ directly (not pydantic-settings) pick up the credentials.
load_dotenv(override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore", env_ignore_empty=True)

    mysql_url: Optional[str] = None

    whatsapp_app_secret: str = "dev-secret"
    whatsapp_verify_token: str = "dev-verify-token"
    whatsapp_access_token: str = "dev-access-token"
    whatsapp_phone_number_id: str = "dev-phone-id"

    monolith_internal_url: str = "http://localhost:3000"
    monolith_internal_token: str = "dev-internal-token"

    aws_region: str = "us-east-1"
    bedrock_model_id: str = "us.amazon.nova-pro-v1:0"


settings = Settings()
