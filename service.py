import os

from aiogram import Bot
from aiogram.enums import ParseMode
from cashews import Cache

cache = Cache()
cache.setup("mem://")
bot = Bot(os.getenv("BOT_TOKEN"), parse_mode=ParseMode.HTML)

