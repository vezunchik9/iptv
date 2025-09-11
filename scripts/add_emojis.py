#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для добавления красивых эмодзи к категориям в плейлисте
"""

import re

# Словарь соответствия категорий и эмодзи
CATEGORY_EMOJIS = {
    'ИНФО': 'ℹ️',
    'Эфирные': '📺',
    'Новости': '📰', 
    'Спортивные': '⚽',
    'Наш спорт': '🏃‍♂️',
    'Музыкальные': '🎵',
    'Кино и сериалы': '🎬',
    'Кинозалы': '🍿',
    'Кинозалы 2': '🎭',
    'Кинозалы 3': '🎪',
    'Кинозалы RUTUBE': '📹',
    'Кинозалы Сити Эдем': '🏛️',
    'Детские': '🧸',
    'Познавательные': '🧠',
    'Развлекательные': '🎊',
    'Федеральные плюс': '🇷🇺',
    'Региoнальные': '📍',
    'Радио': '📻',
    'Религиозные': '⛪',
    'Fashion': '👗',
    'Relax': '🧘‍♂️'
}

def add_emojis_to_playlist(input_file, output_file):
    """Добавляет эмодзи к заголовкам категорий в плейлисте"""
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Паттерн для поиска заголовков категорий
        pattern = r'# === ([^(]+) \((\d+ каналов?)\) ==='
        
        def replace_header(match):
            category = match.group(1).strip()
            count = match.group(2)
            
            # Ищем подходящий эмодзи
            emoji = CATEGORY_EMOJIS.get(category, '📺')  # По умолчанию 📺
            
            return f'# === {emoji} {category} ({count}) ==='
        
        # Заменяем все заголовки категорий
        updated_content = re.sub(pattern, replace_header, content)
        
        # Также обновляем group-title в самих каналах
        for category, emoji in CATEGORY_EMOJIS.items():
            # Обновляем в строках EXTINF
            pattern_extinf = rf'group-title="{re.escape(category)}"'
            replacement_extinf = f'group-title="{emoji} {category}"'
            updated_content = re.sub(pattern_extinf, replacement_extinf, updated_content)
        
        # Сохраняем обновленный файл
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"✅ Эмодзи добавлены в {output_file}")
        
        # Статистика
        emoji_count = len([match for match in re.finditer(r'# === [^(]+ \([^)]+\) ===', updated_content)])
        print(f"📊 Обновлено категорий: {emoji_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def update_category_files():
    """Обновляет файлы отдельных категорий с эмодзи"""
    
    import os
    
    category_mappings = {
        'инфо.m3u': ('ℹ️', 'ИНФО'),
        'эфирные.m3u': ('📺', 'Эфирные'),
        'новости.m3u': ('📰', 'Новости'),
        'спортивные.m3u': ('⚽', 'Спортивные'),
        'наш_спорт.m3u': ('🏃‍♂️', 'Наш спорт'),
        'музыкальные.m3u': ('🎵', 'Музыкальные'),
        'кино_и_сериалы.m3u': ('🎬', 'Кино и сериалы'),
        'кинозалы.m3u': ('🍿', 'Кинозалы'),
        'кинозалы_2.m3u': ('🎭', 'Кинозалы 2'),
        'кинозалы_3.m3u': ('🎪', 'Кинозалы 3'),
        'кинозалы_rutube.m3u': ('📹', 'Кинозалы RUTUBE'),
        'кинозалы_сити_эдем.m3u': ('🏛️', 'Кинозалы Сити Эдем'),
        'детские.m3u': ('🧸', 'Детские'),
        'познавательные.m3u': ('🧠', 'Познавательные'),
        'развлекательные.m3u': ('🎊', 'Развлекательные'),
        'федеральные_плюс.m3u': ('🇷🇺', 'Федеральные плюс'),
        'региoнальные.m3u': ('📍', 'Региoнальные'),
        'радио.m3u': ('📻', 'Радио'),
        'религиозные.m3u': ('⛪', 'Религиозные'),
        'fashion.m3u': ('👗', 'Fashion'),
        'relax.m3u': ('🧘‍♂️', 'Relax')
    }
    
    for filename, (emoji, category_name) in category_mappings.items():
        filepath = f'categories/{filename}'
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Обновляем заголовок
                content = re.sub(r'# Категория: [^\n]+', f'# Категория: {emoji} {category_name}', content)
                
                # Обновляем group-title
                pattern = rf'group-title="{re.escape(category_name.replace(" плюс", "_плюс").replace(" ", "_").lower())}"'
                replacement = f'group-title="{emoji} {category_name}"'
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ Обновлен файл: {filename}")
                
            except Exception as e:
                print(f"⚠️ Ошибка с файлом {filename}: {e}")

if __name__ == "__main__":
    print("🎨 Добавление эмодзи к категориям плейлиста")
    print("="*50)
    
    # Обновляем основной плейлист
    if add_emojis_to_playlist('playlists/televizo_main.m3u', 'playlists/televizo_main.m3u'):
        print("🎯 Основной плейлист обновлен с эмодзи")
    
    # Обновляем файлы категорий
    print("\n📂 Обновление файлов категорий...")
    update_category_files()
    
    print("\n🎉 Все эмодзи добавлены!")
    print("\n📋 Категории с эмодзи:")
    for category, emoji in CATEGORY_EMOJIS.items():
        print(f"  {emoji} {category}")
