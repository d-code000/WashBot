import logging
from typing import Sequence

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

import text
import keyboard
import database
from database import Users, Machines, Subs
from config import DEFAULT_LANG
from config import LANGUAGES

logger = logging.getLogger(__name__)
router_private = Router()
router_private.message.filter(F.chat.type == "private")


class OrderSub(StatesGroup):
    choosing_sub = State()


async def check_is_user(message: Message) -> None:
    if not await database.is_by_id(Users, message.from_user.id):
        await database.add_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            lang=message.from_user.language_code if message.from_user.language_code in LANGUAGES else DEFAULT_LANG
        )


@router_private.message(Command("start"))
async def command_start(message: Message) -> None:
    try:
        await check_is_user(message)
        lang = await database.get_user_lang(message.from_user.id)
        await message.answer(text=text.description[lang],
                             reply_markup=keyboard.menu_lang
                             )
    except ConnectionError:
        await message.answer(text=text.description[DEFAULT_LANG],
                             reply_markup=keyboard.menu_lang
                             )


@router_private.message(Command("status"))
async def command_status(message: Message) -> None:
    try:
        await check_is_user(message)
        lang = await database.get_user_lang(message.from_user.id)
    except ConnectionError:
        lang = DEFAULT_LANG
    try:
        report = await text.get_status()
        await message.answer(text=report[lang],
                             reply_markup=keyboard.menu_update[lang]
                             )
    except ConnectionError:
        await message.answer(text="The site is unavailable, please update later",
                             reply_markup=keyboard.menu_update[lang]
                             )


@router_private.callback_query(F.data == "update")
async def callback_update(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        try:
            lang = await database.get_user_lang(callback.from_user.id)
        except ConnectionError:
            lang = DEFAULT_LANG
        try:
            report = await text.get_status()
            await callback.message.edit_text(text=report[lang],
                                             reply_markup=keyboard.menu_update[lang]
                                             )
        except ConnectionError:
            await callback.message.edit_text(text="The site is unavailable, please update later",
                                             reply_markup=keyboard.menu_update[lang]
                                             )
    except TelegramBadRequest:
        logger.debug("Status has not changed")


@router_private.message(Command("sub"))
async def command_sub(message: Message, state: FSMContext) -> None:
    try:
        await check_is_user(message)
        machines = await database.get_machines()
        lang = await database.get_user_lang(message.from_user.id)
        subs = list(await database.get_user_subs(message.from_user.id))
        kb = await keyboard.menu_sub(machines, subs)
        await message.answer(text=text.sub["start"][lang],
                             reply_markup=kb[lang]
                             )
        await state.clear()
        await state.set_state(OrderSub.choosing_sub)
        await state.update_data(machines=machines,
                                lang=lang,
                                subs=subs
                                )
    except ConnectionError:
        await message.answer(text=text.error[DEFAULT_LANG],
                             reply_markup=keyboard.menu_delete[DEFAULT_LANG]
                             )


@router_private.callback_query(
    OrderSub.choosing_sub,
    F.data.startswith("m")
)
async def callback_set_subs(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    machines: Sequence[Machines] = data["machines"]
    lang: str = data["lang"]
    subs: list = data["subs"]
    sub = int(callback.data[1:])
    if sub in subs:
        subs.remove(sub)
    else:
        subs.append(sub)
    kb = await keyboard.menu_sub(machines, subs)
    try:
        await callback.message.edit_text(text=text.sub["start"][lang],
                                         reply_markup=kb[lang]
                                         )
    except TelegramBadRequest:
        logger.debug("Subs has not changed")
    await state.update_data(machines=machines,
                            lang=lang,
                            subs=subs
                            )


@router_private.callback_query(
    OrderSub.choosing_sub,
    F.data.startswith("sub")
)
async def callback_subs(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    machines: Sequence[Machines] = data["machines"]
    lang: str = data["lang"]
    subs: list = data["subs"]
    await callback.answer(text.sub["subscribe"][lang])
    await callback.message.delete()
    user_subs = await database.get_user_subs(callback.from_user.id)
    for machine in machines:
        if machine.id in subs and machine.id not in user_subs:
            await database.add_sub(user_id=callback.from_user.id,
                                   machine_id=machine.id)
        elif machine.id not in subs and machine.id in user_subs:
            await database.remove_by_id(obj_type=Subs,
                                        obj_id=(callback.from_user.id, machine.id))
    await state.clear()


@router_private.callback_query(F.data.in_(LANGUAGES))
async def callback_set_languages(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        await callback.message.edit_text(text=text.description[callback.data],
                                         reply_markup=keyboard.menu_lang
                                         )
    except TelegramBadRequest:
        logger.debug("Language has not changed")

    try:
        if await database.get_user_lang(callback.from_user.id) != callback.data:
            await database.set_user_lang(callback.from_user.id, callback.data)
    except ConnectionError:
        pass


@router_private.callback_query(F.data == "delete")
async def callback_delete(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.delete()
    await state.clear()


@router_private.message(Command("unsub"))
async def command_unsub(message: Message) -> None:
    try:
        lang = await database.get_user_lang(message.from_user.id)
        await message.answer(text=text.unsub[lang],
                             reply_markup=keyboard.menu_delete[lang]
                             )
        await database.remove_subs(message.from_user.id)
    except ConnectionError:
        await message.answer(text=text.error[DEFAULT_LANG],
                             reply_markup=keyboard.menu_delete[DEFAULT_LANG]
                             )


@router_private.callback_query(
    OrderSub.choosing_sub,
    F.data == "unsub")
async def command_unsub(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang: str = data["lang"]
    await callback.answer(text=text.unsub[lang])
    await callback.message.delete()
    try:
        await database.remove_subs(callback.from_user.id)
    except ConnectionError:
        await callback.message.answer(text=text.error[DEFAULT_LANG],
                                      reply_markup=keyboard.menu_delete[DEFAULT_LANG]
                                      )

    await state.clear()


@router_private.callback_query(F.data == "unsub")
async def command_unsub(callback: CallbackQuery) -> None:
    try:
        lang = await database.get_user_lang(callback.from_user.id)
    except ConnectionError:
        lang = DEFAULT_LANG
    await callback.answer(text=text.unsub[lang])
    try:
        await database.remove_subs(callback.from_user.id)
    except ConnectionError:
        await callback.message.answer(text=text.error[DEFAULT_LANG],
                                      reply_markup=keyboard.menu_delete[DEFAULT_LANG]
                                      )

