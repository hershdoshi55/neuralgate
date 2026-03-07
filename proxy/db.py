import asyncpg
from proxy.settings import settings


async def create_pool():
    return await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=5,
        max_size=20
    )


async def get_db(request):
    return request.app.state.db_pool
