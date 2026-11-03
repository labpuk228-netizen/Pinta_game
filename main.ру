import asyncio
import os

from aiohttp import web
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database import init_db
from handlers import start, profile, jobs, transfers, admin, property, education, top
from tasks.scheduler import start_scheduler


async def health(request):
    return web.Response(text="OK")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(jobs.router)
    dp.include_router(transfers.router)
    dp.include_router(admin.router)
    dp.include_router(property.router)
    dp.include_router(education.router)
    dp.include_router(top.router)

    start_scheduler()
    await start_web_server()
    print("Бот Пихта запущен (Этап 2)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
