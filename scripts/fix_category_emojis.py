#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для восстановления эмодзи в заголовках категорий IPTV плейлистов
"""

import os
import re
from datetime import datetime

# Маппинг категорий и их эмодзи
CATEGORY_EMOJIS = {
    'эфирные': '📺',
    'федеральные_плюс': '🏛️',
    'спортивные': '⚽',
    'кино_и_сериалы': '🎬',
    'кинозалы': '🎭',
    'кинозалы_2': '🎪',
    'кинозалы_3': '🎨',
    'кинозалы_rutube': '📽️',
    'кинозалы_сити_эдем': '🏙️',
    'детские': '👶',
    'музыкальные': '🎵',
    'новости': '📰',
    'познавательные': '🧠',
    'развлекательные': '🎉',
    'региoнальные': '🏘️',
    'религиозные': '⛪',
    'радио': '📻',
    '18+': '🔞',
    'инфо': 'ℹ️',
    'relax': '🧘',
    'fashion': '👗',
    'наш_спорт': '🏆'
}

def fix_category_header(file_path, category_name):
    """Исправляет заголовок категории, добавляя эмодзи"""
    
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return False
    
    # Получаем эмодзи для категории
    emoji = CATEGORY_EMOJIS.get(category_name, '📂')
    
    try:
        # Читаем файл
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Подсчитываем каналы
        channel_count = len([line for line in lines if line.startswith('http')])
        
        # Создаем новый заголовок
        new_header = f"#EXTM3U\n{emoji} Категория: {category_name.replace('_', ' ').title()}\n# Каналов: {channel_count}\n# Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        
        # Находим где заканчивается старый заголовок
        content_start = 0
        for i, line in enumerate(lines):
            if line.startswith('#EXT') and not line.startswith('#EXTM3U') and not line.startswith('#EXTINF'):
                continue
            elif line.startswith('#') and ('Категория:' in line or 'каналов:' in line.lower() or 'обновлено:' in line.lower() or 'очищенный' in line.lower()):
                continue
            elif line.strip() == '':
                continue
            else:
                content_start = i
                break
        
        # Собираем новый контент
        new_content = new_header + '\n'.join(lines[content_start:])
        
        # Записываем обратно
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ {emoji} {category_name}: заголовок обновлен ({channel_count} каналов)")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обработке {category_name}: {e}")
        return False

def main():
    """Основная функция"""
    print("🎨 ВОССТАНОВЛЕНИЕ ЭМОДЗИ В ЗАГОЛОВКАХ КАТЕГОРИЙ")
    print("=" * 50)
    print()
    
    categories_dir = 'categories'
    
    if not os.path.exists(categories_dir):
        print(f"❌ Папка {categories_dir} не найдена!")
        return
    
    # Получаем список файлов категорий
    category_files = [f for f in os.listdir(categories_dir) if f.endswith('.m3u')]
    
    if not category_files:
        print("❌ Файлы категорий не найдены!")
        return
    
    print(f"📂 Найдено категорий: {len(category_files)}")
    print()
    
    success_count = 0
    
    for file_name in sorted(category_files):
        category_name = file_name.replace('.m3u', '')
        file_path = os.path.join(categories_dir, file_name)
        
        if fix_category_header(file_path, category_name):
            success_count += 1
    
    print()
    print(f"🎉 Обработано успешно: {success_count}/{len(category_files)} категорий")
    
    if success_count == len(category_files):
        print("✅ Все заголовки категорий восстановлены!")
    else:
        print(f"⚠️ Некоторые категории не удалось обработать")

if __name__ == "__main__":
    main()
