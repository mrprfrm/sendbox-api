from pydantic import BaseSettings


class AppSettings(BaseSettings):
    broker_url: str = "redis://localhost:6379"
    db_url: str = "mongodb://localhost:27017"
    db_name: str = "default"
    per_request_docs_limit = 50
    origins: list = ["*"]
