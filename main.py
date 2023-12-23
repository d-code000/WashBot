import yaml
import logging.config
import asyncio

from aiogram import Dispatcher

import script
import user_handlers
from service import bot


async def main():
    logger = logging.getLogger(__name__)
    # await script.check_machines()
    dp = Dispatcher()
    dp.include_routers(user_handlers.router_private)
    main_loops = asyncio.get_event_loop()
    main_loops.create_task(script.update_data())
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging_config = yaml.safe_load(open("logging.yaml", 'rt').read())
    logging.config.dictConfig(logging_config)
    asyncio.run(main())
