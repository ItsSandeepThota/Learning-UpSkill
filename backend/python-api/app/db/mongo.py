from typing import Any, Optional
import certifi

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

client: Optional[AsyncIOMotorClient] = None


async def init_mongo_client() -> None:
    global client
    if client is None:
        client_kwargs: dict[str, Any] = {"serverSelectionTimeoutMS": 10000}
        if settings.mongodb_uri.startswith("mongodb+srv://"):
            client_kwargs.update({"tls": True, "tlsCAFile": certifi.where()})
        client = AsyncIOMotorClient(settings.mongodb_uri, **client_kwargs)


async def close_mongo_client() -> None:
    global client
    if client is not None:
        client.close()
        client = None


def get_database() -> AsyncIOMotorDatabase:
    if client is None:
        raise RuntimeError("MongoDB client has not been initialized")
    return client[settings.mongodb_db]