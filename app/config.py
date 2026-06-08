from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application
    APP_NAME: str = "Hintro Meeting Intelligence Service"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # LLM used api
    GEMINI_API_KEY: str

    # Email reminders (Resend)
    RESEND_API_KEY: str
    REMINDER_FROM_EMAIL: str = "reminders@yourdomain.com"

    # Scheduler
    REMINDER_INTERVAL_HOURS: int = 1


settings = Settings()
