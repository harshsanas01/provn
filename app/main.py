from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import load_config
from app.limiter import InMemoryRateLimiter
from app.middleware import RateLimitMiddleware
from app.stats import get_stats

config = load_config()
limiter = InMemoryRateLimiter(config=config)

app = FastAPI(title="Rate Limiter Proof of Concept")
app.add_middleware(RateLimitMiddleware, limiter=limiter, config=config)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/items")
def list_items() -> dict[str, str]:
    return {"status": "ok", "message": "listed"}


@app.post("/api/items")
def create_item() -> dict[str, str]:
    return {"status": "ok", "message": "created"}


@app.put("/api/items/{item_id}")
def update_item(item_id: str) -> dict[str, str]:
    return {"status": "ok", "message": f"updated {item_id}"}


@app.delete("/api/items/{item_id}")
def delete_item(item_id: str) -> dict[str, str]:
    return {"status": "ok", "message": f"deleted {item_id}"}


@app.get("/api/reports")
def reports() -> dict[str, str]:
    return {"status": "ok", "message": "reports"}


@app.get("/internal/rate-limit-stats")
def stats() -> JSONResponse:
    return JSONResponse(content=get_stats(limiter))
