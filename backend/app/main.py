from __future__ import annotations

from fastapi import FastAPI

print("MAIN: before api import")
from .api import router
print("MAIN: after api import")

app = FastAPI(title="Ristiseiska API")

app.include_router(router)

@app.get("/")
def root():
    return {"ok": True}

@app.get("/health")
def health():
    return {"status": "ok"}