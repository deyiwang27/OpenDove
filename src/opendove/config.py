from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="OPENDOVE_", extra="ignore")

    env: str = "local"
    openai_api_key: str = ""
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/opendove"


settings = Settings()

