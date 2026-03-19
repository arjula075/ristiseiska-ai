from __future__ import annotations

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router

app = FastAPI(title="Ristiseiska API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ristiseiska-ai-1.onrender.com",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"status": "ok", "service": "ristiseiska-api"}


@app.get("/health")
def health():
    return {"status": "ok"}