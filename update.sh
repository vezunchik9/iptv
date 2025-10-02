#!/bin/bash
# Простое обновление IPTV плейлистов

echo "🚀 ПРОСТОЕ ОБНОВЛЕНИЕ IPTV"
echo "=========================="
echo "📺 Только парсинг и создание плейлистов"
echo "⚡ Без проверки потоков"
echo ""

# Запускаем простую систему
python3 simple_system.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ГОТОВО!"
    echo "📁 Плейлисты в папке playlists/"
    echo "🔗 GitHub: https://github.com/vezunchik9/iptv"
else
    echo ""
    echo "❌ ОШИБКА!"
    exit 1
fi