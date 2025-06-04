# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Bog'cha Oshxonasi Boshqaruv Tizimi"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"  # API endpointlari uchun umumiy prefix

    # Ma'lumotlar bazasi
    DATABASE_URL: str

    # JWT sozlamalari
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2 soat

    # Rol nomlari (agar .env da o'zgartirilmasa, default qiymatlar)
    ADMIN_ROLE_NAME: str = "admin"
    MANAGER_ROLE_NAME: str = "menejer"
    CHEF_ROLE_NAME: str = "oshpaz"

    # Ogohlantirish chegaralari
    SUSPICIOUS_DIFFERENCE_PERCENTAGE: float = 15.0  # Foizda

    # Ilova muhiti
    APP_ENV: str = "development"  # "development" yoki "production"

    # Celery sozlamalari
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # WebSocket xabarlari uchun Redis kanali
    WS_MESSAGE_CHANNEL: str = "ws_messages_kindergarten"

    # Vaqt mintaqasi
    TIMEZONE: str = "Asia/Tashkent"

    # Pydantic V2 uchun model_config
    # https://docs.pydantic.dev/latest/usage/pydantic_settings/
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'  # .env da ortiqcha o'zgaruvchilar bo'lsa e'tibor bermaslik
    )


settings = Settings()