#!/bin/bash
# 🧹 ПОЛНАЯ ОЧИСТКА ПРОЕКТА

echo "🧹 НАЧИНАЕМ ОЧИСТКУ ПРОЕКТА"
echo "======================================"

# 1. Удаляем старые бэкапы (оставляем только последние 3)
echo "📦 Очищаем бэкапы..."
find . -name "*.backup.*" -mtime +7 -delete 2>/dev/null
find ./backups -type f -mtime +7 -delete 2>/dev/null
BACKUP_COUNT=$(find . -name "*.backup.*" | wc -l)
echo "  Осталось бэкапов: $BACKUP_COUNT"

# 2. Удаляем старые отчеты
echo "📊 Очищаем отчеты..."
find ./reports -type f -mtime +30 -delete 2>/dev/null
REPORT_COUNT=$(find ./reports -type f | wc -l)
echo "  Осталось отчетов: $REPORT_COUNT"

# 3. Удаляем дублирующие скрипты
echo "🗑️  Удаляем дубли скриптов..."
rm -f scripts/stream_checker.py
rm -f scripts/curl_stream_checker.py
rm -f scripts/advanced_stream_checker.py
echo "  Дубли удалены"

# 4. Удаляем временные файлы
echo "🗑️  Удаляем временные файлы..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name ".DS_Store" -delete
find . -name "*.tmp" -delete
echo "  Временные файлы удалены"

# 5. Показываем статистику
echo ""
echo "======================================"
echo "📊 ПОСЛЕ ОЧИСТКИ:"
echo "======================================"
echo "Размер проекта: $(du -sh . | awk '{print $1}')"
echo "Размер categories/: $(du -sh categories/ | awk '{print $1}')"
echo "Размер backups/: $(du -sh backups/ | awk '{print $1}')"
echo "Размер reports/: $(du -sh reports/ | awk '{print $1}')"
echo "Бэкапов: $(find . -name "*.backup.*" | wc -l)"
echo "======================================"
echo "✅ ОЧИСТКА ЗАВЕРШЕНА!"
