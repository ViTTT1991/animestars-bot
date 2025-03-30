import os
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from aiohttp import web

# Получаем переменные окружения
TOKEN = os.getenv('TOKEN')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
PORT = int(os.getenv('PORT', 8443))  # Порт, который Render предоставляет
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # URL вашего сервиса

# Проверка WEBHOOK_URL
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL is not set in environment variables")

# URL для авторизации
LOGIN_URL = 'https://animestars.org/login'
TARGET_URL = 'https://animestars.org/clubs/137/boost/'
LOGIN_DATA = {
    'username': USERNAME,
    'password': PASSWORD
}

# Создаем сессию с заголовками
session = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://animestars.org/',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Функция для авторизации
def authenticate():
    try:
        print(f"Попытка авторизации с данными: username={USERNAME}")
        response = session.post(LOGIN_URL, data=LOGIN_DATA, headers=headers)
        print(f"Статус ответа от {LOGIN_URL}: {response.status_code}")
        if response.status_code == 200:
            print("Авторизация успешна")
            # Проверяем наличие cookies для подтверждения авторизации
            if any(cookie.name.startswith('__cf') for cookie in session.cookies):
                print("Обнаружены Cloudflare cookies, авторизация может быть успешной")
            return True
        else:
            print(f"Ошибка авторизации: статус {response.status_code}, текст ответа: {response.text}")
            return False
    except Exception as e:
        print(f"Ошибка при авторизации: {e}")
        return False

# Функция для парсинга данных
def get_card_info():
    if not authenticate():
        print("Не удалось авторизоваться, возвращаем ошибку")
        return "Ошибка авторизации", []
    
    print(f"Запрос данных с {TARGET_URL}")
    try:
        response = session.get(TARGET_URL, headers=headers)
        print(f"Статус ответа от {TARGET_URL}: {response.status_code}")
        if response.status_code != 200:
            print(f"Не удалось загрузить страницу: статус {response.status_code}, текст: {response.text}")
            return "Не удалось загрузить страницу", []

        soup = BeautifulSoup(response.text, 'html.parser')

        # Примерные селекторы (уточните после анализа HTML)
        card_section = soup.select_one('div.boost-card-info')  # Замените на реальный селектор
        if card_section:
            current_card = card_section.find('h3').text.strip()  # Название карты
            users = [user.text.strip() for user in card_section.select('ul.users-list li')]  # Список пользователей
            print(f"Найдена карта: {current_card}, владельцы: {users}")
            return current_card, users
        else:
            print("Секция с картой не найдена, проверьте селектор")
            return "Информация о карте не найдена", []
    except Exception as e:
        print(f"Ошибка при запросе данных: {e}")
        return "Ошибка загрузки данных", []

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот для проверки карт с animestars.org. Используй /card, чтобы узнать текущую карту и владельцев.")

# Команда /card
async def card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_card, users = get_card_info()
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
    
    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("card", card))

    # Инициализируем приложение
    await app.initialize()
    await app.start()

    # Настраиваем webhook
    webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
    try:
        await app.bot.set_webhook(url=webhook_url)
        print(f"Webhook set to {webhook_url}")
    except Exception as e:
        print(f"Failed to set webhook: {e}")
        raise

    # Создаем веб-сервер
    web_app = web.Application()
    web_app.router.add_post(f"/{TOKEN}", webhook)
    
    # Запускаем сервер
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"Server started on port {PORT}")

    # Держим приложение запущенным
    while True:
        await asyncio.sleep(3600)  # Спим 1 час, чтобы не завершать процесс

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())