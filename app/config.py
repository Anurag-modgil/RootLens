from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./rootlens.db", env="DATABASE_URL")
    app_name: str = "RootLens AI Log Ingestion"
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
