import os
import cloudscraper
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
PORT = int(os.getenv('PORT', 8443))  # Порт, который Render предоставляет
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # URL вашего сервиса

# Проверка WEBHOOK_URL
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL is not set in environment variables")

# URL для авторизации и целевой страницы
LOGIN_URL = 'https://animestars.org/login'
TARGET_URL = 'https://animestars.org/clubs/137/boost/'

# Создаем сессию с cloudscraper
session = cloudscraper.create_scraper(
    delay=15,  # Увеличиваем задержку
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    }
)

# Добавляем реалистичные заголовки
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://animestars.org/',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Функция для извлечения данных формы авторизации
def get_login_form_data():
    try:
        logger.debug(f"Получение формы авторизации с {LOGIN_URL}")
        response = session.get(LOGIN_URL, headers=headers)
        logger.debug(f"Статус ответа от {LOGIN_URL}: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"Не удалось загрузить страницу логина: {response.text}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        form = soup.find('form', {'action': '/login'})  # Ищем форму логина
        if not form:
            logger.error("Форма логина не найдена")
            return None

        # Собираем данные для авторизации
        login_data = {
            'login_name': USERNAME,      # Поле для логина
            'login_password': PASSWORD,  # Поле для пароля
            'login_not_save': '0',      # Стандартное поле DLE
        }

        # Добавляем все скрытые поля из формы
        for input_tag in form.find_all('input', type='hidden'):
            name = input_tag.get('name')
            value = input_tag.get('value', '')  # Устанавливаем пустое значение, если value отсутствует
            if name:
                login_data[name] = value

        logger.debug(f"Собранные данные для авторизации: {login_data}")
        return login_data
    except Exception as e:
        logger.error(f"Ошибка при получении формы авторизации: {e}")
        return None

# Функция для авторизации
def authenticate():
    try:
        login_data = get_login_form_data()
        if not login_data:
            logger.error("Не удалось собрать данные для авторизации")
            return False

        logger.debug(f"Попытка авторизации с данными: {login_data}")
        response = session.post(LOGIN_URL, data=login_data, headers=headers)
        logger.debug(f"Статус ответа от {LOGIN_URL}: {response.status_code}")
        if response.status_code == 200:
            logger.info("Авторизация успешна")
            # Проверяем наличие cookies для подтверждения авторизации
            if any(cookie.name.startswith('__cf') for cookie in session.cookies):
                logger.info("Обнаружены Cloudflare cookies, авторизация может быть успешной")
            # Проверяем перенаправление (успешная авторизация)
            if 'login' not in response.url:
                logger.info(f"Перенаправление после авторизации: {response.url}")
                return True
            else:
                logger.warning("Авторизация не удалась: остались на странице логина")
                return False
        else:
            logger.error(f"Ошибка авторизации: статус {response.status_code}, текст ответа: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при авторизации: {e}")
        return False

# Функция для парсинга данных
def get_card_info():
    if not authenticate():
        logger.error("Не удалось авторизоваться, возвращаем ошибку")
        return "Ошибка авторизации", []
    
    logger.debug(f"Запрос данных с {TARGET_URL}")
    try:
        response = session.get(TARGET_URL, headers=headers)
        logger.debug(f"Статус ответа от {TARGET_URL}: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"Не удалось загрузить страницу: статус {response.status_code}, текст: {response.text}")
            return "Не удалось загрузить страницу", []

        soup = BeautifulSoup(response.text, 'html.parser')

        # Примерные селекторы (уточните после анализа HTML)
        card_section = soup.select_one('div.boost-card-info')  # Замените на реальный селектор
        if card_section:
            current_card = card_section.find('h3').text.strip()  # Название карты
            users = [user.text.strip() for user in card_section.select('ul.users-list li')]  # Список пользователей
            logger.info(f"Найдена карта: {current_card}, владельцы: {users}")
            return current_card, users
        else:
            logger.warning("Секция с картой не найдена, проверьте селектор")
            return "Информация о карте не найдена", []
    except Exception as e:
        logger.error(f"Ошибка при запросе данных: {e}")
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
        logger.info(f"Webhook set to {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        raise

    # Создаем веб-сервер
    web_app = web.Application()
    web_app.router.add_post(f"/{TOKEN}", webhook)
    
    # Запускаем сервер
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Server started on port {PORT}")

    # Держим приложение запущенным
    while True:
        await asyncio.sleep(3600)  # Спим 1 час, чтобы не завершать процесс

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())