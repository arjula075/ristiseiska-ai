from __future__ import annotations

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import time
import threading
from contextlib import asynccontextmanager
import os
from .app_state import state

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router

def load_model_background():
    try:
        print("Loading model...")

        # TODO: siirrä tänne sun nykyinen model loading
        # esim:
        # state.model = load_model("...")

        time.sleep(3)  # testiksi

        state.model_loaded = True
        state.ready = True
        print("Model ready")

    except Exception as e:
        print("Model load failed:", e)
    finally:
        state.model_loading = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=load_model_background, daemon=True)
    t.start()
    yield

app = FastAPI(lifespan=lifespan)

raw_origins = os.getenv("FRONTEND_ORIGINS", "")
allow_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

if not allow_origins:
    allow_origins = [
        "http://localhost:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"status": "ok", "service": "ristiseiska-api"}

from fastapi.responses import JSONResponse

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_loading": state.model_loading,
        "model_loaded": state.model_loaded,
    }

@app.get("/ready")
async def ready():
    if state.ready:
        return {"status": "ready"}

    return JSONResponse(
        status_code=503,
        content={"status": "warming_up"}
    )