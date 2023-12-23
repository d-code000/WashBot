import functools
import logging
from typing import Any, Sequence, Union

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer, BigInteger, String
from sqlalchemy import select, update, delete, Row, RowMapping
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


class Users(Base):
    __tablename__ = "Users"
    id: Column = Column(BigInteger, primary_key=True)
    username = Column(String)
    lang = Column(String(2))
    sub = relationship("Subs", cascade="all,delete", backref="Users")
    admin = relationship("Admins", cascade="all,delete", backref="Users")

    def __repr__(self) -> str:
        return (
            f"Users("
            f"id={self.id!r}, "
            f"username={self.username!r}, "
            f"lang={self.lang}"
            f")"
        )


class Admins(Base):
    __tablename__ = "Admins"
    user_id = Column(ForeignKey(Users.id), primary_key=True)

    def __repr__(self) -> str:
        return (
            f"Admins("
            f"user_id={self.user_id!r}"
            f")"
        )


class Machines(Base):
    __tablename__ = "Machines"
    id: Column = Column(Integer, primary_key=True)
    type = Column(String)
    prise = Column(Integer)
    sub = relationship("Subs", cascade="all,delete", backref="Machines")

    def __repr__(self) -> str:
        return (
            f"Machines("
            f"id={self.id}, "
            f"type={self.type}, "
            f"prise={self.prise}"
            f")"
        )


class Subs(Base):
    __tablename__ = "Subs"
    user_id = Column(ForeignKey(Users.id), primary_key=True)
    machine_id = Column(ForeignKey(Machines.id), primary_key=True)

    def __repr__(self) -> str:
        return (
            f"Subs("
            f"user_id={self.user_id!r}, "
            f"machine_id={self.machine_id}"
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
            logger.info(f"Add user: {user.username}, id {user.id}")
        except IntegrityError:
            logger.error(f"Add user: user with id {user.id} is already exists")


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
            logger.info(f"Add admin: id {admin.user_id}")
        except IntegrityError:
            logger.error(f"Add admin: admin with id {user_id} is already exists or is not a user")


@connect
async def add_machine(_async_session: async_sessionmaker[AsyncSession],
                      machine: Machines
                      ) -> None:
    async with _async_session() as session:
        session.add_all([machine])
        try:
            await session.commit()
            logger.info(f"Add machine: id {machine.id}")
        except IntegrityError:
            logger.error(f"Add machine: machine with id {machine.id} is already exists")


@connect
async def add_sub(_async_session: async_sessionmaker[AsyncSession],
                  user_id: int,
                  machine_id: int
                  ) -> None:
    async with _async_session() as session:
        sub = Subs(
            user_id=user_id,
            machine_id=machine_id
        )
        session.add_all([sub])
        try:
            await session.commit()
            logger.info(f"Add sub: {user_id} - {machine_id} (user id - machine id)")
        except IntegrityError:
            logger.error(f"Add sub: record with id {user_id}, {machine_id} is exists")


@connect
async def remove_by_id(_async_session: async_sessionmaker[AsyncSession],
                       obj_type: [Users, Admins, Machines, Subs],
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
async def is_by_id(_async_session: async_sessionmaker[AsyncSession],
                   obj_type: [Users, Admins, Machines, Subs],
                   obj_id: tuple[int, ...]
                   ) -> bool:
    async with _async_session() as session:
        try:
            obj = await session.get(obj_type, obj_id)
            return bool(obj)
        except InvalidRequestError:
            logger.error("Not all primary keys are specified when calling session.get")
            logger.warning("An invalid value may have been returned")
            return False


@connect
async def set_user_lang(_async_session: async_sessionmaker[AsyncSession],
                        user_id: int,
                        lang: str
                        ) -> None:
    stmt = (
        update(Users)
        .where(Users.id == user_id)
        .values(lang=lang)
    )
    async with _async_session() as session:
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Changing the language of a user with an id {user_id}"
                    f" {lang}")


@connect
async def get_user_lang(_async_session: async_sessionmaker[AsyncSession],
                        user_id: int
                        ) -> str:
    stmt = (select(Users.lang)
            .where(Users.id == user_id))
    async with _async_session() as session:
        result = await session.execute(stmt)
        return result.scalar()


@connect
async def get_machines(_async_session: async_sessionmaker[AsyncSession],
                       ) -> Sequence[Machines]:
    stmt = select(Machines).order_by(Machines.id)
    async with _async_session() as session:
        machines = await session.scalars(stmt)
        return machines.all()


@connect
async def get_user_subs(_async_session: async_sessionmaker[AsyncSession],
                        user_id: int
                        ) -> tuple[Union[Union[Row, RowMapping], Any], ...]:
    stmt = (select(Subs.machine_id)
            .where(Subs.user_id == user_id)
            .order_by(Subs.machine_id))
    async with _async_session() as session:
        subs = await session.scalars(stmt)
        return tuple(subs.all())


@connect
async def get_sub_users(_async_session: async_sessionmaker[AsyncSession],
                        machine_id: int
                        ) -> tuple[int]:
    stmt = (select(Subs.user_id)
            .where(Subs.machine_id == machine_id)
            .order_by(Subs.user_id))
    async with _async_session() as session:
        users_id = await session.scalars(stmt)
        return tuple(users_id.all())


@connect
async def remove_subs(_async_session: async_sessionmaker[AsyncSession],
                      user_id: int
                      ) -> None:
    stmt = delete(Subs).where(Subs.user_id == user_id)
    async with _async_session() as session:
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Remove subs of a user with id {user_id}")
