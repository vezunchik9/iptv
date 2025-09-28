#!/bin/bash

# Скрипт для РЕАЛЬНОЙ проверки IPTV потоков через плеер
# Тестирует реальное воспроизведение и буферизацию как в IPTV Checker

echo "🎬 РЕАЛЬНАЯ ПРОВЕРКА IPTV ПОТОКОВ"
echo "================================="

# Проверяем зависимости
echo "🔍 Проверка зависимостей..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден"
    exit 1
fi

# Проверяем наличие плееров
PLAYERS_FOUND=()

if command -v vlc &> /dev/null; then
    PLAYERS_FOUND+=("vlc")
    echo "✅ VLC найден"
else
    echo "⚠️ VLC не найден"
fi

if command -v ffplay &> /dev/null; then
    PLAYERS_FOUND+=("ffplay")
    echo "✅ ffplay найден"
else
    echo "⚠️ ffplay не найден"
fi

if command -v mpv &> /dev/null; then
    PLAYERS_FOUND+=("mpv")
    echo "✅ mpv найден"
else
    echo "⚠️ mpv не найден"
fi

if [ ${#PLAYERS_FOUND[@]} -eq 0 ]; then
    echo "❌ Не найдено ни одного плеера!"
    echo ""
    echo "Установите хотя бы один плеер:"
    echo "  macOS:"
    echo "    brew install vlc"
    echo "    brew install ffmpeg  # для ffplay"
    echo "    brew install mpv"
    echo ""
    echo "  Ubuntu/Debian:"
    echo "    sudo apt install vlc"
    echo "    sudo apt install ffmpeg  # для ffplay"
    echo "    sudo apt install mpv"
    echo ""
    echo "  CentOS/RHEL:"
    echo "    sudo yum install vlc"
    echo "    sudo yum install ffmpeg"
    echo "    sudo yum install mpv"
    exit 1
fi

echo "🎮 Доступные плееры: ${PLAYERS_FOUND[*]}"

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
CONCURRENT=5
TEST_DURATION=15
PLAYER=""

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
        --player)
            PLAYER="$2"
            if [[ " ${PLAYERS_FOUND[*]} " =~ " ${PLAYER} " ]]; then
                echo "🎮 Используем плеер: $PLAYER"
            else
                echo "❌ Плеер $PLAYER не найден. Доступные: ${PLAYERS_FOUND[*]}"
                exit 1
            fi
            shift 2
            ;;
        --quick)
            echo "⚡ Быстрая проверка"
            TIMEOUT=20
            CONCURRENT=10
            TEST_DURATION=10
            shift
            ;;
        --thorough)
            echo "🔍 Тщательная проверка"
            TIMEOUT=60
            CONCURRENT=3
            TEST_DURATION=30
            shift
            ;;
        --help)
            echo "Использование: $0 [опции]"
            echo ""
            echo "Опции:"
            echo "  --timeout N        Таймаут в секундах (по умолчанию: 30)"
            echo "  --concurrent N     Количество одновременных проверок (по умолчанию: 5)"
            echo "  --test-duration N  Длительность теста каждого потока (по умолчанию: 15)"
            echo "  --player NAME      Конкретный плеер (vlc, ffplay, mpv)"
            echo "  --quick           Быстрая проверка (20с таймаут, 10с тест)"
            echo "  --thorough        Тщательная проверка (60с таймаут, 30с тест)"
            echo "  --help            Показать эту справку"
            echo ""
            echo "Примеры:"
            echo "  $0                        # Стандартная реальная проверка"
            echo "  $0 --quick               # Быстрая проверка"
            echo "  $0 --thorough            # Тщательная проверка"
            echo "  $0 --player ffplay       # Только через ffplay"
            echo "  $0 --test-duration 20    # Тест по 20 секунд"
            echo ""
            echo "ВНИМАНИЕ: Реальная проверка занимает больше времени,"
            echo "но дает точные результаты как в IPTV Checker!"
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
REPORT_FILE="reports/real_stream_check_${TIMESTAMP}.json"

echo ""
echo "⚙️ ПАРАМЕТРЫ РЕАЛЬНОЙ ПРОВЕРКИ:"
echo "   📁 Плейлист: $PLAYLIST_FILE"
echo "   ⏱️ Таймаут: ${TIMEOUT}с"
echo "   🔄 Потоков: $CONCURRENT"
echo "   🎬 Тест потока: ${TEST_DURATION}с"
echo "   🎮 Плеер: $([ -n "$PLAYER" ] && echo "$PLAYER" || echo "Авто-выбор")"
echo "   📊 Отчет: $REPORT_FILE"
echo ""

# Подготавливаем команду
CMD="python3 scripts/real_stream_checker.py '$PLAYLIST_FILE' --timeout $TIMEOUT --concurrent $CONCURRENT --test-duration $TEST_DURATION --output '$REPORT_FILE'"

if [ -n "$PLAYER" ]; then
    CMD="$CMD --player $PLAYER"
fi

echo "🎬 Запуск РЕАЛЬНОЙ проверки потоков..."
echo "======================================"
echo "⚠️  ВНИМАНИЕ: Это может занять много времени!"
echo "   Каждый поток тестируется ${TEST_DURATION} секунд"
echo "   Всего потоков: $(wc -l < "$PLAYLIST_FILE" | grep -o '[0-9]*' | head -1)"
echo ""

# Подтверждение пользователя
read -p "Продолжить? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Проверка отменена"
    exit 0
fi

# Запускаем проверку
eval $CMD

# Проверяем результат
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Реальная проверка завершена успешно!"
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
    print(f\"   Среднее время ответа: {stats.get('avg_response_time', 0)}мс\")
    print(f\"   Средние события буферизации: {stats.get('avg_buffering_events', 0)}\")
    
    # Статистика по плеерам
    player_stats = stats.get('player_statistics', {})
    if player_stats:
        print(f\"   \")
        print(f\"   Статистика по плеерам:\")
        for player, player_stats in player_stats.items():
            total = player_stats.get('total', 0)
            working = player_stats.get('working', 0)
            rate = (working / total * 100) if total > 0 else 0
            print(f\"     {player}: {working}/{total} ({rate:.1f}%)\")
    
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
    echo "   🎬 Анализ буферизации: jq '.results | to_entries[] | select(.value.details.buffering_events > 0)' '$REPORT_FILE'"
    
else
    echo "❌ Ошибка при реальной проверке потоков"
    exit 1
fi
