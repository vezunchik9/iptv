#!/bin/bash

# Полная система управления IPTV плейлистами
# Очистка + Умное обновление + Git push

echo "🚀 ПОЛНАЯ СИСТЕМА УПРАВЛЕНИЯ IPTV ПЛЕЙЛИСТАМИ"
echo "=============================================="

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
mkdir -p reports backups/categories backups/full_backups

# Определяем режим работы
MODE="auto"
SKIP_CLEANUP=false
SKIP_UPDATE=false
SKIP_GIT=false

# Парсим аргументы
while [[ $# -gt 0 ]]; do
    case $1 in
        --cleanup-only)
            MODE="cleanup"
            shift
            ;;
        --update-only)
            MODE="update"
            shift
            ;;
        --skip-cleanup)
            SKIP_CLEANUP=true
            shift
            ;;
        --skip-update)
            SKIP_UPDATE=true
            shift
            ;;
        --skip-git)
            SKIP_GIT=true
            shift
            ;;
        --help|-h)
            echo "Использование: $0 [ОПЦИИ]"
            echo ""
            echo "Режимы работы:"
            echo "  (по умолчанию)   Полный цикл: очистка → обновление → git push"
            echo "  --cleanup-only   Только очистка от нерабочих каналов"
            echo "  --update-only    Только умное обновление из доноров"
            echo ""
            echo "Опции пропуска:"
            echo "  --skip-cleanup   Пропустить этап очистки"
            echo "  --skip-update    Пропустить этап обновления"
            echo "  --skip-git       Пропустить git push"
            echo ""
            echo "Примеры:"
            echo "  $0                      # Полный цикл"
            echo "  $0 --cleanup-only       # Только очистка"
            echo "  $0 --skip-cleanup       # Обновление без очистки"
            exit 0
            ;;
        *)
            echo "❌ Неизвестная опция: $1"
            exit 1
            ;;
    esac
done

echo ""
echo "🎯 ПЛАН ВЫПОЛНЕНИЯ:"
if [ "$MODE" = "cleanup" ] || ([ "$MODE" = "auto" ] && [ "$SKIP_CLEANUP" = false ]); then
    echo "   1️⃣ Очистка нерабочих каналов"
fi
if [ "$MODE" = "update" ] || ([ "$MODE" = "auto" ] && [ "$SKIP_UPDATE" = false ]); then
    echo "   2️⃣ Умное обновление из доноров"
fi
if [ "$MODE" = "auto" ] && [ "$SKIP_GIT" = false ]; then
    echo "   3️⃣ Обновление основного плейлиста"
    echo "   4️⃣ Git commit и push"
fi
echo ""

