#pip install aiogram==3.2.0
#pip install gradio-client==0.7.1

import asyncio
import re
import json
import aiohttp
import os
import re
import time
import aiohttp

from aiogram.types import Message, Message
from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from gradio_client import Client

dp = Dispatcher()
router = Router()


token="UR_TELEGRAM_BOT_TOKEN"
bot = Bot(token)



# Функция для запроса к Danbooru IQDB
async def iqdb_query(image_url):
    iqdb_url = "https://danbooru.donmai.us/iqdb_queries.json"
    async with aiohttp.ClientSession() as session:
        async with session.post(iqdb_url, data={'file': image_url}) as response:
            if response.status == 200:
                response_text = await response.text()  # Получаем текст ответа
                match = re.search(r'post #(\d+)', response_text)
                if match:
                    post_id = match.group(1)  # Извлекаем ID поста
                    return True, post_id
                else:
                    return False, None
            else:
                return False, None


# Обновленный обработчик команды /tags
@dp.message(Command(commands=["tags"]))
async def cmd_tags(event, token):
    bot = Bot (token)
    if event.photo:
        
        photo = event.photo[-1]
        file_id = photo.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        image_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"
        # Запрос к Danbooru IQDB
        iqdb_result, response_data = await iqdb_query(image_url)
        if iqdb_result:
            # Передаем только данные ответа в cmd_dan
            await cmd_dan(event, response_data)
        else:
            # Если изображение не найдено, предлагаем использовать /tt
            #return "Арт не найден в Danbooru. Используйте команду /tt."
            await event.answer("Арт не найден в Danbooru. Используйте команду /tt.", parse_mode=ParseMode.HTML)
    else:
        #return "Пожалуйста, отправьте фото."
        await event.answer("Пожалуйста, отправьте фото.")

@dp.message(Command(commands=['dan']))
async def cmd_dan(event, bot, danbooru_result=None):
    if danbooru_result:
        # Обработка текстового ответа от IQDB
        match = re.search(r'post #(\d+)', danbooru_result)
        if match:
            post_id = match.group(1)
            url = f"https://danbooru.donmai.us/posts/{post_id}.json"
        else:
            #return "Не удалось найти ID поста в результате."
            await event.answer("Не удалось найти ID поста в результате.", parse_mode=ParseMode.HTML)
            
    else:
        parts = event.text.split(maxsplit=1)
        if len(parts) < 2:
            #return "Пожалуйста, укажите ID поста или URL."
            await event.answer("Пожалуйста, укажите ID поста или URL.", parse_mode=ParseMode.HTML)
            

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
                #return "Пожалуйста, укажите правильный ID поста или URL."
                await event.answer("Пожалуйста, укажите правильный ID поста или URL.", parse_mode=ParseMode.HTML)
                

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
                save_dan_request_to_json(args, all_tags)  # Сохраняем запрос

                #return response_text
                await event.answer(response_text, parse_mode=ParseMode.HTML)
                
            else:
                response_text = ("Ошибка при получении информации о посте с Danbooru.")
                #return response_text
                await event.answer(response_text, parse_mode=ParseMode.HTML)

def split_message(text, max_length=4096):
    """Разделение текста на части по max_length символов."""
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

# Создайте функцию для отправки изображения на анализ и получения тегов
# Обновлённая функция для отправки изображения на анализ
async def analyze_image(image_url, score_threshold=0.5):
    
    client = Client("https://hysts-deepdanbooru.hf.space/")
    result = client.predict(image_url, score_threshold, api_name="/predict")
    if isinstance(result, tuple) and len(result) >= 3:
        return result[-1]  # Возвращаем последний элемент кортежа, который содержит теги
    return "Теги не найдены"

# Обработчик команды /tt
@dp.message(Command(commands=["tt", "tags_text", "text_tags"]))
async def cmd_tt(event, token):
    bot = Bot (token)
    # Проверка наличия текста в сообщении
    score_threshold = 0.5  # Значение по умолчанию
    command_text = event.caption if event.photo else event.text
    if command_text:
        args = command_text.split()
        # Проверяем, есть ли второй аргумент и является ли он числом
        if len(args) > 1 and re.match(r'^0\.\d+$', args[1]):
            score_threshold = float(args[1])

    # Создание папки "deepbooru", если её нет
        if not os.path.exists("deepbooru"):
            os.makedirs("deepbooru")
            
    if event.photo:
               
        photo = event.photo[-1]  # Выбираем фотографию с наивысшим качеством
        file_id = photo.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        async with aiohttp.ClientSession() as session:
            image_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"

            # Анализ изображения с учётом заданного порога
            tags = await analyze_image(image_url, score_threshold)
        response_text = "<code>"
        response_text += ", ".join(tags.split(', ')) + "</code>"
        messages = split_message(response_text)
        messages = "".join(messages)
        await session.close()
        #return messages
        await event.answer(messages, parse_mode=ParseMode.HTML)
    
    else:
        print("Event is not a photo, returning None")
        #return "Вы забыли прикрепить фото."
        await event.answer("Вы забыли прикрепить фото.", parse_mode=ParseMode.HTML)

# Функция для сохранения запросов в JSON
def save_dan_request_to_json(url, tags):
    data = {"url": url, "tags": tags}
    with open("dan_requests.json", "a") as file:
        json.dump(data, file)
        file.write("\n")  # Добавляем перенос строки для читаемости
               
