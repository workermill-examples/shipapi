import ssl as _ssl
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings


def _asyncpg_url(url: str) -> tuple[str, dict]:
    """Convert a database URL for asyncpg compatibility.

    asyncpg does not accept ``sslmode`` as a query parameter — it expects
    ``ssl`` to be passed via ``connect_args``.  This helper strips
    ``sslmode`` from the URL and returns the cleaned URL plus any extra
    ``connect_args`` needed.
    """
    parts = urlsplit(url)
    qs = parse_qs(parts.query)
    connect_args: dict = {}

    if "sslmode" in qs:
        mode = qs.pop("sslmode")[0]
        if mode in ("require", "verify-ca", "verify-full"):
            connect_args["ssl"] = _ssl.create_default_context()
        new_query = urlencode(qs, doseq=True)
        url = urlunsplit(parts._replace(query=new_query))

    return url, connect_args


_url, _connect_args = _asyncpg_url(settings.database_url)

engine = create_async_engine(
    _url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
