from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
 

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "mysql+pymysql://root:password@localhost:3306/seat_booking"
    test_database_url: str = "mysql+pymysql://root:password@localhost:3306/seat_booking_test"
    hold_duration_seconds: int = 300
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
