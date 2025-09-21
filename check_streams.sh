#!/bin/bash

# Скрипт для проверки работоспособности IPTV потоков

echo "🔍 Проверка работоспособности IPTV потоков"
echo "==========================================="

# Проверяем зависимости
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден"
    exit 1
fi

if ! python3 -c "import aiohttp" 2>/dev/null; then
    echo "📦 Устанавливаем зависимости..."
    pip3 install aiohttp asyncio
fi

# Определяем файл плейлиста
PLAYLIST_FILE="playlists/televizo_main.m3u"

if [ ! -f "$PLAYLIST_FILE" ]; then
    echo "❌ Файл плейлиста не найден: $PLAYLIST_FILE"
    exit 1
fi

# Создаем папку для отчетов
mkdir -p reports

# Параметры по умолчанию
DETAILED=false
TIMEOUT=10
CONCURRENT=20

# Обработка аргументов командной строки
while [[ $# -gt 0 ]]; do
    case $1 in
        --detailed)
            DETAILED=true
            echo "🔬 Включена детальная проверка (медленнее)"
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            echo "⏱️ Таймаут: ${TIMEOUT}с"
            shift 2
            ;;
        --concurrent)
            CONCURRENT="$2"
            echo "🔄 Одновременных проверок: $CONCURRENT"
            shift 2
            ;;
        --help)
            echo "Использование: $0 [опции]"
            echo ""
            echo "Опции:"
            echo "  --detailed       Детальная проверка с ffprobe"
            echo "  --timeout N      Таймаут в секундах (по умолчанию: 10)"
            echo "  --concurrent N   Количество одновременных проверок (по умолчанию: 20)"
            echo "  --help          Показать эту справку"
            echo ""
            echo "Примеры:"
            echo "  $0                    # Быстрая проверка"
            echo "  $0 --detailed         # Детальная проверка"
            echo "  $0 --timeout 5        # Быстрая проверка с таймаутом 5с"
            echo "  $0 --detailed --concurrent 10  # Детальная проверка, 10 потоков"
            exit 0
            ;;
        *)
            echo "❌ Неизвестный параметр: $1"
            echo "Используйте --help для справки"
            exit 1
            ;;
    esac
done

# Генерируем имя файла отчета
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
REPORT_FILE="reports/stream_check_${TIMESTAMP}.json"

echo ""
echo "⚙️ Параметры проверки:"
echo "   📁 Плейлист: $PLAYLIST_FILE"
echo "   ⏱️ Таймаут: ${TIMEOUT}с"
echo "   🔄 Потоков: $CONCURRENT"
echo "   🔬 Детальная: $([ "$DETAILED" = true ] && echo "Да" || echo "Нет")"
echo "   📊 Отчет: $REPORT_FILE"
echo ""

# Подготавливаем команду
CMD="python3 scripts/stream_checker.py '$PLAYLIST_FILE' --timeout $TIMEOUT --concurrent $CONCURRENT --output '$REPORT_FILE'"

if [ "$DETAILED" = true ]; then
    CMD="$CMD --detailed"
fi

echo "🚀 Запуск проверки..."
echo "========================"

# Запускаем проверку
eval $CMD

# Проверяем результат
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Проверка завершена успешно!"
    echo "📊 Отчет сохранен: $REPORT_FILE"
    
    # Показываем краткую статистику если файл существует
    if [ -f "$REPORT_FILE" ]; then
        echo ""
        echo "📈 Краткая статистика:"
        python3 -c "
import json
try:
    with open('$REPORT_FILE', 'r') as f:
        data = json.load(f)
    stats = data.get('statistics', {})
    print(f\"   Всего каналов: {stats.get('total_checked', 0)}\")
    print(f\"   Работающих: {stats.get('working', 0)} ({stats.get('success_rate', 0)}%)\")
    print(f\"   Среднее время отклика: {stats.get('avg_response_time', 0)}мс\")
except:
    pass
"
    fi
    
    echo ""
    echo "🔍 Для просмотра полного отчета:"
    echo "   cat '$REPORT_FILE' | python3 -m json.tool"
    
else
    echo "❌ Ошибка при проверке потоков"
    exit 1
fi
