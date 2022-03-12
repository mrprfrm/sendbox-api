import uuid
from datetime import datetime

import pydantic
from fastapi import FastAPI, WebSocket, WebSocketDisconnect


def to_camel_case(snake_str: str) -> str:
    components = snake_str.split("_")
    # We capitalize the first letter of each component except the first one
    # with the 'capitalize' method and join them together.
    return components[0] + "".join(x.capitalize() if x else "_" for x in components[1:])


class User(pydantic.BaseModel):
    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    username: str = pydantic.Field(...)


class Message(pydantic.BaseModel):
    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    content: str = pydantic.Field(...)
    user: User = pydantic.Field(...)
    publicated_at: datetime = pydantic.Field(default_factory=datetime.utcnow)

    class Config:
        alias_generator = to_camel_case
        allow_population_by_field_name = True


class WebsocketManager:
    def __init__(self):
        self._connections: list = []

    async def connect(self, ws: WebSocket) -> User:
        await ws.accept()
        self._connections.append(ws)
        user_hash = hash(datetime.now().timestamp())
        return User(username=f'User-{user_hash}')

    async def send(self, user: User, content: str):
        message = Message(content=content, user=user)
        for connection in self._connections:
            await connection.send_text(message.json(by_alias=True))

    async def disconnect(self, ws: WebSocket):
        self._connections.remove(ws)


app = FastAPI()

manager = WebsocketManager()


@app.websocket('/messages')
async def messages_hadler(websocket: WebSocket):
    user = await manager.connect(websocket)
    try:
        while True:
            if message := await websocket.receive_text():
                await manager.send(user, message)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
