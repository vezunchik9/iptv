#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания организованного плейлиста для Televizo
с категоризацией каналов по группам
"""

import os
import re
from collections import defaultdict, Counter
from datetime import datetime

class TelevizoPlaylistCreator:
    def __init__(self, source_file):
        self.source_file = source_file
        self.channels = defaultdict(list)
        self.total_channels = 0
        
    def read_source_playlist(self):
        """Читает исходный M3U файл и парсит каналы по категориям"""
        try:
            # Пробуем разные кодировки
            encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'iso-8859-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(self.source_file, 'r', encoding=encoding) as f:
                        content = f.read()
                    print(f"✓ Файл прочитан с кодировкой: {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None or len(content.strip()) == 0:
                print("❌ Файл пустой или не удалось прочитать")
                return False
            
            lines = content.splitlines()
            current_info = None
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('#EXTINF'):
                    current_info = line
                elif line and not line.startswith('#') and current_info:
                    # Извлекаем информацию о канале
                    channel_data = self.parse_extinf_line(current_info, line)
                    if channel_data:
                        category = channel_data['group']
                        self.channels[category].append(channel_data)
                        self.total_channels += 1
                    current_info = None
            
            print(f"✓ Обработано {self.total_channels} каналов в {len(self.channels)} категориях")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при чтении файла: {e}")
            return False
    
    def parse_extinf_line(self, extinf_line, url):
        """Парсит строку #EXTINF и извлекает информацию о канале"""
        try:
            # Извлекаем tvg-id
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', extinf_line)
            tvg_id = tvg_id_match.group(1) if tvg_id_match else "no_epg"
            
            # Извлекаем tvg-logo
            tvg_logo_match = re.search(r'tvg-logo="([^"]*)"', extinf_line)
            tvg_logo = tvg_logo_match.group(1) if tvg_logo_match else ""
            
            # Извлекаем group-title
            group_match = re.search(r'group-title="([^"]*)"', extinf_line)
            group = group_match.group(1) if group_match else "Разное"
            
            # Извлекаем название канала (после последней запятой)
            name_match = re.search(r',(.*)$', extinf_line)
            name = name_match.group(1).strip() if name_match else "Без названия"
            
            # Извлекаем дополнительные параметры
            catchup_match = re.search(r'catchup="([^"]*)"', extinf_line)
            catchup = catchup_match.group(1) if catchup_match else None
            
            catchup_days_match = re.search(r'catchup-days="([^"]*)"', extinf_line)
            catchup_days = catchup_days_match.group(1) if catchup_days_match else None
            
            return {
                'name': name,
                'url': url,
                'tvg_id': tvg_id,
                'tvg_logo': tvg_logo,
                'group': group,
                'catchup': catchup,
                'catchup_days': catchup_days,
                'original_extinf': extinf_line
            }
        except Exception as e:
            print(f"⚠️ Ошибка при парсинге канала: {e}")
            return None
    
    def create_main_playlist(self, output_file="playlists/televizo_main.m3u"):
        """Создает основной плейлист для Televizo с организованными категориями"""
        
        # Сортируем категории: важные первыми
        priority_categories = [
            "ИНФО", "Эфирные", "Новости", "Спорт", "Кино", "Музыка", 
            "Детские", "Познавательные", "Развлекательные"
        ]
        
        sorted_categories = []
        
        # Сначала добавляем приоритетные категории (если они есть)
        for cat in priority_categories:
            if cat in self.channels:
                sorted_categories.append(cat)
        
        # Затем добавляем остальные в алфавитном порядке
        for cat in sorted(self.channels.keys()):
            if cat not in sorted_categories:
                sorted_categories.append(cat)
        
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                # Заголовок плейлиста
                f.write('#EXTM3U url-tvg="https://iptvx.one/epg/epg_lite.xml.gz"\n')
                f.write(f'# Televizo IPTV Playlist\n')
                f.write(f'# Создан: {datetime.now().strftime("%d.%m.%Y %H:%M")}\n')
                f.write(f'# Всего каналов: {self.total_channels}\n')
                f.write(f'# Категорий: {len(self.channels)}\n')
                f.write(f'# GitHub: https://github.com/YOUR_USERNAME/iptv\n\n')
                
                # Добавляем каналы по категориям
                for category in sorted_categories:
                    channels_in_category = self.channels[category]
                    f.write(f'# === {category.upper()} ({len(channels_in_category)} каналов) ===\n\n')
                    
                    for channel in channels_in_category:
                        # Создаем оптимизированную строку EXTINF для Televizo
                        extinf = f'#EXTINF:-1'
                        
                        if channel['tvg_id']:
                            extinf += f' tvg-id="{channel["tvg_id"]}"'
                        
                        if channel['tvg_logo']:
                            extinf += f' tvg-logo="{channel["tvg_logo"]}"'
                        
                        extinf += f' group-title="{category}"'
                        
                        if channel['catchup']:
                            extinf += f' catchup="{channel["catchup"]}"'
                            if channel['catchup_days']:
                                extinf += f' catchup-days="{channel["catchup_days"]}"'
                        
                        extinf += f',{channel["name"]}\n'
                        
                        f.write(extinf)
                        f.write(f'{channel["url"]}\n\n')
                
            print(f"✓ Основной плейлист создан: {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при создании плейлиста: {e}")
            return False
    
    def create_category_playlists(self):
        """Создает отдельные плейлисты для каждой категории"""
        try:
            for category, channels in self.channels.items():
                safe_category = re.sub(r'[^\w\-_\.]', '_', category)
                filename = f"categories/{safe_category.lower()}.m3u"
                
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write('#EXTM3U\n')
                    f.write(f'# Категория: {category}\n')
                    f.write(f'# Каналов: {len(channels)}\n\n')
                    
                    for channel in channels:
                        f.write(f'{channel["original_extinf"]}\n')
                        f.write(f'{channel["url"]}\n\n')
                
            print(f"✓ Создано {len(self.channels)} плейлистов по категориям")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при создании плейлистов категорий: {e}")
            return False
    
    def show_statistics(self):
        """Показывает статистику по каналам и категориям"""
        print("\n" + "="*50)
        print("📊 СТАТИСТИКА ПЛЕЙЛИСТА")
        print("="*50)
        print(f"Общее количество каналов: {self.total_channels}")
        print(f"Количество категорий: {len(self.channels)}")
        print("\n📂 Каналы по категориям:")
        
        for category, channels in sorted(self.channels.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  {category}: {len(channels)} каналов")

def main():
    print("🚀 Создание плейлиста для Televizo")
    print("="*40)
    
    creator = TelevizoPlaylistCreator("kanal")
    
    # Читаем исходный файл
    if not creator.read_source_playlist():
        print("\n⚠️ ВНИМАНИЕ: Исходный файл 'kanal' пустой или не найден!")
        print("Пожалуйста, сохраните ваш плейлист в файл 'kanal' и запустите скрипт снова.")
        return
    
    # Показываем статистику
    creator.show_statistics()
    
    # Создаем плейлисты
    print("\n📝 Создание плейлистов...")
    
    if creator.create_main_playlist():
        print("✅ Основной плейлист для Televizo создан")
    
    if creator.create_category_playlists():
        print("✅ Плейлисты по категориям созданы")
    
    print(f"\n🎯 ГОТОВО! Плейлисты созданы для {creator.total_channels} каналов")
    print("\n📁 Структура файлов:")
    print("  📄 playlists/televizo_main.m3u - основной плейлист для Televizo")
    print("  📁 categories/ - плейлисты по категориям")
    
    print("\n🔗 Для GitHub используйте raw ссылки:")
    print("  https://raw.githubusercontent.com/YOUR_USERNAME/iptv/main/playlists/televizo_main.m3u")

if __name__ == "__main__":
    main()
