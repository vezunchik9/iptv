#!/bin/bash
# IPTV System - обновление плейлиста

echo "🚀 IPTV SYSTEM"
echo "=============="
echo "📺 Парсинг доноров и создание плейлиста"
echo ""

# Запускаем систему
python3 iptv_system.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ГОТОВО!"
    echo "📁 Плейлист: playlists/televizo.m3u"
    echo "🔗 GitHub: https://github.com/vezunchik9/iptv"
else
    echo ""
    echo "❌ ОШИБКА!"
    exit 1
fi