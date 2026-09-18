import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    autopay,
    bills,
    cases,
    chat,
    customers,
    disputes,
    fastag,
    followups,
    nishchint,
    refunds,
    simulation,
    tickets,
    transactions,
    voice,
    workflows,
)
from app.config import get_settings
from app.database.seed import seed_if_empty
from app.database.session import Base, SessionLocal, engine
from app.models import *  # noqa: F401,F403  (ensures all models are registered on Base before create_all)

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(title="Nishchint", description="Autonomous AI support teammate — prototype backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(customers.router)
app.include_router(transactions.router)
app.include_router(cases.router)
app.include_router(tickets.router)
app.include_router(disputes.router)
app.include_router(followups.router)
app.include_router(simulation.router)
app.include_router(workflows.router)
app.include_router(bills.router)
app.include_router(fastag.router)
app.include_router(autopay.router)
app.include_router(refunds.router)
app.include_router(nishchint.router)
app.include_router(voice.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "nishchint-backend"}
