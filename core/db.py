# core/db.py : Database connection setup and session management for async SQLAlchemy with PostgreSQL


from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from core.config import settings

# creating a connection pool to PostgreSQL :
engine = create_async_engine(
    settings.database_url,
    echo=settings.sql_echo,
)

# Creating session factory : 
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False 
)

Base = declarative_base()

# DEPENDENCY :
async def get_db() :
    async with AsyncSessionLocal() as session :
        yield session
