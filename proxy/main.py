from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
import asyncpg
import redis.asyncio as aioredis
from proxy.settings import settings

from proxy.routers import completions, models, analytics
from proxy.metrics import router as metrics_router
from proxy.middleware.auth import api_key_middleware
from proxy.middleware.rate_limit import rate_limit_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=5,
        max_size=20,
    )
    app.state.redis = await aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    yield
    await app.state.db_pool.close()
    await app.state.redis.close()


app = FastAPI(
    title="NeuralGate",
    description="Intelligent LLM cost-optimization proxy",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware — FastAPI stack is LIFO, so register rate_limit first (runs second),
# then auth (runs first on every request).
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(api_key_middleware)

# Routers
app.include_router(completions.router)
app.include_router(models.router)
app.include_router(analytics.router, prefix="/analytics")
app.include_router(metrics_router)


@app.get("/health")
async def health(request: Request):
    status = {"status": "ok", "db": "ok", "redis": "ok"}
    try:
        await request.app.state.db_pool.fetchval("SELECT 1")
    except Exception as e:
        status["db"] = str(e)
        status["status"] = "degraded"
    try:
        await request.app.state.redis.ping()
    except Exception as e:
        status["redis"] = str(e)
        status["status"] = "degraded"
    return status
