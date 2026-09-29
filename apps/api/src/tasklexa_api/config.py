from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "tasklexa-api"
    environment: str = "local"
    demo_mode: bool = False
    cors_origins: str = "http://localhost:3000"

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    database_url: str = "postgresql://tasklexa:tasklexa_dev_password@postgres:5432/tasklexa"

    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "tasklexa_dev_password"
    neo4j_host: str = "neo4j"
    neo4j_bolt_port: int = 7687

    redis_url: str = "redis://redis:6379/0"
    redis_host: str = "redis"
    redis_port: int = 6379

    openrouter_api_key: str | None = None
    band_agent_id: str | None = None
    band_api_key: str | None = None
    band_agent_key: str | None = None
    band_user_key: str | None = None
    similarweb_api_key: str | None = None
    vultr_api_key: str | None = None

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def async_database_url(self) -> str:
        if self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()

