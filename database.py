import logging
import functools


from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.exc import IntegrityError

import config

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = "Users"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    lang = Column(String(2))

    def __repr__(self) -> str:
        return (
            f"Users("
            f"id={self.id!r}, "
            f"username={self.username!r}, "
            f"lang={self.lang})"
        )


class Subs(Base):
    __tablename__ = "Subs"
    user_id = Column(ForeignKey("Users.id"), primary_key=True)

    def __repr__(self) -> str:
        return (
            f"Subs(user_id={self.user_id!r}"
            )


class Admins(Base):
    __tablename__ = "Admins"
    user_id = Column(ForeignKey("Users.id"), primary_key=True)

    def __repr__(self) -> str:
        return (
            f"Admins(user_id={self.user_id!r}"
            )


def connect(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            engine = create_async_engine(config.DB_URL)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async_session = async_sessionmaker(engine, expire_on_commit=False)
            logger.info(f"Create async engine ({config.DB_URL})")
            await func(async_session, *args, **kwargs)
            await engine.dispose()
        except OSError:
            logger.error("No connection to database")

    return wrapper


@connect
async def add_user(_async_session: async_sessionmaker[AsyncSession],
                   user_id: int,
                   username: str = None,
                   lang: str = "ru"
                   ) -> None:
    async with _async_session() as session:
        user = Users(
            id=user_id,
            username=username,
            lang=lang
        )
        session.add_all([user])
        try:
            await session.commit()
            logger.info(f"Add user: {username} (id {user_id})")
        except IntegrityError:
            logger.error(f"User with id {user_id} has already been added")


@connect
async def add_admin(_async_session: async_sessionmaker[AsyncSession],
                    user_id: int
                    ) -> None:
    async with _async_session() as session:
        admin = Admins(
            user_id=user_id
        )
        session.add_all([admin])
        try:
            await session.commit()
            logger.info(f"Add admin: (id {user_id})")
        except IntegrityError:
            logger.error(f"Admin with id {user_id} has already been added")

