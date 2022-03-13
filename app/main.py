from aioredis import Redis, from_url
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect

from app.models import Message
from app.settings import AppSettings

settings = AppSettings()


async def get_redis():
    redis = await from_url(settings.broker_dsn)
    yield redis
    await redis.close()


app = FastAPI()


@app.post("/messages")
async def send_message(message: Message, redis: Redis = Depends(get_redis)):
    """
    Create message endpoint.

    Separated endpoint is needed for sending messages
    because of websocket.receive method blocks main thread.
    """

    await redis.publish("messages", message.json(by_alias=True))
    return message


@app.websocket("/messages")
async def messages_hadler(websocket: WebSocket, redis: Redis = Depends(get_redis)):
    await websocket.accept()
    pubsub = redis.pubsub()
    await pubsub.subscribe("messages")
    try:
        while True:
            if message := await pubsub.get_message():
                data = message.get("data", "")
                if data and isinstance(data, bytes):
                    await websocket.send_text(data.decode())
    except WebSocketDisconnect:
        pass
