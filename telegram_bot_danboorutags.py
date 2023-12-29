#pip install aiogram==3.2.0

import asyncio
import re
import json
import aiohttp
import re

from aiogram.types import Message, Message
from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command

dp = Dispatcher()
router = Router()

bot = Bot(token="TOKEN")

# Функция для сохранения запросов в JSON
def save_dan_request_to_json(url, tags):
    data = {"url": url, "tags": tags}
    with open("dan_requests.json", "a") as file:
        json.dump(data, file)
        file.write("\n")  # Добавляем перенос строки для читаемости

@dp.message(Command(commands=['dan']))
async def cmd_dan(event: Message):
    parts = event.text.split(maxsplit=1)
    if len(parts) < 2:
        await event.answer("Пожалуйста, укажите ID поста или URL.")
        return

    args = parts[1]
    # Проверяем, является ли аргумент числом (ID поста) или URL
    if args.isdigit():
        post_id = args
    else:
        # Извлекаем ID из URL, если передан URL
        match = re.search(r'/posts/(\d+)', args)
        if match:
            post_id = match.group(1)
        else:
            await event.answer("Пожалуйста, укажите правильный ID поста или URL.")
            return

    url = f"https://danbooru.donmai.us/posts/{post_id}.json"
    await bot.send_chat_action(chat_id=event.chat.id, action="typing") #уведомление что пишется текст
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                post_data = await response.json()

                # Форматирование тегов в моноширинном тексте
                response_text = "<code>"
                categorized_tags = []
                all_tags = []

                # Категоризированные теги
                if 'tag_string_artist' in post_data:
                    categorized_tags.extend(post_data['tag_string_artist'].split())
                if 'tag_string_character' in post_data:
                    categorized_tags.extend(post_data['tag_string_character'].split())
                if 'tag_string_copyright' in post_data:
                    categorized_tags.extend(post_data['tag_string_copyright'].split())
                
                # Добавляем категоризированные теги в основной список
                all_tags.extend(categorized_tags)

                # Добавляем остальные теги
                if 'tag_string' in post_data:
                    all_tags.extend(post_data['tag_string'].split())

                # Формируем ответ
                response_text += ", ".join(all_tags) + "</code>"
                categories_text = "\n\n" + "\n".join([
                    f"Artist: {', '.join(post_data['tag_string_artist'].split())}" if 'tag_string_artist' in post_data else "",
                    f"Characters: {', '.join(post_data['tag_string_character'].split())}" if 'tag_string_character' in post_data else "",
                    f"Copyrights: {', '.join(post_data['tag_string_copyright'].split())}" if 'tag_string_copyright' in post_data else ""
                ]) + "\nОстальное теги"

                response_text += categories_text

                await event.answer(response_text, parse_mode=ParseMode.HTML)
                save_dan_request_to_json(args, all_tags)  # Сохраняем запрос
            else:
                await event.answer("Ошибка при получении информации о посте с Danbooru.")