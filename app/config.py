
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    allowed_origins: str = "http://localhost:3000"
    environment: str = "development"
    debug: bool = True

    # Redis
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 300

    # Email
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = ""
    mail_port: int = 587
    mail_starttls: bool = True
    mail_server: str = "smtp.gmail.com"

    @property
    def origins_list(self) -> List[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
        ]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
