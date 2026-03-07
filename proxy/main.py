from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncpg
import redis.asyncio as aioredis
from proxy.settings import settings

# Routers added as they are built (Day 4+)
from proxy.routers import completions
# from proxy.routers import models, analytics, health
# from proxy.metrics import router as metrics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db_pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=5,
        max_size=20
    )
    app.state.redis = await aioredis.from_url(
        settings.redis_url,
        decode_responses=True
    )
    yield
    # Shutdown
    await app.state.db_pool.close()
    await app.state.redis.close()


app = FastAPI(
    title="NeuralGate",
    description="Intelligent LLM cost-optimization proxy",
    version="1.0.0",
    lifespan=lifespan
)

# Routers registered here as they are built (Day 4+)
app.include_router(completions.router)
# app.include_router(models.router)
# app.include_router(analytics.router, prefix="/analytics")
# app.include_router(health.router)
# app.include_router(metrics_router)
