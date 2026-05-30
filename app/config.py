from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./rootlens.db", env="DATABASE_URL")
    app_name: str = "RootLens AI Log Ingestion"
    debug: bool = False
    
    # Qdrant configurations
    qdrant_url: str = Field(default=":memory:", env="QDRANT_URL")
    qdrant_collection: str = Field(default="logs", env="QDRANT_COLLECTION")

    class Config:
        env_file = ".env"

settings = Settings()
