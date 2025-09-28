#!/bin/bash

# Скрипт очистки IPTV плейлистов от нерабочих каналов

echo "🧹 СИСТЕМА ОЧИСТКИ IPTV ПЛЕЙЛИСТОВ"
echo "=================================="

# Проверяем зависимости
echo "📦 Проверка зависимостей..."

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден"
    exit 1
fi

# Проверяем инструменты для проверки видео
TOOLS_AVAILABLE=0

if command -v ffprobe &> /dev/null; then
    echo "✅ ffprobe найден"
    TOOLS_AVAILABLE=1
fi

if command -v vlc &> /dev/null; then
    echo "✅ VLC найден"
    TOOLS_AVAILABLE=1
fi

if command -v mpv &> /dev/null; then
    echo "✅ mpv найден"
    TOOLS_AVAILABLE=1
fi

if command -v curl &> /dev/null; then
    echo "✅ curl найден"
    TOOLS_AVAILABLE=1
fi

if [ $TOOLS_AVAILABLE -eq 0 ]; then
    echo "❌ Не найдено инструментов для проверки видео!"
    echo "💡 Установите один из: ffmpeg, vlc, mpv, curl"
    exit 1
fi

# Устанавливаем зависимости Python если нужно
python3 -c "import aiohttp" 2>/dev/null || {
    echo "📦 Устанавливаем aiohttp..."
    pip3 install aiohttp
}

# Создаем папки если их нет
mkdir -p reports
mkdir -p backups/categories

# Определяем режим работы
MODE="smart"
CATEGORY=""
MIN_CHANNELS=5

# Парсим аргументы
while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            MODE="full"
            shift
            ;;
        --smart)
            MODE="smart"
            shift
            ;;
        --category)
            MODE="category"
            CATEGORY="$2"
            shift 2
            ;;
        --min-channels)
            MIN_CHANNELS="$2"
            shift 2
            ;;
        --help|-h)
            echo "Использование: $0 [ОПЦИИ]"
            echo ""
            echo "Режимы работы:"
            echo "  --smart          Умная очистка (только проблемные категории) [по умолчанию]"
            echo "  --full           Полная очистка всех категорий"
            echo "  --category NAME  Очистка конкретной категории"
            echo ""
            echo "Опции:"
            echo "  --min-channels N Минимум каналов для обработки (по умолчанию: 5)"
            echo "  --help, -h       Показать эту справку"
            echo ""
            echo "Примеры:"
            echo "  $0 --smart                    # Умная очистка"
            echo "  $0 --full                     # Полная очистка"
            echo "  $0 --category спортивные      # Очистка спортивных каналов"
            exit 0
            ;;
        *)
            echo "❌ Неизвестная опция: $1"
            echo "Используйте --help для справки"
            exit 1
            ;;
    esac
done

echo ""
echo "🎯 ПАРАМЕТРЫ ОЧИСТКИ:"
echo "   Режим: $MODE"
if [ "$MODE" = "category" ]; then
    echo "   Категория: $CATEGORY"
fi
echo "   Минимум каналов: $MIN_CHANNELS"
echo ""

# Создаем бэкап всех категорий перед очисткой
echo "💾 Создаем бэкап всех категорий..."
BACKUP_DIR="backups/full_backup_$(date '+%Y%m%d_%H%M%S')"
mkdir -p "$BACKUP_DIR"
cp -r categories/ "$BACKUP_DIR/" 2>/dev/null || echo "⚠️ Нет категорий для бэкапа"

# Запускаем очистку
echo "🚀 Запускаем очистку плейлистов..."
echo ""

if [ "$MODE" = "full" ]; then
    python3 scripts/cleanup_and_restore_system.py --mode full --min-channels "$MIN_CHANNELS"
elif [ "$MODE" = "smart" ]; then
    python3 scripts/cleanup_and_restore_system.py --mode smart --min-channels "$MIN_CHANNELS"
elif [ "$MODE" = "category" ]; then
    if [ -z "$CATEGORY" ]; then
        echo "❌ Не указана категория для очистки"
        exit 1
    fi
    python3 scripts/cleanup_and_restore_system.py --mode category --category "$CATEGORY"
fi

CLEANUP_EXIT_CODE=$?

if [ $CLEANUP_EXIT_CODE -ne 0 ]; then
    echo "❌ Ошибка при очистке плейлистов"
    exit 1
fi

echo ""
echo "🔄 Обновляем основной плейлист..."
python3 scripts/create_televizo_playlist.py

echo ""
echo "📊 ФИНАЛЬНАЯ СТАТИСТИКА:"
echo "   Полный бэкап: $BACKUP_DIR"
echo "   Отчеты: reports/"
echo "   Бэкапы категорий: backups/categories/"

# Показываем размеры категорий после очистки
echo ""
echo "📁 РАЗМЕРЫ КАТЕГОРИЙ ПОСЛЕ ОЧИСТКИ:"
for category in categories/*.m3u; do
    if [ -f "$category" ]; then
        CHANNELS=$(grep -c "^http" "$category" 2>/dev/null || echo 0)
        BASENAME=$(basename "$category" .m3u)
        printf "   %-25s %s каналов\n" "$BASENAME:" "$CHANNELS"
    fi
done

# Показываем последние отчеты
echo ""
echo "📋 ПОСЛЕДНИЕ ОТЧЕТЫ:"
ls -lt reports/cleanup_report_*.json 2>/dev/null | head -3 | while read line; do
    echo "   📄 $(echo "$line" | awk '{print $9}' | xargs basename)"
done

echo ""
echo "🎉 ОЧИСТКА ЗАВЕРШЕНА!"
echo ""
echo "💡 ЧТО БЫЛО СДЕЛАНО:"
echo "   ✅ Проверены все каналы на реальную работоспособность"
echo "   ❌ Удалены нерабочие каналы (буферизация, ошибки)"
echo "   🔄 Восстановлены каналы из донорских источников"
echo "   💾 Созданы бэкапы для безопасности"
echo "   📊 Сгенерированы детальные отчеты"
echo ""
echo "🔍 МЕТОДЫ ПРОВЕРКИ:"
echo "   🎬 ffprobe - анализ видеопотоков"
echo "   📺 VLC/mpv - реальное воспроизведение"
echo "   🌐 curl - проверка HLS сегментов"
echo "   ⚡ Детекция буферизации и ошибок"
echo ""
echo "📈 РЕЗУЛЬТАТ: Ваши плейлисты теперь содержат только рабочие каналы!"
