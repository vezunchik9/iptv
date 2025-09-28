#!/bin/bash

# Скрипт для очистки проекта IPTV от мусорных файлов

echo "🧹 ОЧИСТКА ПРОЕКТА IPTV ОТ МУСОРА"
echo "================================="
echo ""

# Функция для безопасного удаления с подтверждением
safe_remove() {
    local path="$1"
    local description="$2"
    local size=$(du -sh "$path" 2>/dev/null | cut -f1)
    
    if [ -e "$path" ]; then
        echo "🗑️ Найден мусор: $description ($size)"
        read -p "   Удалить? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$path"
            echo "   ✅ Удалено: $description"
        else
            echo "   ⏭️ Пропущено: $description"
        fi
        echo ""
    fi
}

# Подсчет размера до очистки
echo "📊 Размер проекта ДО очистки:"
du -sh .
echo ""

# 1. Очистка старых отчетов (оставляем только последний)
echo "1️⃣ ОЧИСТКА СТАРЫХ ОТЧЕТОВ"
echo "========================="

if [ -d "reports" ]; then
    # Находим самый новый файл отчета
    newest_report=$(ls -t reports/*.json 2>/dev/null | head -1)
    
    # Удаляем все остальные отчеты
    for report in reports/*.json; do
        if [ "$report" != "$newest_report" ] && [ -f "$report" ]; then
            safe_remove "$report" "Старый отчет: $(basename "$report")"
        fi
    done
else
    echo "   📂 Папка reports не найдена"
fi

# 2. Очистка старых бэкапов (оставляем только сегодняшние)
echo "2️⃣ ОЧИСТКА СТАРЫХ БЭКАПОВ"
echo "========================="

if [ -d "backups" ]; then
    # Удаляем бэкапы старше 1 дня
    find backups/ -name "*.backup.*" -mtime +1 -type f 2>/dev/null | while read backup; do
        safe_remove "$backup" "Старый бэкап: $(basename "$backup")"
    done
    
    # Удаляем пустые папки в бэкапах
    find backups/ -type d -empty -delete 2>/dev/null
else
    echo "   📂 Папка backups не найдена"
fi

# 3. Очистка дубликатов плейлистов
echo "3️⃣ ОЧИСТКА ДУБЛИКАТОВ ПЛЕЙЛИСТОВ"
echo "================================"

if [ -d "playlists" ]; then
    # Удаляем старые бэкапы плейлистов
    for backup in playlists/*.backup.*; do
        if [ -f "$backup" ]; then
            safe_remove "$backup" "Бэкап плейлиста: $(basename "$backup")"
        fi
    done
else
    echo "   📂 Папка playlists не найдена"
fi

# 4. Очистка временных файлов
echo "4️⃣ ОЧИСТКА ВРЕМЕННЫХ ФАЙЛОВ"
echo "==========================="

# Поиск и удаление временных файлов
temp_files=$(find . -name "*.tmp" -o -name "*.temp" -o -name "*~" -o -name ".DS_Store" 2>/dev/null)
if [ -n "$temp_files" ]; then
    echo "$temp_files" | while read temp_file; do
        safe_remove "$temp_file" "Временный файл: $(basename "$temp_file")"
    done
else
    echo "   ✅ Временных файлов не найдено"
fi

# 5. Очистка кеша Python
echo "5️⃣ ОЧИСТКА КЕША PYTHON"
echo "======================"

pycache_dirs=$(find . -name "__pycache__" -type d 2>/dev/null)
if [ -n "$pycache_dirs" ]; then
    echo "$pycache_dirs" | while read pycache_dir; do
        safe_remove "$pycache_dir" "Кеш Python: $pycache_dir"
    done
else
    echo "   ✅ Кеша Python не найдено"
fi

# Подсчет размера после очистки
echo ""
echo "📊 РЕЗУЛЬТАТ ОЧИСТКИ:"
echo "===================="
echo "Размер проекта ПОСЛЕ очистки:"
du -sh .
echo ""

echo "🎉 ОЧИСТКА ЗАВЕРШЕНА!"
echo ""
echo "💡 РЕКОМЕНДАЦИИ:"
echo "   • Запускайте этот скрипт раз в неделю"
echo "   • Важные бэкапы сохраняются автоматически"
echo "   • Последний отчет всегда остается"
echo ""
echo "🚀 Для запуска: ./cleanup_project.sh"
