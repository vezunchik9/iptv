#!/bin/bash

# Автоматическое обновление плейлистов и пуш в Git

echo "🔄 АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ПЛЕЙЛИСТОВ"
echo "======================================="

# Проверяем зависимости
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "❌ Git не найден"
    exit 1
fi

# Устанавливаем зависимости если нужно
echo "📦 Проверка зависимостей..."
python3 -c "import requests" 2>/dev/null || {
    echo "📦 Устанавливаем requests..."
    pip3 install requests
}

# Создаем бэкап текущих плейлистов
echo "💾 Создаем бэкап..."
BACKUP_DIR="backups/$(date '+%Y%m%d_%H%M%S')"
mkdir -p "$BACKUP_DIR"
cp -r categories/ "$BACKUP_DIR/" 2>/dev/null || echo "⚠️ Нет категорий для бэкапа"

# Запускаем парсер
echo "🔍 Запускаем парсер плейлистов..."
python3 scripts/playlist_parser.py

if [ $? -ne 0 ]; then
    echo "❌ Ошибка при парсинге плейлистов"
    exit 1
fi

# Обновляем основной плейлист
echo "📝 Обновляем основной плейлист..."
python3 scripts/create_televizo_playlist.py

# Проверяем изменения в Git
echo "🔍 Проверяем изменения..."
git add .
CHANGES=$(git diff --cached --name-only)

if [ -z "$CHANGES" ]; then
    echo "ℹ️ Нет изменений для коммита"
    exit 0
fi

echo "📋 Найдены изменения в файлах:"
echo "$CHANGES"

# Создаем коммит
TIMESTAMP=$(date '+%d.%m.%Y %H:%M')
COMMIT_MSG="🔄 Автообновление плейлистов ($TIMESTAMP)

Обновлены категории:
$(echo "$CHANGES" | grep "categories/" | sed 's/categories\///g' | sed 's/\.m3u//g' | sort | uniq | head -10)

Автоматически обновлено парсером плейлистов"

echo "💾 Создаем коммит..."
git commit -m "$COMMIT_MSG"

if [ $? -ne 0 ]; then
    echo "❌ Ошибка при создании коммита"
    exit 1
fi

# Пушим в репозиторий
echo "🚀 Отправляем изменения в репозиторий..."
git push origin main

if [ $? -eq 0 ]; then
    echo "✅ Изменения успешно отправлены!"
    
    # Показываем статистику
    echo ""
    echo "📊 СТАТИСТИКА ОБНОВЛЕНИЯ:"
    echo "   Время: $TIMESTAMP"
    echo "   Измененных файлов: $(echo "$CHANGES" | wc -l)"
    echo "   Категорий обновлено: $(echo "$CHANGES" | grep "categories/" | wc -l)"
    
    # Показываем размеры категорий
    echo ""
    echo "📁 РАЗМЕРЫ КАТЕГОРИЙ:"
    for category in categories/*.m3u; do
        if [ -f "$category" ]; then
            CHANNELS=$(grep -c "^http" "$category" 2>/dev/null || echo 0)
            BASENAME=$(basename "$category" .m3u)
            printf "   %-20s %s каналов\n" "$BASENAME:" "$CHANNELS"
        fi
    done
    
else
    echo "❌ Ошибка при отправке в репозиторий"
    echo "💡 Возможно нужно настроить Git credentials"
    exit 1
fi

echo ""
echo "🎉 АВТООБНОВЛЕНИЕ ЗАВЕРШЕНО!"
