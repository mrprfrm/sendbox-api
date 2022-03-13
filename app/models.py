import uuid
from datetime import datetime

import pydantic


def to_camel_case(snake_str: str) -> str:
    components = snake_str.split("_")
    # We capitalize the first letter of each component except the first one
    # with the 'capitalize' method and join them together.
    return components[0] + "".join(x.capitalize() if x else "_" for x in components[1:])


class User(pydantic.BaseModel):
    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    username: str = pydantic.Field(...)


def default_user():
    """
    User's default factory for Message model.

    Using until authentication logic will be provided.
    """

    user_hash = hash(datetime.now().timestamp())
    return User(username=user_hash)


class Message(pydantic.BaseModel):
    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    body: str = pydantic.Field(...)
    user: User = pydantic.Field(default_factory=default_user)
    publicated_at: datetime = pydantic.Field(default_factory=datetime.utcnow)

    class Config:
        alias_generator = to_camel_case
        allow_population_by_field_name = True
