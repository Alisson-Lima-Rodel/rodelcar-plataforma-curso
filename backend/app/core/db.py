from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    # Conexões gerenciadas (Supabase) podem cair entre requisições; valida antes
    # de usar para não estourar erro no primeiro hit após ociosidade.
    pool_pre_ping=True,
    # Mantém o nº de clientes abaixo do teto do pooler do Supabase em modo sessão
    # (15). Sob rajada, querer mais que (pool_size + max_overflow) faz a query
    # AGUARDAR pool_timeout por uma conexão livre — em vez de estourar EMAXCONNSESSION.
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    connect_args=settings.db_connect_args,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
