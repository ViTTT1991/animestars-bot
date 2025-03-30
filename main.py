import os
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Получаем переменные окружения
TOKEN = os.getenv('TOKEN')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')

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

# Основная функция
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("card", card))
    application.run_polling()

if __name__ == '__main__':
    main()