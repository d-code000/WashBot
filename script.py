import asyncio
import logging

from aiogram.exceptions import TelegramForbiddenError

import config
import database
from database import Users
import webparser
from service import bot
import text
import keyboard


logger = logging.getLogger(__name__)


async def check_machines() -> None:
    try:
        for machine in await webparser.get_machines():
            await database.add_machine(machine)
    except ConnectionError:
        pass


async def mailing(users_id: list[int], message: dict[str: str], reply_markup: dict[str: str]) -> None:
    for user_id in users_id:
        if await database.is_by_id(
            obj_type=Users,
            obj_id=[user_id]
        ):
            lang = await database.get_user_lang(user_id)
            try:
                await bot.send_message(chat_id=user_id,
                                       text=message[lang],
                                       reply_markup=reply_markup[lang])
            except TelegramForbiddenError:
                await database.remove_by_id(
                    obj_type=Users,
                    obj_id=[user_id]
                )


async def update_data() -> None:
    old_status = await webparser.get_machines_status()
    while True:
        status = await webparser.get_machines_status()
        time = await webparser.get_time_last_update()
        if status != old_status:
            machines = await database.get_machines()
            users_id = set()
            for machine in machines:
                if status[machine.id] != old_status[machine.id]:
                    users_id.update(await database.get_sub_users(machine.id))
            users_id = list(users_id)
            users_id.sort()
            await mailing(
                users_id=users_id,
                message=await text.get_status(status, time),
                reply_markup=keyboard.menu_update
            )
            old_status = status
        await asyncio.sleep(config.UPDATE_TIME)


