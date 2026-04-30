from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Populate os.environ from .env so boto3 and other libraries that read
# os.environ directly (not pydantic-settings) pick up the credentials.
load_dotenv(override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore", env_ignore_empty=True)

    # DB — managed by Rails monolith, used here for the LangGraph checkpointer (TBD)
    db_host: Optional[str] = None
    db_user: Optional[str] = None
    db_pass: Optional[str] = None
    db_name: Optional[str] = None

    whatsapp_app_secret: str = "dev-secret"
    whatsapp_verify_token: str = "dev-verify-token"
    whatsapp_access_token: str = "dev-access-token"
    whatsapp_phone_number_id: str = "dev-phone-id"

    reklaim_api_url: str = "http://localhost:5001"
    dealers_chatbot_api_key: str = "dev-chatbot-key"

    aws_region: str = "us-east-1"
    bedrock_model_id: str = "us.amazon.nova-pro-v1:0"


settings = Settings()
