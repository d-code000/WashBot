import logging

from aiohttp import ClientSession

import database
import webparser
from service import cache
from service import bot
import config

logger = logging.getLogger(__name__)

TRANSLATE = {
        "en": {
            "СТИРКА": "WASHING",
            "КАПСУЛА": "CAPSULE",
            "СУШКА": "DRYING",
            "Свободно": "Freely",
            "Занято": "Occupied",
            "Отключено": "Disabled",
            "Оплачено": "Paid for",
            "В ремонте": "Under repair"
        }
    }


@cache(ttl=config.STATUS_TTL)
async def get_status() -> dict[str: str]:
    async with ClientSession() as session:
        try:
            machines = await database.get_machines(bot.id)
        except ConnectionError:
            machines = await webparser.get_machines(session)
        status = await webparser.get_machines_status(session)
        time = await webparser.get_time_last_update(session)
    report = {
        "ru": f"Состояние машин {time[0]} в {time[1]}:\n",
        "en": f"Status of machines {time[0]} in {time[1]}:\n"
    }
    for lang in report.keys():
        for machine in machines:
            if lang != "ru":
                try:
                    trans_type = TRANSLATE[lang][machine.type]
                except KeyError:
                    trans_type = machine.type
                    logger.warning(f"None translate tor type {trans_type}")
                try:
                    trans_status = TRANSLATE[lang][status[machine.seq_num]]
                except KeyError:
                    trans_status = status[machine.seq_num]
                    logger.warning(f"None translate tor status {trans_status}")
                report[lang] += (f"{'🟢' if status[machine.seq_num] == 'Свободно' else '🔴'}"
                                 f" {trans_type} {machine.seq_num}"
                                 f" - {trans_status}\n")
            else:
                report[lang] += (f"{'🟢' if status[machine.seq_num] == 'Свободно' else '🔴'}"
                                 f" {machine.type} {machine.seq_num}"
                                 f" - {status[machine.seq_num]}\n")
    return report


description = {
    "ru": "Вас приветствует WashBot -  бот по отслеживанию 📈 статуса машин.\n\n"
          f"Устали каждый раз перезагружать <a href='{config.SITE_URL}'>сайт</a> 🔄 в надежде на то, "
          f"что какая-нибудь машина освободиться?"
          " Теперь вы можете просто подписаться на уведомления 🔔 и быть первым,"
          " кто узнает об освободившейся машине!\n\n"
          "Доступные команды:\n"
          "/start - приветствие со списком доступных команд\n"
          "/status - текущий статус машин\n"
          "/sub - подписаться на уведомления\n"
          "/unsub - отписаться от всех уведомлений\n\n"
          "🌐 Данный бот является парсером и поэтому работает только с данными сайта.\n"
          "🔄 Уведомления присылаются сразу же после обновления данных на сайте.\n"
          f"🛠️ Тех. поддержка и предложения по модернизации: <a href='{config.TECH_SUPPORT}'>Disha</a>\n\n"
          "❗ Данный проект является некоммерческим и не имеет никакого отношения к"
          " организации-поставщику услуг ❗",

    "en": "You are welcomed by the WashBot, a bot for tracking 📈 the status of machines.\n\n"
          f"Tired of restarting every time <a href='{config.SITE_URL}'>the site</a> 🔄 in the hope that "
          f"that some machine is free?"
          " Now you can just subscribe to notifications 🔔 and be the first,"
          " who finds out about the freed machine!\n\n"
          "Available commands:\n"
          "/start - greeting with a list of available commands\n"
          "/status - current status of machines\n"
          "/sub - subscribe to notifications\n"
          "/unsub - unsubscribe from all notifications\n\n"
          "🌐 This bot is a parser and therefore works only with site data.\n"
          "🔄 Notifications are sent immediately after updating the data on the site.\n"
          f"🛠️ Those. support and upgrade suggestions: <a href='{config.TECH_SUPPORT}'>Disha</a>\n\n"
          "❗ This project is non-commercial and has nothing to do with"
          " service provider organization ❗"
}

sub = {
    "start": {
        "ru": "Выберите машинки:",
        "en": "Choose machines:"
    },
    "subscribe": {
        "ru": "Вы подписались на машинки",
        "en": "You have subscribed to machines"
    }
}
unsub = {
    "ru": "Вы отписались от всех уведомлений",
    "en": "You have unsubscribed from all notifications"
}

error = {
    "ru": "В данный момент сервис недоступен, мы уже работаем над проблемой",
    "en": "The service is currently unavailable, we are already working on the problem"
}
