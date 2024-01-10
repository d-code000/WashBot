import asyncio
import logging

from aiogram.exceptions import TelegramForbiddenError
from aiohttp import ClientSession

import config
import database
from database import Users
import webparser
from service import bot
import text
import keyboard


logger = logging.getLogger(__name__)


async def check_machines() -> None:
    async with ClientSession() as session:
        try:
            for machine in await webparser.get_machines(session):
                await database.add_machine(machine)
        except ConnectionError:
            pass


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
                obj_type=Users,
                obj_id=[user_id]
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
                        machines = await database.get_machines()
                    except ConnectionError:
                        machines = await webparser.get_machines(session)
                    users_id = set()
                    for machine in machines:
                        if status[machine.id] != old_status[machine.id]:
                            users_id.update(await database.get_sub_users(machine.id))
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


