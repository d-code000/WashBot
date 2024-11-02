import yaml
import logging.config
import asyncio

from aiogram import Dispatcher

import script
import user_handlers
from service import bot


async def startup():
    asyncio.create_task(script.update_data())


async def main():
    logger = logging.getLogger(__name__)
    await script.check_bot()
    await script.check_machines()
    dp = Dispatcher()
    dp.include_routers(user_handlers.router_private)
    dp.startup.register(startup)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging_config = yaml.safe_load(open("logging.yaml", 'rt').read())
    logging.config.dictConfig(logging_config)
    asyncio.run(main())
