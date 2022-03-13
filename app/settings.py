from pydantic import BaseSettings


class AppSettings(BaseSettings):
    broker_dsn: str = "redis://localhost:6379"
