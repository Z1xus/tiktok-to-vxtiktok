import logging
import re
from os import getenv
from typing import Optional
import asyncio

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from aiohttp import ClientSession
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

TOKEN = getenv("TOKEN") or exit("TOKEN is not set in the .env!")
MONGODB_URI = getenv("MONGODB_URI") or exit("MONGODB_URI is not set in the .env!")

logging.basicConfig(level=logging.WARNING)

router = Router()
client = AsyncIOMotorClient(MONGODB_URI)
db = client.tiktokToVxtiktok
chats_collection = db.chats


async def get_redirected_url(url: str) -> str:
    async with ClientSession() as session:
        async with session.get(url) as response:
            return str(response.url)


@router.message(Command(commands=["start"]))
async def command_start(message: types.Message, bot: Bot) -> None:
    await bot.send_message(message.chat.id, "send me a tiktok link and I'll convert it to a vxtiktok link :)")


@router.message(Command(commands=["about"]))
async def command_about(message: types.Message, bot: Bot) -> None:
    await bot.send_message(
        message.chat.id,
        'this bot is open-source and avalible on <a href="https://github.com/z1xus/tiktok-to-vxtiktok">github</a>!\n'
        '\nwhat is <a href="https://github.com/dylanpdx/vxtiktok">vxtiktok</a>?\n'
        "it's a web service that fixes tiktok links embedding on various platforms by enabling the ability to watch the video directly in the embed rather than having to open the app.\n"
        '\ncontact me if you have questions <a href="https://t.me/z1xus">@z1xus</a> &lt;3',
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.message(Command(commands=["replace"]))
async def command_toggle(message: types.Message, bot: Bot) -> None:
    if message.chat.type == "private":
        await bot.send_message(message.chat.id, "this command is intended to be used in group chats ❌")
        return

    chat_data = await chats_collection.find_one({"chat_id": message.chat.id}) or {}
    replace_toggle_state = chat_data.get("replace_toggle_state", False)
    new_state = not replace_toggle_state

    await chats_collection.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"replace_toggle_state": new_state}},
        upsert=True,
    )
    await bot.send_message(
        message.chat.id,
        f"message replacing is {'enabled ✅' if new_state else 'disabled ❌'}",
    )


@router.message()
async def convert_link(message: types.Message, bot: Bot) -> None:
    tiktok_link = re.findall(r"(https?://(?:www\.|vm\.)?tiktok\.com/[^\s]+)", message.text)
    if tiktok_link:
        try:
            redirected_url = (
                tiktok_link[0]
                if "www.tiktok.com" in tiktok_link[0]
                else await get_redirected_url(tiktok_link[0])
            )
            vxtiktok_link = redirected_url.split("?")[0].replace("www.tiktok.com", "vxtiktok.com")

            if message.chat.type != "private":
                chat_data = await chats_collection.find_one({"chat_id": message.chat.id}) or {}
                if chat_data.get("replace_toggle_state", False):
                    await bot.delete_message(message.chat.id, message.message_id)
            await bot.send_message(message.chat.id, vxtiktok_link)
        except Exception as e:
            logging.error(e)
            await bot.send_message(message.chat.id, "oops, I failed to convert your tiktok link\ncontact the dev @z1xus")
    elif message.chat.type == "private" and re.findall(r"(https?://[^\s]+)", message.text):
        await bot.send_message(message.chat.id, "this doesn't look like a tiktok link to me 🤨")


@router.inline_query()
async def inline_query_handler(inline_query: types.InlineQuery, bot: Bot) -> None:
    tiktok_link = re.findall(r"(https?://(?:www\.|vm\.)?tiktok\.com/[^\s]+)", inline_query.query)
    if tiktok_link:
        try:
            redirected_url = (
                tiktok_link[0]
                if "www.tiktok.com" in tiktok_link[0]
                else await get_redirected_url(tiktok_link[0])
            )
            vxtiktok_link = redirected_url.split("?")[0].replace("www.tiktok.com", "vxtiktok.com")
            item = InlineQueryResultArticle(
                id="tiktok_link",
                title="converted link",
                input_message_content=InputTextMessageContent(message_text=vxtiktok_link),
                description=vxtiktok_link,
                thumbnail_url="https://github.com/Z1xus/tiktok-to-vxtiktok/blob/main/assets/cooltent.webp",
            )
            await bot.answer_inline_query(inline_query.id, results=[item], cache_time=30)
        except Exception as e:
            logging.error(e)
            await bot.answer_inline_query(inline_query.id, results=[], cache_time=30)
    else:
        item = InlineQueryResultArticle(
            id="not_valid",
            title="not a valid link",
            input_message_content=InputTextMessageContent(message_text="❌ no valid link provided"),
            description="this doesn't look like a tiktok link to me 🤨",
            thumbnail_url="https://github.com/Z1xus/tiktok-to-vxtiktok/blob/main/assets/shrugtent.webp",
        )
        await bot.answer_inline_query(inline_query.id, results=[item], cache_time=30)


async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    me = await bot.get_me()
    print(f"Logged in as @{me.username} (ID: {me.id})")

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Ctrl+C detected, exiting...")
