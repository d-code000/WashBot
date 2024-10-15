import asyncio
import logging

from aiogram.types import Message
from aiogram.exceptions import TelegramForbiddenError
from aiohttp import ClientSession

import config
import database
from database import User, Bot
import webparser
from service import bot
import text
import keyboard
from config import LANGUAGES, DEFAULT_LANG


logger = logging.getLogger(__name__)


async def check_machines() -> None:
    async with ClientSession() as session:
        try:
            for machine in await webparser.get_machines(session):
                machine.bot_id = bot.id
                await database.add_object(machine)
        except ConnectionError:
            pass


async def check_bot() -> None:
    if not await database.get_by_id(Bot, bot.id):
        user = await bot.me()
        tg_bot = Bot(
            id=user.id,
            username=user.username
        )
        await database.add_object(tg_bot)


async def check_user(message: Message) -> None:
    user = await database.get_by_id(User, message.from_user.id)
    if not user:
        user = User(
            id=message.from_user.id,
            bot_id=bot.id,
            username=message.from_user.username,
            lang=message.from_user.language_code if message.from_user.language_code in LANGUAGES else DEFAULT_LANG
        )
        await database.add_object(user)
    elif user.bot_id != bot.id:
        await database.remove_subs(user.id)
        await database.update_bot_id(user.id, bot.id)


async def mailing(users_id: list[int], message: dict[str: str], reply_markup: dict[str: str]) -> None:
    for user_id in users_id:
        lang = await database.get_user_lang(user_id)
        try:
            await bot.send_message(chat_id=user_id,
                                   text=message[lang],
                                   reply_markup=reply_markup[lang])
        except TelegramForbiddenError:
            logger.error("User blocked bot")
            await database.remove_by_id(
                obj_type=User,
                obj_id=(user_id, bot.seq_num)
            )


async def update_data() -> None:
    async with ClientSession() as session:
        old_status = None
        while not old_status:
            try:
                old_status = await webparser.get_machines_status(session)
            except ConnectionError:
                await asyncio.sleep(config.UPDATE_TIME)
        while True:
            try:
                status = await webparser.get_machines_status(session)
                if status != old_status:
                    logger.info("Status of machines is changed")
                    try:
                        machines = await database.get_machines(bot.id)
                    except ConnectionError:
                        machines = await webparser.get_machines(session)
                    users_id = set()
                    for machine in machines:
                        if status[machine.seq_num] != old_status[machine.seq_num]:
                            users_id.update(await database.get_sub_users(machine.seq_num, machine.bot_id))
                    users_id = list(users_id)
                    await mailing(
                        users_id=users_id,
                        message=await text.get_status(),
                        reply_markup=keyboard.menu_update
                    )
                    old_status = status
            except ConnectionError:
                pass
            await asyncio.sleep(config.UPDATE_TIME)


