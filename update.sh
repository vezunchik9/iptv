#!/bin/bash

# 🎯 ПРОСТАЯ СИСТЕМА ОБНОВЛЕНИЯ IPTV
# ==================================
# 
# Использование:
#   ./update.sh         # Полное обновление
#   ./update.sh check   # Только проверка потоков  
#   ./update.sh parse   # Только парсинг доноров
#   ./update.sh status  # Показать статус

cd "$(dirname "$0")"

echo "🚀 IPTV AUTO SYSTEM"
echo "==================="
echo ""

case "$1" in
    "check")
        echo "🧹 Запуск проверки потоков..."
        python3 auto_system.py --check
        ;;
    "parse") 
        echo "🔄 Запуск парсинга доноров..."
        python3 auto_system.py --parse
        ;;
    "build")
        echo "📺 Сборка плейлистов..."
        python3 auto_system.py --build
        ;;
    "status")
        python3 auto_system.py --status
        ;;
    *)
        echo "🎯 Запуск полного цикла обновления..."
        python3 auto_system.py
        ;;
esac

echo ""
echo "✅ Готово!"
