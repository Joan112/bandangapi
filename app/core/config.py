"""
Configuración centralizada con Pydantic Settings
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración de la aplicación
    Todas las variables se cargan desde .env
    """

    # ==================== APP ====================
    PROJECT_NAME: str = "BandangWeb API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = Field(default=False)

    # ==================== SECURITY ====================
    SECRET_KEY: str = Field(
        ..., min_length=32, description="Secret key para JWT (mínimo 32 caracteres)"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 8

    # ==================== CORS ====================
    BACKEND_CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
        
    # ==================== RATE LIMITING ====================
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # ==================== EMAIL (Opcional) ====================
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None

    # ==================== AWS S3 (Opcional) ====================
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    AWS_BUCKET_NAME: str | None = None

    # ==================== LOGGING ====================
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_FORMAT: str = "json"  # json | text
    
    # ==================== SUPABASE ====================
    SUPABASE_URL: str = Field(..., description="URL de Supabase")
    SUPABASE_KEY: str = Field(..., description="Clave anónima de Supabase")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Clave de servicio de Supabase (bypasa RLS)")
    SUPABASE_DB_PASSWORD: str | None = Field(None, description="Contraseña de la base de datos de Supabase (solo si usas conexión directa a PostgreSQL)")
    SUPABASE_REALTIME_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Singleton de configuración
    Se cachea para evitar leer .env múltiples veces
    """
    return Settings()


# Instancia global
settings = get_settings()
