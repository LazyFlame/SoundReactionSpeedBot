import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

import database as db
from handlers import router as reaction_router

load_dotenv()
# Ищем токен бота. Убедись, что в .env написано TG_TOKEN=...
BOT_TOKEN = os.getenv("TG_TOKEN")

# Настройка прокси для обхода блокировок (если нужно)
PROXY_URL = "http://127.0.0.1:2081" # Замени на порт своего прокси (2081, 7890 и т.д.)
session = AiohttpSession(proxy=PROXY_URL)
bot = Bot(token=BOT_TOKEN, session=session)

# Если прокси не нужен, просто раскомментируй строку ниже и закомментируй 3 строки выше:
# bot = Bot(token=BOT_TOKEN)

dp = Dispatcher(storage=MemoryStorage())

# Подключаем наш игровой обработчик кнопок
dp.include_router(reaction_router)

async def main():
    # Создаем таблицы базы данных
    await db.init_db()
    print("Бот замера скорости реакции и ошибок запущен успешно...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
