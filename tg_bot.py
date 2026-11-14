import asyncio
import io
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

import database as db
from handlers import router as reaction_router
from quiz import SOUNDS_DICT

load_dotenv()
BOT_TOKEN = os.getenv("TG_TOKEN")

PROXY_URL = os.getenv("PROXY_URL", "http://127.0.0.1:2081")
if PROXY_URL:
    session = AiohttpSession(proxy=PROXY_URL)
    bot = Bot(token=BOT_TOKEN, session=session)
else:
    bot = Bot(token=BOT_TOKEN)

dp = Dispatcher(storage=MemoryStorage())
dp.include_router(reaction_router)

# Кэш байтов аудиофайлов в памяти, чтобы не скачивать из Telegram каждый раз заново
AUDIO_CACHE: dict[str, bytes] = {}


async def handle_index(request: web.Request):
    return web.FileResponse("webapp/index.html")


async def handle_tg_sound(request: web.Request):
    """Скачивает звук из Telegram по file_id и отдает его в браузер Mini App."""
    filename = request.match_info["filename"]
    file_id = SOUNDS_DICT.get(filename)

    if not file_id:
        return web.Response(status=404, text="Sound not found")

    if filename not in AUDIO_CACHE:
        tg_file = await bot.get_file(file_id)
        buf = io.BytesIO()
        await bot.download_file(tg_file.file_path, destination=buf)
        AUDIO_CACHE[filename] = buf.getvalue()

    return web.Response(
        body=AUDIO_CACHE[filename],
        content_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes"}
    )


async def api_init(request: web.Request):
    data = await request.json()
    state = await db.get_or_create_user_state(
        user_id=int(data["user_id"]),
        username=data.get("username", ""),
        first_name=data.get("first_name", "")
    )
    return web.json_response(state)


async def api_profile(request: web.Request):
    data = await request.json()
    await db.update_user_profile(
        user_id=int(data["user_id"]),
        gender=data["gender"],
        age=int(data["age"]),
        hearing_status=data["hearing_status"],
        cockpit_familiarity=data["cockpit_familiarity"],
        fatigue_level=int(data["fatigue_level"])
    )
    return web.json_response({"ok": True})


async def api_practice(request: web.Request):
    data = await request.json()
    await db.update_user_practice_count(
        user_id=int(data["user_id"]),
        practice_count=int(data["practice_count"])
    )
    return web.json_response({"ok": True})


async def api_result(request: web.Request):
    data = await request.json()
    await db.save_reaction_results(
        user_id=int(data["user_id"]),
        trial_index=int(data["trial_index"]),
        sound_id=data["sound_id"],
        target_sequence=data["target_sequence"],
        execution_time=float(data["execution_time"]),
        errors=int(data["errors_count"])
    )
    return web.json_response({"ok": True})


def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_post("/api/init", api_init)
    app.router.add_post("/api/profile", api_profile)
    app.router.add_post("/api/practice", api_practice)
    app.router.add_post("/api/result", api_result)
    # Отдаем звуки напрямую из локальной папки sounds_
    app.router.add_static("/sounds/", path="sounds_", name="sounds")
    return app



async def main():
    await db.init_db()

    web_app = create_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8080)
    await site.start()
    print("Веб-сервер Mini App запущен на http://127.0.0.1:8080")

    print("Telegram-бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
