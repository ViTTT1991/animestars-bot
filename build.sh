#!/usr/bin/env bash
set -e

# Установка зависимостей Python
pip install -r requirements.txt

# Установка Playwright и браузеров
playwright install --with-deps