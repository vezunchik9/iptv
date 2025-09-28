#!/bin/bash

# Умная система очистки IPTV плейлистов с правильной логикой:
# 1. Обновляем из доноров (свежие ссылки)
# 2. Проверяем ВСЕ каналы (включая новые)
# 3. Удаляем нерабочие
# 4. Автопуш в Git

echo "🤖 УМНАЯ СИСТЕМА ОЧИСТКИ IPTV ПЛЕЙЛИСТОВ"
echo "========================================"

# Проверяем зависимости
echo "📦 Проверка системы..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "❌ Git не найден"
    exit 1
fi

# Проверяем инструменты для видео
TOOLS_COUNT=0
for tool in ffprobe vlc mpv curl; do
    if command -v $tool &> /dev/null; then
        echo "✅ $tool доступен"
        TOOLS_COUNT=$((TOOLS_COUNT + 1))
    fi
done

if [ $TOOLS_COUNT -eq 0 ]; then
    echo "❌ Не найдено инструментов для проверки видео!"
    echo "💡 Установите: ffmpeg, vlc, mpv или curl"
    exit 1
fi

echo "✅ Найдено $TOOLS_COUNT инструментов для проверки видео"

# Устанавливаем Python зависимости
python3 -c "import requests, aiohttp" 2>/dev/null || {
    echo "📦 Устанавливаем Python зависимости..."
    pip3 install requests aiohttp
}

# Создаем необходимые папки
mkdir -p reports backups/full_backups

# Определяем режим работы
DRY_RUN=false
CONFIG="donors_config.json"

# Парсим аргументы
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --config)
            CONFIG="$2"
            shift 2
            ;;
        --help|-h)
            echo "Использование: $0 [ОПЦИИ]"
            echo ""
            echo "Умная очистка с правильной логикой:"
            echo "  1. 🔄 Обновление из донорских источников"
            echo "  2. 🎬 Реальная проверка всех видеопотоков"
            echo "  3. 🧹 Удаление нерабочих каналов"
            echo "  4. 🚀 Автоматический Git push"
            echo ""
            echo "Опции:"
            echo "  --dry-run        Тестовый запуск без изменений"
            echo "  --config FILE    Файл конфигурации (по умолчанию: donors_config.json)"
            echo "  --help, -h       Показать эту справку"
            echo ""
            echo "Примеры:"
            echo "  $0                    # Полная умная очистка"
            echo "  $0 --dry-run          # Тестовый запуск"
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
echo "🎯 ПАРАМЕТРЫ ЗАПУСКА:"
echo "   Конфигурация: $CONFIG"
echo "   Тестовый режим: $([ "$DRY_RUN" = true ] && echo "ДА" || echo "НЕТ")"
echo ""

# Проверяем Git статус
echo "📋 Проверка Git статуса..."
git status --porcelain > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Не Git репозиторий или ошибка Git"
    exit 1
fi

# Показываем текущие изменения
UNCOMMITTED=$(git status --porcelain | wc -l)
if [ $UNCOMMITTED -gt 0 ]; then
    echo "⚠️ Есть незакоммиченные изменения: $UNCOMMITTED файлов"
    echo "💡 Они будут включены в итоговый коммит"
fi

echo ""
echo "🚀 ЗАПУСК УМНОЙ ОЧИСТКИ..."
echo ""

# Показываем логику работы
echo "📋 ЛОГИКА РАБОТЫ:"
echo "   1️⃣ Обновляем плейлисты из донорских источников"
echo "   2️⃣ Проверяем ВСЕ каналы на реальную работоспособность"
echo "   3️⃣ Удаляем нерабочие каналы"
echo "   4️⃣ Обновляем основной плейлист"
echo "   5️⃣ Автоматически коммитим и пушим в Git"
echo ""

# Запускаем умную систему
if [ "$DRY_RUN" = true ]; then
    python3 scripts/smart_cleanup_system.py --config "$CONFIG" --dry-run
else
    python3 scripts/smart_cleanup_system.py --config "$CONFIG"
fi

CLEANUP_EXIT_CODE=$?

if [ $CLEANUP_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ ОШИБКА ПРИ ВЫПОЛНЕНИИ УМНОЙ ОЧИСТКИ"
    echo ""
    echo "🔍 Возможные причины:"
    echo "   • Проблемы с сетью при загрузке донорских плейлистов"
    echo "   • Ошибки при проверке видеопотоков"
    echo "   • Проблемы с Git (нет прав на push)"
    echo "   • Недостаточно места на диске"
    echo ""
    echo "💡 Проверьте логи выше для деталей"
    exit 1
fi

echo ""
echo "🎉 УМНАЯ ОЧИСТКА УСПЕШНО ЗАВЕРШЕНА!"
echo ""
echo "✨ ЧТО БЫЛО СДЕЛАНО:"
echo "   🔄 Плейлисты обновлены из свежих донорских источников"
echo "   🎬 Все каналы проверены на реальную работоспособность"
echo "   🧹 Нерабочие каналы удалены"
echo "   📝 Основной плейлист обновлен"
echo "   🚀 Изменения автоматически отправлены в Git"
echo "   💾 Созданы полные бэкапы для безопасности"
echo ""
echo "🎯 РЕЗУЛЬТАТ: Ваши плейлисты теперь содержат только рабочие каналы"
echo "              с самыми свежими ссылками из донорских источников!"
echo ""

# Показываем финальный Git статус
echo "📊 ФИНАЛЬНЫЙ СТАТУС:"
TOTAL_CHANNELS=0
for category in categories/*.m3u; do
    if [ -f "$category" ]; then
        CHANNELS=$(grep -c "^http" "$category" 2>/dev/null || echo 0)
        TOTAL_CHANNELS=$((TOTAL_CHANNELS + CHANNELS))
    fi
done

echo "   📺 Всего рабочих каналов: $TOTAL_CHANNELS"
echo "   📁 Категорий: $(ls categories/*.m3u 2>/dev/null | wc -l)"

# Показываем последний коммит
echo ""
echo "📋 ПОСЛЕДНИЙ КОММИТ:"
git log --oneline -1 | sed 's/^/   /'

echo ""
echo "🎊 Готово! Наслаждайтесь качественными IPTV плейлистами!"
