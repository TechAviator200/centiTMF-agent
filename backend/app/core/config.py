from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://centitmf:centitmf@postgres:5432/centitmf"
    SYNC_DATABASE_URL: str = "postgresql://centitmf:centitmf@postgres:5432/centitmf"

    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "centitmf"
    S3_SECRET_KEY: str = "centitmf123"
    S3_BUCKET: str = "centitmf-docs"

    OPENAI_API_KEY: str = ""

    LOG_LEVEL: str = "INFO"

    @property
    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.startswith("sk-"))


settings = Settings()
