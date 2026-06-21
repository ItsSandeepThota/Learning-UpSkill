from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes.auth import router as auth_router
from app.core.config import settings
from app.db.mongo import close_mongo_client, init_mongo_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_mongo_client()
    try:
        yield
    finally:
        await close_mongo_client()


app = FastAPI(title="Shizen Bank API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):4200",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "Shizen Bank API"}