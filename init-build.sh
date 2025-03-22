#!/bin/bash

# Логирование
LOG_FILE="cleanup.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Начало очистки: $(date)"

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "Docker не установлен. Установите Docker и повторите попытку."
    exit 1
fi

# Удаление данных certbot
echo "Удаление данных certbot..."
sudo rm -rf data/certbot

# Остановка и удаление всех контейнеров
echo "Остановка и удаление всех контейнеров..."
docker rm -f $(docker ps -a -q)

# Удаление всех Docker-образов
echo "Удаление всех Docker-образов..."
docker rmi $(docker images -q)

# Инициализация Let's Encrypt
echo "Запуск init-letsencrypt.sh..."
./init-letsencrypt.sh

echo "Очистка завершена: $(date)"