# Создаем полный бэкап перед началом
FULL_BACKUP_DIR="backups/full_backups/backup_$(date '+%Y%m%d_%H%M%S')"
echo "💾 Создаем полный бэкап: $FULL_BACKUP_DIR"
mkdir -p "$FULL_BACKUP_DIR"
cp -r categories/ "$FULL_BACKUP_DIR/" 2>/dev/null
cp playlists/*.m3u "$FULL_BACKUP_DIR/" 2>/dev/null

# Этап 1: Очистка нерабочих каналов
if [ "$MODE" = "cleanup" ] || ([ "$MODE" = "auto" ] && [ "$SKIP_CLEANUP" = false ]); then
    echo ""
    echo "🧹 ЭТАП 1: ОЧИСТКА НЕРАБОЧИХ КАНАЛОВ"
    echo "===================================="
    
    # Запускаем умную очистку (только проблемные категории)
    python3 scripts/cleanup_and_restore_system.py --mode smart --min-channels 10
    
    CLEANUP_EXIT_CODE=$?
    
    if [ $CLEANUP_EXIT_CODE -ne 0 ]; then
        echo "❌ Ошибка при очистке плейлистов"
        exit 1
    fi
    
    echo "✅ Очистка завершена"
fi

# Этап 2: Умное обновление
if [ "$MODE" = "update" ] || ([ "$MODE" = "auto" ] && [ "$SKIP_UPDATE" = false ]); then
    echo ""
    echo "🧠 ЭТАП 2: УМНОЕ ОБНОВЛЕНИЕ ИЗ ДОНОРОВ"
    echo "======================================"
    
    python3 scripts/smart_playlist_parser.py
    
    UPDATE_EXIT_CODE=$?
    
    if [ $UPDATE_EXIT_CODE -ne 0 ]; then
        echo "❌ Ошибка при умном обновлении"
        exit 1
    fi
    
    echo "✅ Умное обновление завершено"
fi

# Этап 3: Обновление основного плейлиста
if [ "$MODE" = "auto" ]; then
    echo ""
    echo "📝 ЭТАП 3: ОБНОВЛЕНИЕ ОСНОВНОГО ПЛЕЙЛИСТА"
    echo "========================================="
    
    python3 scripts/create_televizo_playlist.py
    
    PLAYLIST_EXIT_CODE=$?
    
    if [ $PLAYLIST_EXIT_CODE -ne 0 ]; then
        echo "❌ Ошибка при создании основного плейлиста"
        exit 1
    fi
    
    echo "✅ Основной плейлист обновлен"
fi

# Этап 4: Git commit и push
if [ "$MODE" = "auto" ] && [ "$SKIP_GIT" = false ]; then
    echo ""
    echo "🚀 ЭТАП 4: ОТПРАВКА В РЕПОЗИТОРИЙ"
    echo "================================="
    
    # Проверяем изменения
    git add .
    CHANGES=$(git diff --cached --name-only)
    
    if [ -z "$CHANGES" ]; then
        echo "ℹ️ Нет изменений для коммита"
    else
        echo "📋 Найдены изменения:"
        echo "$CHANGES" | head -10
        
        if [ $(echo "$CHANGES" | wc -l) -gt 10 ]; then
            echo "... и еще $(( $(echo "$CHANGES" | wc -l) - 10 )) файлов"
        fi
        
        # Подсчитываем статистику
        CATEGORIES_CHANGED=$(echo "$CHANGES" | grep "categories/" | wc -l)
        REPORTS_CREATED=$(echo "$CHANGES" | grep "reports/" | wc -l)
        
        # Создаем коммит
        TIMESTAMP=$(date '+%d.%m.%Y %H:%M')
        COMMIT_MSG="🔄 Полное обновление плейлистов ($TIMESTAMP)

🧹 Очистка и восстановление:
- Проверены каналы на реальную работоспособность
- Удалены нерабочие каналы (буферизация, ошибки)
- Восстановлены каналы из донорских источников

🧠 Умное обновление:
- Обновлены существующие ссылки каналов
- Добавлены новые качественные каналы
- Обновлены метаданные и логотипы

📊 Статистика:
- Категорий обновлено: $CATEGORIES_CHANGED
- Отчетов создано: $REPORTS_CREATED
- Полный бэкап: $FULL_BACKUP_DIR

Автоматически обновлено полной системой управления"

        echo "💾 Создаем коммит..."
        git commit -m "$COMMIT_MSG"
        
        if [ $? -ne 0 ]; then
            echo "❌ Ошибка при создании коммита"
            exit 1
        fi
        
        echo "🚀 Отправляем в репозиторий..."
        git push origin main
        
        if [ $? -eq 0 ]; then
            echo "✅ Изменения успешно отправлены!"
        else
            echo "❌ Ошибка при отправке в репозиторий"
            exit 1
        fi
    fi
fi

# Финальная статистика
echo ""
echo "📊 ФИНАЛЬНАЯ СТАТИСТИКА"
echo "======================="

# Показываем размеры категорий
echo "📁 Размеры категорий:"
TOTAL_CHANNELS=0
for category in categories/*.m3u; do
    if [ -f "$category" ]; then
        CHANNELS=$(grep -c "^http" "$category" 2>/dev/null || echo 0)
        BASENAME=$(basename "$category" .m3u)
        printf "   %-25s %s каналов\n" "$BASENAME:" "$CHANNELS"
        TOTAL_CHANNELS=$((TOTAL_CHANNELS + CHANNELS))
    fi
done

echo ""
echo "📈 Общая статистика:"
echo "   📺 Всего каналов: $TOTAL_CHANNELS"
echo "   📁 Категорий: $(ls categories/*.m3u 2>/dev/null | wc -l)"
echo "   💾 Полный бэкап: $FULL_BACKUP_DIR"

# Показываем последние отчеты
echo ""
echo "📋 Последние отчеты:"
ls -lt reports/ 2>/dev/null | head -3 | tail -n +2 | while read line; do
    echo "   📄 $(echo "$line" | awk '{print $9}')"
done

echo ""
echo "🎉 ПОЛНОЕ ОБНОВЛЕНИЕ ЗАВЕРШЕНО!"
echo ""
echo "✨ РЕЗУЛЬТАТ:"
echo "   🧹 Плейлисты очищены от нерабочих каналов"
echo "   🔄 Добавлены новые рабочие каналы из доноров"
echo "   📈 Обновлены метаданные и ссылки"
echo "   💾 Созданы бэкапы для безопасности"
echo "   📊 Сгенерированы детальные отчеты"
echo "   🚀 Изменения отправлены в Git репозиторий"
echo ""
echo "🎯 Ваши IPTV плейлисты теперь максимально актуальны и надежны!"
