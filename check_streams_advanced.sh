#!/bin/bash

# Улучшенный скрипт для проверки работоспособности IPTV потоков
# Использует множественные методы проверки для более точных результатов

echo "🚀 УЛУЧШЕННАЯ ПРОВЕРКА IPTV ПОТОКОВ"
echo "===================================="

# Проверяем зависимости
echo "🔍 Проверка зависимостей..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден"
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo "❌ curl не найден (необходим для улучшенной проверки)"
    exit 1
fi

# Проверяем Python зависимости
echo "📦 Проверка Python зависимостей..."
python3 -c "import aiohttp" 2>/dev/null || {
    echo "📦 Устанавливаем aiohttp..."
    pip3 install aiohttp
}

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
TIMEOUT=15
CONCURRENT=15
RETRY=2
METHODS=""

# Обработка аргументов командной строки
while [[ $# -gt 0 ]]; do
    case $1 in
        --detailed)
            DETAILED=true
            echo "🔬 Включена детальная проверка с ffprobe"
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
        --retry)
            RETRY="$2"
            echo "🔄 Повторных попыток: $RETRY"
            shift 2
            ;;
        --methods)
            METHODS="$2"
            echo "🔧 Методы проверки: $METHODS"
            shift 2
            ;;
        --quick)
            echo "⚡ Быстрая проверка (только HTTP методы)"
            METHODS="http_head http_get"
            TIMEOUT=10
            CONCURRENT=20
            shift
            ;;
        --thorough)
            echo "🔍 Тщательная проверка (все методы)"
            DETAILED=true
            METHODS="http_head http_get curl socket ffprobe"
            TIMEOUT=20
            CONCURRENT=10
            RETRY=3
            shift
            ;;
        --help)
            echo "Использование: $0 [опции]"
            echo ""
            echo "Опции:"
            echo "  --detailed         Детальная проверка с ffprobe"
            echo "  --timeout N        Таймаут в секундах (по умолчанию: 15)"
            echo "  --concurrent N     Количество одновременных проверок (по умолчанию: 15)"
            echo "  --retry N          Количество повторных попыток (по умолчанию: 2)"
            echo "  --methods LIST     Методы проверки через пробел"
            echo "                     Доступные: http_head http_get curl socket ffprobe"
            echo "  --quick           Быстрая проверка (только HTTP методы)"
            echo "  --thorough        Тщательная проверка (все методы)"
            echo "  --help            Показать эту справку"
            echo ""
            echo "Примеры:"
            echo "  $0                        # Стандартная проверка"
            echo "  $0 --quick               # Быстрая проверка"
            echo "  $0 --thorough            # Тщательная проверка"
            echo "  $0 --methods 'curl socket' # Только curl и socket"
            echo "  $0 --detailed --timeout 30 # Детальная проверка с большим таймаутом"
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
REPORT_FILE="reports/advanced_stream_check_${TIMESTAMP}.json"

echo ""
echo "⚙️ ПАРАМЕТРЫ ПРОВЕРКИ:"
echo "   📁 Плейлист: $PLAYLIST_FILE"
echo "   ⏱️ Таймаут: ${TIMEOUT}с"
echo "   🔄 Потоков: $CONCURRENT"
echo "   🔄 Повторов: $RETRY"
echo "   🔬 Детальная: $([ "$DETAILED" = true ] && echo "Да" || echo "Нет")"
echo "   🔧 Методы: $([ -n "$METHODS" ] && echo "$METHODS" || echo "По умолчанию")"
echo "   📊 Отчет: $REPORT_FILE"
echo ""

# Подготавливаем команду
CMD="python3 scripts/advanced_stream_checker.py '$PLAYLIST_FILE' --timeout $TIMEOUT --concurrent $CONCURRENT --retry $RETRY --output '$REPORT_FILE'"

if [ "$DETAILED" = true ]; then
    CMD="$CMD --detailed"
fi

if [ -n "$METHODS" ]; then
    CMD="$CMD --methods $METHODS"
fi

echo "🚀 Запуск улучшенной проверки..."
echo "================================="

# Запускаем проверку
eval $CMD

# Проверяем результат
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Проверка завершена успешно!"
    echo "📊 Отчет сохранен: $REPORT_FILE"
    
    # Показываем детальную статистику если файл существует
    if [ -f "$REPORT_FILE" ]; then
        echo ""
        echo "📈 ДЕТАЛЬНАЯ СТАТИСТИКА:"
        python3 -c "
import json
try:
    with open('$REPORT_FILE', 'r') as f:
        data = json.load(f)
    stats = data.get('statistics', {})
    print(f\"   Всего каналов: {stats.get('total_checked', 0)}\")
    print(f\"   Работающих: {stats.get('working', 0)} ({stats.get('success_rate', 0)}%)\")
    print(f\"   Доступных: {stats.get('accessible', 0)} ({stats.get('accessibility_rate', 0)}%)\")
    print(f\"   Среднее время отклика: {stats.get('avg_response_time', 0)}мс\")
    
    # Статистика по методам
    method_stats = stats.get('method_statistics', {})
    if method_stats:
        print(f\"   \")
        print(f\"   Статистика по методам проверки:\")
        for method, method_stats in method_stats.items():
            total = method_stats.get('total', 0)
            success = method_stats.get('success', 0)
            rate = (success / total * 100) if total > 0 else 0
            print(f\"     {method}: {success}/{total} ({rate:.1f}%)\")
    
except Exception as e:
    print(f\"   Ошибка при чтении статистики: {e}\")
"
    fi
    
    echo ""
    echo "🔍 Для просмотра полного отчета:"
    echo "   cat '$REPORT_FILE' | python3 -m json.tool"
    
    # Предлагаем быстрые действия
    echo ""
    echo "🛠️ ДОСТУПНЫЕ ДЕЙСТВИЯ:"
    echo "   📊 Просмотр отчета: cat '$REPORT_FILE' | python3 -m json.tool"
    echo "   🔍 Поиск неработающих: jq '.results | to_entries[] | select(.value.working == false)' '$REPORT_FILE'"
    echo "   ✅ Поиск работающих: jq '.results | to_entries[] | select(.value.working == true)' '$REPORT_FILE'"
    
else
    echo "❌ Ошибка при проверке потоков"
    exit 1
fi
