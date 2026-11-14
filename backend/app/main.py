from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import PipelineStage, User
from app.routers import (
    auth_routes,
    conversation_routes,
    number_routes,
    pipeline_routes,
    tracking_routes,
    user_routes,
    webhook_routes,
    ws_routes,
)
from app.security import hash_password

DEFAULT_STAGES = [
    ("Nuevo", False, False),
    ("Contactado", False, False),
    ("Calificado", False, False),
    ("Propuesta", False, False),
    ("Ganado", True, False),
    ("Perdido", False, True),
]


def seed() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        if db.scalar(select(PipelineStage.id).limit(1)) is None:
            for position, (name, won, lost) in enumerate(DEFAULT_STAGES):
                db.add(PipelineStage(name=name, position=position, is_won=won, is_lost=lost))
        if db.scalar(select(User.id).limit(1)) is None:
            db.add(
                User(
                    email=settings.admin_email,
                    name="Admin",
                    hashed_password=hash_password(settings.admin_password),
                    role="admin",
                )
            )
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)  # pasar a Alembic antes de producción
    seed()
    yield


app = FastAPI(title="Control Total WSP Web", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip()
        for o in f"{get_settings().cors_origins},{get_settings().landing_origins}".split(",")
        if o.strip()
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
for module in (auth_routes, number_routes, conversation_routes, pipeline_routes, tracking_routes, user_routes, webhook_routes, ws_routes):
    app.include_router(module.router)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}
