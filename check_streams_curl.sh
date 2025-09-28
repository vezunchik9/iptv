#!/bin/bash

# Скрипт для УЛУЧШЕННОЙ проверки IPTV потоков через curl
# Анализирует реальную скорость загрузки и стабильность потоков

echo "🌐 УЛУЧШЕННАЯ ПРОВЕРКА IPTV ПОТОКОВ (CURL)"
echo "==========================================="

# Проверяем зависимости
echo "🔍 Проверка зависимостей..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден"
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo "❌ curl не найден (необходим для проверки)"
    exit 1
fi

echo "✅ curl найден: $(curl --version | head -1)"

# Определяем файл плейлиста
PLAYLIST_FILE="playlists/televizo_main.m3u"

if [ ! -f "$PLAYLIST_FILE" ]; then
    echo "❌ Файл плейлиста не найден: $PLAYLIST_FILE"
    exit 1
fi

# Создаем папку для отчетов
mkdir -p reports

# Параметры по умолчанию
TIMEOUT=30
CONCURRENT=10
TEST_DURATION=15

# Обработка аргументов командной строки
while [[ $# -gt 0 ]]; do
    case $1 in
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
        --test-duration)
            TEST_DURATION="$2"
            echo "🎬 Длительность теста: ${TEST_DURATION}с"
            shift 2
            ;;
        --quick)
            echo "⚡ Быстрая проверка"
            TIMEOUT=20
            CONCURRENT=15
            TEST_DURATION=10
            shift
            ;;
        --thorough)
            echo "🔍 Тщательная проверка"
            TIMEOUT=45
            CONCURRENT=5
            TEST_DURATION=20
            shift
            ;;
        --help)
            echo "Использование: $0 [опции]"
            echo ""
            echo "Опции:"
            echo "  --timeout N        Таймаут в секундах (по умолчанию: 30)"
            echo "  --concurrent N     Количество одновременных проверок (по умолчанию: 10)"
            echo "  --test-duration N  Длительность теста каждого потока (по умолчанию: 15)"
            echo "  --quick           Быстрая проверка (20с таймаут, 10с тест)"
            echo "  --thorough        Тщательная проверка (45с таймаут, 20с тест)"
            echo "  --help            Показать эту справку"
            echo ""
            echo "Примеры:"
            echo "  $0                        # Стандартная проверка"
            echo "  $0 --quick               # Быстрая проверка"
            echo "  $0 --thorough            # Тщательная проверка"
            echo "  $0 --test-duration 20    # Тест по 20 секунд"
            echo ""
            echo "ОСОБЕННОСТИ:"
            echo "  - Анализирует реальную скорость загрузки"
            echo "  - Проверяет HLS сегменты для .m3u8 потоков"
            echo "  - Оценивает качество потока (0-100 баллов)"
            echo "  - Выявляет проблемы со скоростью и соединением"
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
REPORT_FILE="reports/curl_stream_check_${TIMESTAMP}.json"

echo ""
echo "⚙️ ПАРАМЕТРЫ УЛУЧШЕННОЙ ПРОВЕРКИ:"
echo "   📁 Плейлист: $PLAYLIST_FILE"
echo "   ⏱️ Таймаут: ${TIMEOUT}с"
echo "   🔄 Потоков: $CONCURRENT"
echo "   🎬 Тест потока: ${TEST_DURATION}с"
echo "   📊 Отчет: $REPORT_FILE"
echo ""

# Подготавливаем команду
CMD="python3 scripts/curl_stream_checker.py '$PLAYLIST_FILE' --timeout $TIMEOUT --concurrent $CONCURRENT --test-duration $TEST_DURATION --output '$REPORT_FILE'"

echo "🌐 Запуск улучшенной проверки через curl..."
echo "============================================"

# Запускаем проверку
eval $CMD

# Проверяем результат
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Улучшенная проверка завершена успешно!"
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
    print(f\"   Среднее время отклика: {stats.get('avg_response_time', 0)}мс\")
    print(f\"   Средний балл качества: {stats.get('avg_quality_score', 0)}\")
    print(f\"   HLS потоков: {stats.get('hls_streams', 0)}\")
    print(f\"   Проблемы со скоростью: {stats.get('speed_issues', 0)}\")
    print(f\"   Проблемы с соединением: {stats.get('connection_issues', 0)}\")
    
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
    echo "   🏆 Лучшие потоки: jq '.results | to_entries[] | select(.value.quality_score >= 80)' '$REPORT_FILE'"
    echo "   🐌 Медленные потоки: jq '.results | to_entries[] | select(.value.details.speed_download < 50000)' '$REPORT_FILE'"
    echo "   📺 HLS потоки: jq '.results | to_entries[] | select(.value.url | contains(\"m3u8\"))' '$REPORT_FILE'"
    
else
    echo "❌ Ошибка при улучшенной проверке потоков"
    exit 1
fi
