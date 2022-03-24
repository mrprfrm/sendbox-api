import uuid
from typing import List

import pydantic
from aioredis import Redis, from_url
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from starlette.middleware.cors import CORSMiddleware

from .models import Action, ActionType, Message
from .settings import AppSettings

settings = AppSettings()


async def get_redis():
    redis = await from_url(settings.broker_url)
    yield redis
    await redis.close()


async def get_db():
    client = AsyncIOMotorClient(settings.db_url, uuidRepresentation="standard")
    yield client[settings.db_name]
    client.close()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessagesCollection(pydantic.BaseModel):
    has_next: bool = False
    messages: List[Message] = []


@app.get("/messages", response_model=MessagesCollection)
async def list_messages(offset: int = 0, db: AsyncIOMotorDatabase = Depends(get_db)):
    cursor = db.messages.find({})
    if offset and offset > 0:
        cursor.skip(offset)
    cursor.limit(settings.per_request_docs_limit).sort("publicated_at", -1)
    count = await db.messages.count_documents({})

    messages = [Message(**doc) async for doc in cursor]
    return MessagesCollection(
        has_next=offset + settings.per_request_docs_limit < count, messages=messages
    )


class MessageRequest(pydantic.BaseModel):
    body: str = pydantic.Field(...)


@app.post("/messages", response_model=Message)
async def create_message(
    request_message: MessageRequest,
    redis: Redis = Depends(get_redis),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Create message endpoint.

    Separated endpoint is needed for sending messages
    because of websocket.receive method blocks main thread.
    """
    message = Message(**request_message.dict())
    await db.messages.insert_one(message.dict())
    action = Action(action_type=ActionType.CREATE, message=message)
    await redis.publish("messages", action.json(by_alias=True))
    return message


@app.patch("/messages/{pk}", response_model=Message)
async def update_message(
    pk: uuid.UUID,
    request_message: MessageRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    if doc := await db.messages.find_one({"id": pk}):
        message = Message(**dict(doc, **request_message.dict()))
        await db.messages.update_one({"id": pk}, {"$set": message.dict()})
        action = Action(action_type=ActionType.UPDATE, message=message)
        await redis.publish("messages", action.json(by_alias=True))
        return message
    raise Exception(f"Message with id {pk} is not exist.")


@app.delete("/messages/{pk}", response_model=Message)
async def delete_message(
    pk: uuid.UUID,
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    if doc := await db.messages.find_one({"id": pk}):
        await db.messages.delete_one({"id": pk})
        messsage = Message(**doc)
        action = Action(action_type=ActionType.DELETE, message=messsage)
        await redis.publish("messages", action.json(by_alias=True))
        return messsage
    raise Exception(f"Message with id {pk} is not exist.")


@app.websocket("/messages")
async def messages_hadler(websocket: WebSocket, redis: Redis = Depends(get_redis)):
    async with redis.pubsub() as pubsub:
        await websocket.accept()
        await pubsub.subscribe("messages")
        try:
            while True:
                # TODO add handler for presence message
                await websocket.receive_text()
                if message := await pubsub.get_message(ignore_subscribe_messages=True):
                    data = message.get("data", "")
                    if data and isinstance(data, bytes):
                        await websocket.send_text(data.decode())
        except WebSocketDisconnect:
            await pubsub.unsubscribe("messages")
