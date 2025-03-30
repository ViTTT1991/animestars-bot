import os
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from aiohttp import web
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Получаем переменные окружения
TOKEN = os.getenv('TOKEN')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
PORT = int(os.getenv('PORT', 8443))
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL is not set in environment variables")

LOGIN_URL = 'https://animestars.org/login'
TARGET_URL = 'https://animestars.org/clubs/137/boost/'

# Функция для авторизации и парсинга
async def get_card_info():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Настройка заголовков и параметров браузера
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.5',
        })

        # Авторизация
        logger.debug(f"Попытка авторизации с данными: username={USERNAME}")
        await page.goto(LOGIN_URL, timeout=60000)
        await page.wait_for_load_state('networkidle')

        # Заполняем форму
        await page.fill('input[name="login_name"]', USERNAME)  # Поле для логина
        await page.fill('input[name="login_password"]', PASSWORD)  # Поле для пароля

        # Нажимаем кнопку отправки формы
        await page.click('button[type="submit"]')  # Уточните селектор кнопки, если нужно
        await page.wait_for_url(TARGET_URL, timeout=60000)  # Ждем загрузки целевой страницы

        # Проверка успешности авторизации
        current_url = page.url
        if 'login' in current_url:
            logger.error("Авторизация не удалась: остались на странице логина")
            await browser.close()
            return "Ошибка авторизации", []

        logger.info(f"Авторизация успешна, текущий URL: {current_url}")

        # Парсинг данных
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        # Примерные селекторы (уточните после анализа HTML)
        card_section = soup.select_one('div.boost-card-info')  # Замените на реальный селектор
        if card_section:
            current_card = card_section.find('h3').text.strip()  # Название карты
            users = [user.text.strip() for user in card_section.select('ul.users-list li')]  # Список пользователей
            logger.info(f"Найдена карта: {current_card}, владельцы: {users}")
            await browser.close()
            return current_card, users
        else:
            logger.warning("Секция с картой не найдена, проверьте селектор")
            await browser.close()
            return "Информация о карте не найдена", []

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот для проверки карт с animestars.org. Используй /card, чтобы узнать текущую карту и владельцев.")

# Команда /card
async def card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_card, users = await get_card_info()
    if users:
        users_text = "\n".join(users)
        reply_text = f"Текущая карта: {current_card}\nВладельцы:\n{users_text}"
    else:
        reply_text = f"Текущая карта: {current_card}\nВладельцев пока нет или данные недоступны."
    await update.message.reply_text(reply_text)

# Webhook обработчик
async def webhook(request):
    update = Update.de_json(await request.json(), app.bot)
    await app.process_update(update)
    return web.Response(text="OK")

# Основная функция
async def main():
    global app
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("card", card))

    await app.initialize()
    await app.start()

    webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
    try:
        await app.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        raise

    web_app = web.Application()
    web_app.router.add_post(f"/{TOKEN}", webhook)
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Server started on port {PORT}")

    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())