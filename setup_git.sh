#!/bin/bash

# Скрипт для инициализации Git репозитория и подготовки к публикации на GitHub

echo "🚀 Настройка Git репозитория для IPTV плейлистов"
echo "==============================================="

# Инициализация Git репозитория
if [ ! -d ".git" ]; then
    echo "📁 Инициализация Git репозитория..."
    git init
else
    echo "✅ Git репозиторий уже инициализирован"
fi

# Добавление файлов
echo "📝 Добавление файлов в репозиторий..."
git add .

# Первый коммит
echo "💾 Создание первого коммита..."
git commit -m "🎉 Первоначальная структура IPTV плейлистов для Televizo

- Создана основная структура проекта
- Добавлен основной плейлист televizo_main.m3u
- Организованы категории каналов
- Добавлены скрипты для обработки плейлистов
- Создана документация и README

Категории:
- ИНФО (информационные каналы)
- Эфирные (основные российские каналы)
- Новости
- Спорт
- Музыка
- Кино
- Детские
- Познавательные
- Развлекательные
- Международные
- Региональные

Цель: 1000+ каналов с организацией по категориям"

echo ""
echo "✅ Репозиторий настроен!"
echo ""
echo "🔗 Следующие шаги:"
echo "1. Создайте репозиторий на GitHub"
echo "2. Добавьте remote origin:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/iptv.git"
echo "3. Отправьте код на GitHub:"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "📺 После публикации на GitHub ваш основной плейлист будет доступен по ссылке:"
echo "https://raw.githubusercontent.com/YOUR_USERNAME/iptv/main/playlists/televizo_main.m3u"
echo ""
echo "🎯 Не забудьте:"
echo "- Заменить YOUR_USERNAME на ваш GitHub username в файлах README.md и LINKS.md"
echo "- Сохранить ваш файл 'kanal' с каналами"
echo "- Запустить scripts/create_televizo_playlist.py для обработки каналов"
