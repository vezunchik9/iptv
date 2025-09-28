#!/bin/bash

# Интерактивная проверка IPTV потоков с визуальной обратной связью

echo "🎬 ИНТЕРАКТИВНАЯ ПРОВЕРКА IPTV ПОТОКОВ"
echo "======================================"

# Проверяем зависимости
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден"
    exit 1
fi

# Проверяем VLC на Mac
VLC_FOUND=false
if [ -f "/Applications/VLC.app/Contents/MacOS/VLC" ]; then
    echo "✅ VLC найден в Applications"
    VLC_FOUND=true
elif command -v vlc &> /dev/null; then
    echo "✅ VLC найден в PATH"
    VLC_FOUND=true
else
    echo "⚠️ VLC не найден, будет использован curl"
fi

if command -v curl &> /dev/null; then
    echo "✅ curl найден"
else
    echo "❌ curl не найден"
    exit 1
fi

# Показываем доступные категории
echo ""
echo "📁 ДОСТУПНЫЕ КАТЕГОРИИ:"
ls -1 categories/*.m3u | sed 's/categories\///g' | sed 's/\.m3u//g' | nl

echo ""
echo "Выберите категорию для проверки:"
read -p "Введите номер или имя файла: " CHOICE

# Определяем файл для проверки
if [[ "$CHOICE" =~ ^[0-9]+$ ]]; then
    # Если введен номер
    CATEGORY_FILE=$(ls -1 categories/*.m3u | sed -n "${CHOICE}p")
else
    # Если введено имя
    if [[ "$CHOICE" == *.m3u ]]; then
        CATEGORY_FILE="categories/$CHOICE"
    else
        CATEGORY_FILE="categories/${CHOICE}.m3u"
    fi
fi

if [ ! -f "$CATEGORY_FILE" ]; then
    echo "❌ Файл не найден: $CATEGORY_FILE"
    exit 1
fi

echo "📺 Выбрана категория: $CATEGORY_FILE"

# Показываем количество каналов
TOTAL_CHANNELS=$(grep -c "^http" "$CATEGORY_FILE" 2>/dev/null || echo 0)
echo "📊 Всего каналов в категории: $TOTAL_CHANNELS"

# Настройки проверки
echo ""
echo "⚙️ НАСТРОЙКИ ПРОВЕРКИ:"
echo "1. Быстрая проверка (5с на канал, без плеера)"
echo "2. Стандартная проверка (10с на канал)" 
echo "3. Тщательная проверка (15с на канал)"
if [ "$VLC_FOUND" = true ]; then
    echo "4. Демонстрация с плеером (10с на канал, показывает VLC)"
fi

read -p "Выберите режим (1-4): " MODE

case $MODE in
    1)
        TEST_DURATION=5
        SHOW_PLAYER=""
        VISUAL=""
        echo "⚡ Быстрая проверка"
        ;;
    2)
        TEST_DURATION=10
        SHOW_PLAYER=""
        VISUAL=""
        echo "🔍 Стандартная проверка"
        ;;
    3)
        TEST_DURATION=15
        SHOW_PLAYER=""
        VISUAL="--visual"
        echo "🔬 Тщательная проверка"
        ;;
    4)
        if [ "$VLC_FOUND" = true ]; then
            TEST_DURATION=10
            SHOW_PLAYER="--show-player"
            VISUAL="--visual"
            echo "🎬 Демонстрация с плеером"
        else
            echo "❌ VLC не найден, используем стандартную проверку"
            TEST_DURATION=10
            SHOW_PLAYER=""
            VISUAL=""
        fi
        ;;
    *)
        echo "❌ Неверный выбор, используем стандартную проверку"
        TEST_DURATION=10
        SHOW_PLAYER=""
        VISUAL=""
        ;;
esac

# Ограничение количества каналов
echo ""
if [ $TOTAL_CHANNELS -gt 10 ]; then
    echo "⚠️ В категории много каналов ($TOTAL_CHANNELS)"
    read -p "Сколько каналов проверить? (Enter = все): " MAX_CHANNELS
    if [[ "$MAX_CHANNELS" =~ ^[0-9]+$ ]] && [ $MAX_CHANNELS -gt 0 ]; then
        MAX_CHANNELS_ARG="--max-channels $MAX_CHANNELS"
        echo "📋 Будет проверено: $MAX_CHANNELS каналов"
    else
        MAX_CHANNELS_ARG=""
        echo "📋 Будут проверены все каналы"
    fi
else
    MAX_CHANNELS_ARG=""
    echo "📋 Будут проверены все каналы"
fi

# Создаем папку для отчетов
mkdir -p reports

# Подготавливаем команду
CMD="python3 scripts/interactive_stream_checker.py '$CATEGORY_FILE' --test-duration $TEST_DURATION $VISUAL $SHOW_PLAYER $MAX_CHANNELS_ARG"

echo ""
echo "🚀 ЗАПУСК ИНТЕРАКТИВНОЙ ПРОВЕРКИ"
echo "================================"
echo "📁 Файл: $CATEGORY_FILE"
echo "⏱️ Тест: ${TEST_DURATION}с на канал"
echo "🎮 Плеер: $([ -n "$SHOW_PLAYER" ] && echo "Показывать" || echo "Скрытый режим")"
echo ""

# Запускаем проверку
eval $CMD

echo ""
echo "✅ Интерактивная проверка завершена!"

# Показываем отчеты
LATEST_REPORT=$(ls -t interactive_check_report_*.json 2>/dev/null | head -1)
if [ -f "$LATEST_REPORT" ]; then
    echo "📊 Отчет сохранен: $LATEST_REPORT"
    
    # Показываем краткую статистику
    echo ""
    echo "📈 КРАТКАЯ СТАТИСТИКА:"
    python3 -c "
import json
try:
    with open('$LATEST_REPORT', 'r') as f:
        data = json.load(f)
    results = data.get('results', {})
    total = len(results)
    working = sum(1 for r in results.values() if r.get('working', False))
    print(f'   Всего проверено: {total}')
    print(f'   Работающих: {working} ({working/total*100:.1f}%)') if total > 0 else print('   Работающих: 0')
    
    # Показываем первые несколько результатов
    print(f'   ')
    print(f'   Детали:')
    for i, (channel_id, result) in enumerate(list(results.items())[:5]):
        status = '✅' if result.get('working') else '❌'
        name = result.get('channel_name', 'Unknown')[:30]
        print(f'     {status} {name}')
    
    if len(results) > 5:
        print(f'     ... и еще {len(results) - 5} каналов')
        
except Exception as e:
    print(f'   Ошибка при чтении отчета: {e}')
"
fi
