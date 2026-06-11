from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    database_url: str
    telegram_bot_token: str
    google_calendar_credentials: str = "{}"
    google_calendar_id: str = "primary"
    google_calendar_max_retries: int = 3
    google_calendar_base_delay: float = 1.0
    google_calendar_max_delay: float = 10.0
    n8n_webhook_url: str = ""
    reserva_temporal_minutos: int = 10
    recordatorio_horas_antes: int = 24
    env: str = "development"
