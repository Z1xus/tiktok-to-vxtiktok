import os
import re
import aiohttp
import logging
import pymongo
import sys
import asyncio
from os import getenv
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from aiogram.utils import markdown
from aiogram.filters import Command, CommandStart

load_dotenv()

TOKEN = getenv("TOKEN")
MONGODB_URI = getenv("MONGODB_URI")

router = Router()
db = pymongo.MongoClient(MONGODB_URI).tiktokToVxtiktok

async def get_redirected_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return str(response.url)

@router.message(Command("start"))
async def command_start(message: types.Message, bot: Bot) -> None:
    logging.info("Received /start command")
    await bot.send_message(message.chat.id, "send me a tiktok link and I'll convert it to a vxtiktok link :)")

@router.message(Command("about"))
async def command_start(message: types.Message, bot: Bot) -> None:
    await bot.send_message(
        message.chat.id, 
        "this bot is open-source and avalible on <a href=\"https://github.com/z1xus/tiktok-to-vxtiktok\">github</a>!\n"
        "\nwhat is <a href=\"https://github.com/dylanpdx/vxtiktok\">vxtiktok</a>?\n"
        "it's a web service that fixes tiktok links embedding on various platforms by enabling the ability to watch the video directly in the embed rather than having to open the app.\n"
        "\ncontact me if you have questions <a href=\"https://t.me/z1xus\">@z1xus</a> &lt;3",
        parse_mode='HTML',
        disable_web_page_preview=True
    )

@router.message(Command("replace"))
async def command_toggle(message: types.Message, bot: Bot) -> None:
    if message.chat.type == 'private':
        await bot.send_message(message.chat.id, "this command is intended to be used in group chats ❌")
    else:
        chat_data = db.chats.find_one({"chat_id": message.chat.id}) or {}
        replace_toggle_state = chat_data.get("replace_toggle_state", False)
        db.chats.update_one({"chat_id": message.chat.id}, {"$set": {"replace_toggle_state": not replace_toggle_state}}, upsert=True)
        await bot.send_message(message.chat.id, f"message replacing is {'enabled ✅' if not replace_toggle_state else 'disabled ❌'}")


@router.message(F.content_type == 'text')
async def convert_link(message: types.Message, bot: Bot):
    tiktok_link = re.findall(r"(https?://(?:www\.|vm\.)?tiktok\.com/[^\s]+)", message.text)
    if tiktok_link:
        try:
            redirected_url = tiktok_link[0] if "www.tiktok.com" in tiktok_link[0] else await get_redirected_url(tiktok_link[0])
            vxtiktok_link = redirected_url.split("?")[0].replace("www.tiktok.com", "vxtiktok.com")
            if message.chat.type != 'private':
                chat_data = db.chats.find_one({"chat_id": message.chat.id}) or {}
                if chat_data.get("replace_toggle_state", False):
                    await bot.delete_message(message.chat.id, message.message_id)
            await bot.send_message(message.chat.id, vxtiktok_link)
        except Exception as e:
            logging.error(e)
            await bot.send_message(message.chat.id, "oops, I failed to convert your tiktok link\ncontact the dev @z1xus")
    elif message.chat.type == 'private' and re.findall(r"(https?://[^\s]+)", message.text):
        await bot.send_message(message.chat.id, "this doesn't look like a tiktok link to me 🤨")

@router.inline_query()
async def inline_query_handler(inline_query: types.InlineQuery, bot: Bot):
    tiktok_link = re.findall(r"(https?://(?:www\.|vm\.)?tiktok\.com/[^\s]+)", inline_query.query)
    if tiktok_link:
        try:
            redirected_url = tiktok_link[0] if "www.tiktok.com" in tiktok_link[0] else await get_redirected_url(tiktok_link[0])
            vxtiktok_link = redirected_url.split("?")[0].replace("www.tiktok.com", "vxtiktok.com")
            input_content = InputTextMessageContent(message_text=vxtiktok_link)
            result_id = 'tiktok_link'
            item = InlineQueryResultArticle(
                id=result_id,
                title="converted link",
                input_message_content=input_content,
                description=vxtiktok_link,
                thumbnail_url="https://cdn.discordapp.com/attachments/1118618417650483285/1147749774116782152/sticker.webp",
            )
            await bot.answer_inline_query(inline_query.id, results=[item], cache_time=1)
        except Exception as e:
            logging.error(e)
            await bot.answer_inline_query(inline_query.id, results=[], cache_time=1)
    else:
        input_content = InputTextMessageContent(message_text="❌ no valid link provided")
        item = InlineQueryResultArticle(
            id='not_valid',
            title="not a valid link",
            input_message_content=input_content,
            description="this doesn't look like a tiktok link to me 🤨",
            thumbnail_url="https://cdn.discordapp.com/attachments/1118618417650483285/1147774687628251146/793a1d46c34f47efa9722e05478a704b.webp",
        )
        await bot.answer_inline_query(inline_query.id, results=[item], cache_time=1)

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())