#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенный скрипт для создания полного плейлиста Televizo
из всех категорий, включая 18+ контент
"""

import os
import re
from collections import defaultdict
from datetime import datetime

class FullTelevizoPlaylistCreator:
    def __init__(self, categories_dir="categories"):
        self.categories_dir = categories_dir
        self.channels = defaultdict(list)
        self.total_channels = 0
        
        # Маппинг эмодзи для категорий
        self.category_emojis = {
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
            'наш_спорт': '🏆',
            'разное': '📂'
        }
        
    def read_category_file(self, file_path, category_name):
        """Читает файл категории и парсит каналы"""
        try:
            encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'iso-8859-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if not content:
                print(f"⚠️ Не удалось прочитать файл: {file_path}")
                return 0
            
            lines = content.strip().split('\n')
            channels_count = 0
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Пропускаем заголовки и комментарии
                if line.startswith('#EXTM3U') or line.startswith('#') and not line.startswith('#EXTINF'):
                    i += 1
                    continue
                
                # Ищем EXTINF строку
                if line.startswith('#EXTINF'):
                    extinf_line = line
                    i += 1
                    
                    # Следующая строка должна быть URL
                    if i < len(lines):
                        url_line = lines[i].strip()
                        if url_line and not url_line.startswith('#'):
                            channel = self.parse_channel(extinf_line, url_line, category_name)
                            if channel:
                                self.channels[category_name].append(channel)
                                channels_count += 1
                
                i += 1
            
            return channels_count
            
        except Exception as e:
            print(f"⚠️ Ошибка при чтении {file_path}: {e}")
            return 0
    
    def parse_channel(self, extinf_line, url, category):
        """Парсит информацию о канале из EXTINF строки"""
        try:
            # Извлекаем название канала
            name_match = re.search(r',(.+)$', extinf_line)
            name = name_match.group(1).strip() if name_match else "Unknown"
            
            # Извлекаем tvg-id
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', extinf_line)
            tvg_id = tvg_id_match.group(1) if tvg_id_match else ""
            
            # Извлекаем tvg-logo
            tvg_logo_match = re.search(r'tvg-logo="([^"]*)"', extinf_line)
            tvg_logo = tvg_logo_match.group(1) if tvg_logo_match else ""
            
            # Извлекаем group-title
            group_title_match = re.search(r'group-title="([^"]*)"', extinf_line)
            group_title = group_title_match.group(1) if group_title_match else category
            
            return {
                'name': name,
                'url': url,
                'tvg_id': tvg_id,
                'tvg_logo': tvg_logo,
                'group_title': group_title,
                'category': category,
                'extinf': extinf_line
            }
            
        except Exception as e:
            print(f"⚠️ Ошибка при парсинге канала: {e}")
            return None
    
    def read_all_categories(self):
        """Читает все файлы категорий"""
        if not os.path.exists(self.categories_dir):
            print(f"❌ Папка {self.categories_dir} не найдена!")
            return False
        
        category_files = [f for f in os.listdir(self.categories_dir) if f.endswith('.m3u')]
        
        if not category_files:
            print(f"❌ Файлы категорий не найдены в {self.categories_dir}!")
            return False
        
        print(f"📂 Найдено категорий: {len(category_files)}")
        
        total_processed = 0
        for file_name in sorted(category_files):
            category_name = file_name.replace('.m3u', '')
            file_path = os.path.join(self.categories_dir, file_name)
            
            channels_count = self.read_category_file(file_path, category_name)
            total_processed += channels_count
            
            emoji = self.category_emojis.get(category_name, '📂')
            print(f"   {emoji} {category_name}: {channels_count} каналов")
        
        self.total_channels = total_processed
        print(f"\n✅ Всего обработано каналов: {self.total_channels}")
        return True
    
    def create_main_playlist(self, output_file="playlists/televizo_main.m3u", include_adult=True):
        """Создает основной плейлист для Televizo"""
        
        # Приоритет категорий для сортировки
        priority_order = [
            "инфо", "эфирные", "федеральные_плюс", "новости", 
            "спортивные", "наш_спорт", "кино_и_сериалы", 
            "кинозалы", "кинозалы_2", "кинозалы_3", "кинозалы_rutube", "кинозалы_сити_эдем",
            "музыкальные", "детские", "познавательные", "развлекательные",
            "региoнальные", "радио", "религиозные", "relax", "fashion", "разное"
        ]
        
        # Добавляем 18+ в конец, если включено
        if include_adult:
            priority_order.append("18+")
        
        # Сортируем категории
        sorted_categories = []
        for cat in priority_order:
            if cat in self.channels:
                sorted_categories.append(cat)
        
        # Добавляем оставшиеся категории
        for cat in sorted(self.channels.keys()):
            if cat not in sorted_categories:
                if not include_adult and cat == "18+":
                    continue
                sorted_categories.append(cat)
        
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                # Заголовок плейлиста
                f.write('#EXTM3U url-tvg="https://iptvx.one/epg/epg_lite.xml.gz"\n')
                f.write(f'# 📺 Televizo IPTV Playlist (ПОЛНАЯ ВЕРСИЯ)\n')
                f.write(f'# Создан: {datetime.now().strftime("%d.%m.%Y %H:%M")}\n')
                f.write(f'# Всего каналов: {self.total_channels}\n')
                f.write(f'# Категорий: {len(sorted_categories)}\n')
                f.write(f'# Включает 18+ контент: {"Да" if include_adult else "Нет"}\n')
                f.write(f'# GitHub: https://github.com/vezunchik9/iptv\n')
                f.write(f'# Telegram: @SHARED_NEW\n\n')
                
                # Добавляем каналы по категориям
                for category in sorted_categories:
                    channels_in_category = self.channels[category]
                    emoji = self.category_emojis.get(category, '📂')
                    
                    f.write(f'# === {emoji} {category.upper().replace("_", " ")} ({len(channels_in_category)} каналов) ===\n\n')
                    
                    for channel in channels_in_category:
                        f.write(f'{channel["extinf"]}\n')
                        f.write(f'{channel["url"]}\n\n')
            
            print(f"✅ Плейлист создан: {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при создании плейлиста: {e}")
            return False
    
    def show_statistics(self):
        """Показывает статистику по каналам"""
        print(f"\n📊 СТАТИСТИКА ПОЛНОГО ПЛЕЙЛИСТА")
        print("=" * 50)
        print(f"Общее количество каналов: {self.total_channels}")
        print(f"Количество категорий: {len(self.channels)}")
        print("\n📂 Каналы по категориям:")
        
        for category, channels in sorted(self.channels.items(), key=lambda x: len(x[1]), reverse=True):
            emoji = self.category_emojis.get(category, '📂')
            print(f"  {emoji} {category}: {len(channels)} каналов")

def main():
    print("🚀 СОЗДАНИЕ ПОЛНОГО ПЛЕЙЛИСТА TELEVIZO")
    print("=" * 50)
    print("📺 Включает ВСЕ категории, включая 18+ контент")
    print()
    
    creator = FullTelevizoPlaylistCreator()
    
    # Читаем все категории
    if not creator.read_all_categories():
        print("\n❌ Не удалось прочитать категории!")
        return
    
    # Показываем статистику
    creator.show_statistics()
    
    # Создаем полный плейлист (с 18+)
    print("\n📝 Создание полного плейлиста...")
    if creator.create_main_playlist("playlists/televizo_main.m3u", include_adult=True):
        print("✅ Полный плейлист создан (включая 18+)")
    
    # Создаем безопасный плейлист (без 18+)
    print("\n📝 Создание безопасного плейлиста...")
    if creator.create_main_playlist("playlists/televizo_safe.m3u", include_adult=False):
        print("✅ Безопасный плейлист создан (без 18+)")
    
    print(f"\n🎯 ГОТОВО! Плейлисты созданы для {creator.total_channels} каналов")
    print(f"\n📁 Файлы:")
    print(f"  📄 playlists/televizo_main.m3u - полный плейлист (с 18+)")
    print(f"  📄 playlists/televizo_safe.m3u - безопасный плейлист (без 18+)")
    print(f"\n🔗 GitHub raw ссылки:")
    print(f"  https://raw.githubusercontent.com/vezunchik9/iptv/main/playlists/televizo_main.m3u")
    print(f"  https://raw.githubusercontent.com/vezunchik9/iptv/main/playlists/televizo_safe.m3u")

if __name__ == "__main__":
    main()
