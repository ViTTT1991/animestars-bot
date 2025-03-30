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
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # URL вашего сервиса, например https://your-service.onrender.com

# URL для авторизации (уточните после анализа)
LOGIN_URL = 'https://animestars.org/login'
LOGIN_DATA = {
    'username': USERNAME,
    'password': PASSWORD
}

# Создаем сессию
session = requests.Session()

# Функция для авторизации
def authenticate():
    try:
        response = session.post(LOGIN_URL, data=LOGIN_DATA)
        if response.status_code == 200:
            print("Авторизация успешна")
            return True
        else:
            print(f"Ошибка авторизации: {response.status_code}")
            return False
    except Exception as e:
        print(f"Ошибка при авторизации: {e}")
        return False

# Функция для парсинга данных
def get_card_info():
    if not authenticate():
        return "Ошибка авторизации", []
    
    url = "https://animestars.org/clubs/137/boost/"
    try:
        response = session.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Примерные селекторы (уточните после анализа HTML)
        card_section = soup.select_one('div.boost-card-info')  # Замените на реальный селектор
        if card_section:
            current_card = card_section.find('h3').text.strip()  # Название карты
            users = [user.text.strip() for user in card_section.select('ul.users-list li')]  # Список пользователей
            return current_card, users
        return "Информация недоступна", []
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

    # Настраиваем webhook
    await app.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    print(f"Webhook set to {WEBHOOK_URL}/{TOKEN}")

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