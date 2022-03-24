import httpx
import pytest
from starlette import status

from app.main import app
from app.models import Message


@pytest.fixture
@pytest.mark.usefixtures("faker", "db")
async def messages(faker, db):
    result = await db.messages.insert_many(
        map(lambda itm: Message(body=faker.text()).dict(), range(0, 100))
    )
    yield result.inserted_ids
    await db.messages.delete_many({"id": {"$in": result.inserted_ids}})


@pytest.fixture
@pytest.mark.usefixtures("faker", "db")
async def message(faker, db):
    message = Message(body=faker.text())
    await db.messages.insert_one(message.dict())
    yield message
    await db.messages.delete_one({"id": message.id})


@pytest.mark.asyncio
@pytest.mark.usefixtures("messages")
@pytest.mark.parametrize(
    "offset,has_next,lenght",
    [
        (0, True, 50),
        (25, True, 50),
        (50, False, 50),
        (75, False, 25),
        (100, False, 0),
    ],
)
async def test_messages_list(offset, has_next, lenght):
    async with httpx.AsyncClient(app=app) as client:
        response = await client.get(f"http://localhost:8000/messages?offset={offset}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["messages"]) == lenght
        assert response.json()["has_next"] == has_next


@pytest.mark.asyncio
@pytest.mark.usefixtures("faker", "db")
async def test_create_message_response(faker, db):
    async with httpx.AsyncClient(app=app) as client:
        body = faker.text()
        response = await client.post(
            "http://localhost:8000/messages", json={"body": body}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["body"] == body
        assert await db.messages.count_documents({"body": body}) == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("faker", "db", "message")
async def test_update_message(faker, db, message):
    async with httpx.AsyncClient(app=app) as client:
        body = faker.text()
        message_id = str(message.id)
        response = await client.patch(
            f"http://localhost:8000/messages/{message_id}", json={"body": body}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["body"] == body
        assert response.json()["id"] == message_id
        assert await db.messages.count_documents({"id": message.id, "body": body}) == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("db", "message")
async def test_delete_message(db, message):
    async with httpx.AsyncClient(app=app) as client:
        message_id = str(message.id)
        response = await client.delete(f"http://localhost:8000/messages/{message_id}")
        assert response.status_code == status.HTTP_200_OK
        assert await db.messages.count_documents({"id": message.id}) == 0
