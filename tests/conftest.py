import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from app.settings import AppSettings

settings = AppSettings()


@pytest.fixture
async def db():
    client = AsyncIOMotorClient(
        "mongodb://localhost:27017", uuidRepresentation="standard"
    )
    yield client["test"]
    client.drop_database("test")
