from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str | None = None
    MONDAY_API_KEY: str | None = None
    MONDAY_BOARD_ID: int = 18396329631

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
