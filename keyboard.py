import logging
from typing import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import Machine
from text import TRANSLATE

logger = logging.getLogger(__name__)

menu_lang = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Ru", callback_data="ru"),
            InlineKeyboardButton(text="🇬🇧 En", callback_data="en")
        ]

    ] +
    [
        [
            InlineKeyboardButton(text="🗑️ Delete", callback_data="delete")
        ]
    ]
    )
menu_update = {
    "ru": InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="update")
            ],
            [
                InlineKeyboardButton(text="🔕 Отписаться", callback_data="unsub")
            ],
            [
                InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete")
            ]
        ]
    ),
    "en": InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Update", callback_data="update")
            ],
            [
                InlineKeyboardButton(text="🔕 Unsubscribe", callback_data="unsub")
            ],
            [
                InlineKeyboardButton(text="🗑️ Delete", callback_data="delete")
            ]
        ]
    )
}

menu_delete = {
    "ru": InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete")
            ]
        ]
    ),
    "en": InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑️ Delete", callback_data="delete")
            ]
        ]
    )
}


async def menu_sub(machines: Sequence[Machine], subs: list[int]) -> dict[str, InlineKeyboardMarkup]:
    menu = {
        "ru": None,
        "en": None
    }
    inline_keyboard = {
        "ru": [],
        "en": []
    }
    for lang in menu.keys():
        for machine in machines:
            if lang != "ru":
                try:
                    trans_type = TRANSLATE[lang][machine.type]
                except KeyError:
                    trans_type = machine.type
                    logger.warning(f"None translate tor type {trans_type}")
                inline_keyboard[lang] += [[
                    InlineKeyboardButton(text=f"{'➤ ' if machine.seq_num in subs else ''} "
                                              f"{trans_type} {machine.seq_num}",
                                         callback_data=f"m{machine.seq_num}")
                ]]
            else:
                inline_keyboard[lang] += [[
                    InlineKeyboardButton(text=f"{'➤ ' if machine.seq_num in subs else ''} "
                                              f"{machine.type} {machine.seq_num}",
                                         callback_data=f"m{machine.seq_num}")
                ]]
    inline_keyboard["ru"] += [
        [InlineKeyboardButton(text="🔔 Подписаться", callback_data="sub")],
        [InlineKeyboardButton(text="🔕 Отписаться", callback_data="unsub")],
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete")
    ]
                              ]
    inline_keyboard["en"] += [
        [InlineKeyboardButton(text="🔔 Subscribe", callback_data="sub")],
        [InlineKeyboardButton(text="🔕 Unsubscribe", callback_data="unsub")],
        [InlineKeyboardButton(text="🗑️ Delete", callback_data="delete")]
    ]

    menu["ru"] = InlineKeyboardMarkup(inline_keyboard=inline_keyboard["ru"])
    menu["en"] = InlineKeyboardMarkup(inline_keyboard=inline_keyboard["en"])

    return menu
