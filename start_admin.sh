#!/bin/bash

# Скрипт быстрого запуска веб-админки IPTV

echo "🚀 Запуск веб-админки IPTV"
echo "=========================="

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.7+"
    exit 1
fi

# Проверяем зависимости
echo "🔍 Проверка зависимостей..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Устанавливаем зависимости..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка установки зависимостей"
        echo "Попробуйте: pip3 install flask aiohttp"
        exit 1
    fi
fi

# Проверяем ffmpeg (опционально)
if command -v ffprobe &> /dev/null; then
    echo "✅ ffprobe найден - детальная проверка потоков доступна"
else
    echo "⚠️ ffprobe не найден - только базовая проверка потоков"
    echo "Для полной функциональности установите: brew install ffmpeg"
fi

# Создаем необходимые папки
echo "📁 Создание рабочих папок..."
mkdir -p reports
mkdir -p backups

# Проверяем наличие плейлиста
if [ ! -f "playlists/televizo_main.m3u" ]; then
    echo "⚠️ Основной плейлист не найден"
    echo "Убедитесь что файл playlists/televizo_main.m3u существует"
fi

# Определяем IP адрес
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)

echo ""
echo "🌐 Запуск веб-сервера..."
echo "========================"
echo "📊 Адреса для доступа:"
echo "   Локально:    http://localhost:5000"
if [ -n "$LOCAL_IP" ]; then
    echo "   В сети:      http://$LOCAL_IP:5000"
fi
echo ""
echo "🔧 Функции:"
echo "   ✅ Редактирование каналов"
echo "   ✅ Массовые операции"
echo "   ✅ Проверка потоков"
echo "   ✅ Автосохранение в GitHub"
echo ""
echo "⏹️ Для остановки нажмите Ctrl+C"
echo ""

# Переходим в папку web и запускаем приложение
cd web

# Запуск с обработкой ошибок
python3 app.py 2>&1 | while IFS= read -r line; do
    # Добавляем timestamp к логам
    echo "[$(date '+%H:%M:%S')] $line"
done
