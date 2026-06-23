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
    telegram_webhook_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_calendar_credentials: str = "{}"
    google_calendar_id: str = "primary"
    google_calendar_max_retries: int = 3
    google_calendar_base_delay: float = 1.0
    google_calendar_max_delay: float = 10.0
    n8n_webhook_url: str = ""
    reserva_temporal_minutos: int = 10
    lista_espera_minutos: int = 5
    recordatorio_horas_antes: int = 24
    recordatorio_job_interval_minutos: int = 60
    completado_job_interval_minutos: int = 5
    env: str = "development"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
