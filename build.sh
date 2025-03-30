#!/usr/bin/env bash
set -e

# Установка системных зависимостей для Chromium
apt-get update
apt-get install -y \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0

# Установка зависимостей Python
pip install -r requirements.txt

# Установка Playwright и браузеров
playwright install --with-deps