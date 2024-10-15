import functools
import logging
from typing import Any, Sequence

from sqlalchemy import Column
from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy import Integer, BigInteger, String
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import UnmappedInstanceError

import config

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class Bot(Base):
    __tablename__ = "Bot"
    id: Column = Column(BigInteger, primary_key=True)
    username = Column(String)
    user = relationship("User", cascade="all,delete", backref="Bot")
    machine = relationship("Machine", cascade="all,delete", backref="Bot")

    def __repr__(self) -> str:
        return (
            f"Bot("
            f"id={self.id}, "
            f"username={self.username}"
            f")"
        )


class User(Base):
    __tablename__ = "User"
    id: Column = Column(BigInteger, primary_key=True)
    bot_id = Column(ForeignKey(Bot.id))
    username = Column(String)
    lang = Column(String(2))
    sub = relationship("Sub", cascade="all,delete", backref="User")
    admin = relationship("Admin", cascade="all,delete", backref="User")

    def __repr__(self) -> str:
        return (
            f"User("
            f"id={self.id}, "
            f"bot_id={self.bot_id}"
            f"username={self.username}, "
            f"lang={self.lang}"
            f")"
        )


class Admin(Base):
    __tablename__ = "Admin"
    user_id = Column(ForeignKey(User.id), primary_key=True)

    def __repr__(self) -> str:
        return (
            f"Admin("
            f"user_id={self.user_id}"
            f")"
        )


class Machine(Base):
    __tablename__ = "Machine"
    seq_num = Column(Integer, primary_key=True)
    bot_id = Column(ForeignKey(Bot.id), primary_key=True)
    type = Column(String)
    prise = Column(Integer)
    sub = relationship("Sub", cascade="all,delete", backref="Machine")

    def __repr__(self) -> str:
        return (
            f"Machine("
            f"seq_num={self.seq_num}, "
            f"bot_id={self.bot_id}, "
            f"type={self.type}, "
            f"prise={self.prise}"
            f")"
        )


class Sub(Base):
    __tablename__ = "Sub"
    user_id = Column(ForeignKey(User.id), primary_key=True)
    seq_num: Column = Column(Integer, primary_key=True)
    bot_id: Column = Column(BigInteger, primary_key=True)
    machine_id = ForeignKeyConstraint([seq_num, bot_id], [Machine.seq_num, Machine.bot_id])

    def __repr__(self) -> str:
        return (
            f"Sub("
            f"user_id={self.user_id}, "
            f"seq_num={self.seq_num}, "
            f"bot_id={self.bot_id}"
            f")"
        )


def connect(func) -> Any:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            engine = create_async_engine(config.DB_URL)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async_session = async_sessionmaker(engine, expire_on_commit=False)
            logger.debug(f"Create async engine {config.DB_URL}")
            result = await func(async_session, *args, **kwargs)
            await engine.dispose()
            return result
        except OSError as exc:
            logger.error("No connection to database")
            raise ConnectionError("No connection to database") from exc

    return wrapper


@connect
async def add_object(_async_session: async_sessionmaker[AsyncSession],
                     obj: [User, Admin, Machine, Sub, Bot]
                     ) -> None:
    async with _async_session() as session:
        session.add_all([obj])
        try:
            await session.commit()
            logger.info(f"Add {obj.__tablename__} with id ?")
        except IntegrityError:
            logger.error(f"{obj.__tablename__} with id ? is already exists")


@connect
async def remove_by_id(_async_session: async_sessionmaker[AsyncSession],
                       obj_type: [User, Admin, Machine, Sub, Bot],
                       obj_id: tuple[int, ...]
                       ) -> None:
    async with _async_session() as session:
        try:
            obj = await session.get(obj_type, obj_id)
            await session.delete(obj)
            await session.commit()
            logger.info(f"Remove object from table {obj_type.__tablename__}: id {obj_id}")
        except UnmappedInstanceError:
            logger.error(f"Remove object from table {obj_type.__tablename__}: object with id {obj_id} not found")


@connect
async def get_by_id(_async_session: async_sessionmaker[AsyncSession],
                    obj_type: [User, Admin, Machine, Sub, Bot],
                    obj_id: tuple[int, ...]
                    ) -> [User, Admin, Machine, Sub, Bot]:
    async with _async_session() as session:
        try:
            obj = await session.get(obj_type, obj_id)
            return obj
        except InvalidRequestError:
            logger.error("Not all primary keys are specified when calling session.get")


@connect
async def set_user_lang(_async_session: async_sessionmaker[AsyncSession],
                        user_id: int,
                        lang: str
                        ) -> None:
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(lang=lang)
    )
    async with _async_session() as session:
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Changing the language of a user with an id {user_id} {lang}")


@connect
async def get_user_lang(_async_session: async_sessionmaker[AsyncSession],
                        user_id: int
                        ) -> str:
    stmt = (select(User.lang)
            .where(User.id == user_id))
    async with _async_session() as session:
        result = await session.execute(stmt)
        return result.scalar()


@connect
async def get_machines(_async_session: async_sessionmaker[AsyncSession],
                       bot_id: int
                       ) -> Sequence[Machine]:
    stmt = (select(Machine)
            .where(Machine.bot_id == bot_id)
            .order_by(Machine.seq_num))
    async with _async_session() as session:
        machines = await session.scalars(stmt)
        return machines.all()


@connect
async def get_user_subs(_async_session: async_sessionmaker[AsyncSession],
                        user_id: int
                        ) -> tuple[int]:
    stmt = (select(Sub.seq_num)
            .where(Sub.user_id == user_id)
            .order_by(Sub.seq_num))
    async with _async_session() as session:
        subs = await session.scalars(stmt)
        return tuple(subs.all())


@connect
async def get_sub_users(_async_session: async_sessionmaker[AsyncSession],
                        seq_num: int,
                        bot_id: int
                        ) -> tuple[int]:
    stmt = (select(Sub.user_id)
            .where(Sub.seq_num == seq_num)
            .where(Sub.bot_id == bot_id)
            .order_by(Sub.user_id))
    async with _async_session() as session:
        users_id = await session.scalars(stmt)
        return tuple(users_id.all())


@connect
async def remove_subs(_async_session: async_sessionmaker[AsyncSession],
                      user_id: int
                      ) -> None:
    stmt = delete(Sub).where(Sub.user_id == user_id)
    async with _async_session() as session:
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Remove subs of a user with id {user_id}")


@connect
async def update_bot_id(_async_session: async_sessionmaker[AsyncSession],
                        user_id: int,
                        bot_id: int
                        ) -> None:
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(bot_id=bot_id)
    )
    async with _async_session() as session:
        await session.execute(stmt)
        await session.commit()
        logger.info(f"User {user_id} change new Bot {bot_id}")
