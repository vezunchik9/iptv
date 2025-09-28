#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 МАСТЕР-СКРИПТ ИСПРАВЛЕНИЯ ПЛЕЙЛИСТОВ
Инженерный подход: точно в цель, без усложнений
"""

import os
import re
from datetime import datetime
from collections import defaultdict

class MasterPlaylistFixer:
    def __init__(self):
        self.categories_dir = "categories"
        self.playlists_dir = "playlists"
        
        # Правильные эмодзи для категорий
        self.category_emojis = {
            '18+': '🔞',
            'fashion': '👗', 
            'relax': '🧘',
            'детские': '👶',
            'инфо': 'ℹ️',
            'кино_и_сериалы': '🎬',
            'кинозалы': '🎭',
            'кинозалы_2': '🎪',
            'кинозалы_3': '🎨',
            'кинозалы_rutube': '📽️',
            'кинозалы_сити_эдем': '🏙️',
            'музыкальные': '🎵',
            'наш_спорт': '🏆',
            'новости': '📰',
            'познавательные': '🧠',
            'радио': '📻',
            'развлекательные': '🎉',
            'разное': '📂',
            'региoнальные': '🏘️',
            'религиозные': '⛪',
            'спортивные': '⚽',
            'федеральные_плюс': '🏛️',
            'эфирные': '📺'
        }
        
        # Приоритет категорий для плейлиста
        self.category_priority = [
            'инфо', 'эфирные', 'федеральные_плюс', 'новости',
            'спортивные', 'наш_спорт', 'кино_и_сериалы',
            'кинозалы', 'кинозалы_2', 'кинозалы_3', 'кинозалы_rutube', 'кинозалы_сити_эдем',
            'музыкальные', 'детские', 'познавательные', 'развлекательные',
            'региoнальные', 'радио', 'религиозные', 'relax', 'fashion', 'разное', '18+'
        ]
    
    def fix_category_headers(self):
        """Исправляет заголовки всех категорий с эмодзи"""
        print("🎨 ИСПРАВЛЕНИЕ ЗАГОЛОВКОВ КАТЕГОРИЙ")
        print("=" * 40)
        
        if not os.path.exists(self.categories_dir):
            print(f"❌ Папка {self.categories_dir} не найдена!")
            return False
        
        fixed_count = 0
        category_files = [f for f in os.listdir(self.categories_dir) if f.endswith('.m3u')]
        
        for file_name in sorted(category_files):
            category_name = file_name.replace('.m3u', '')
            file_path = os.path.join(self.categories_dir, file_name)
            
            if self.fix_single_category_header(file_path, category_name):
                fixed_count += 1
        
        print(f"\n✅ Исправлено заголовков: {fixed_count}/{len(category_files)}")
        return True
    
    def fix_single_category_header(self, file_path, category_name):
        """Исправляет заголовок одной категории"""
        try:
            # Читаем файл
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Подсчитываем каналы
            channel_count = len([line for line in lines if line.startswith('http')])
            
            if channel_count == 0:
                print(f"⚠️ {category_name}: пустая категория, пропускаем")
                return False
            
            # Получаем эмодзи
            emoji = self.category_emojis.get(category_name, '📂')
            
            # Создаем правильный заголовок
            display_name = category_name.replace('_', ' ').title()
            new_header = [
                "#EXTM3U",
                f"{emoji} Категория: {display_name}",
                f"# Каналов: {channel_count}",
                f"# Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                ""
            ]
            
            # Находим где начинается контент (первый EXTINF)
            content_start = 0
            for i, line in enumerate(lines):
                if line.startswith('#EXTINF'):
                    content_start = i
                    break
            
            # Собираем новый контент
            new_content = '\n'.join(new_header) + '\n'.join(lines[content_start:])
            
            # Записываем обратно
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ {emoji} {category_name}: {channel_count} каналов")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка {category_name}: {e}")
            return False
    
    def clean_brazzers_channels(self):
        """Очищает нерабочие Brazzers каналы из 18+"""
        print("\n🧹 ОЧИСТКА НЕРАБОЧИХ BRAZZERS КАНАЛОВ")
        print("=" * 40)
        
        file_path = os.path.join(self.categories_dir, '18+.m3u')
        if not os.path.exists(file_path):
            print("❌ Файл 18+.m3u не найден!")
            return False
        
        try:
            # Читаем файл
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Создаем бэкап
            backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"💾 Создан бэкап: {backup_path}")
            
            # Фильтруем каналы
            new_lines = []
            i = 0
            removed_count = 0
            kept_count = 0
            
            while i < len(lines):
                line = lines[i].strip()
                
                # Копируем заголовки и комментарии
                if not line.startswith('#EXTINF'):
                    new_lines.append(line)
                    i += 1
                    continue
                
                # Проверяем EXTINF + URL пару
                extinf_line = line
                url_line = ""
                
                if i + 1 < len(lines):
                    url_line = lines[i + 1].strip()
                
                # Удаляем нерабочие Brazzers каналы (180sec.flv)
                if 'brazzers' in extinf_line.lower() and '180sec.flv' in url_line:
                    print(f"🗑️ Удален: {extinf_line.split(',')[-1]}")
                    removed_count += 1
                    i += 2  # Пропускаем и EXTINF и URL
                    continue
                
                # Оставляем рабочие каналы
                new_lines.append(extinf_line)
                if url_line:
                    new_lines.append(url_line)
                    kept_count += 1
                
                i += 2 if url_line else 1
            
            # Обновляем счетчик в заголовке
            for j, line in enumerate(new_lines):
                if line.startswith('# Каналов:'):
                    new_lines[j] = f"# Каналов: {kept_count}"
                    break
            
            # Записываем очищенный файл
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            
            print(f"✅ Удалено нерабочих: {removed_count}")
            print(f"✅ Оставлено рабочих: {kept_count}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при очистке: {e}")
            return False
    
    def create_perfect_playlist(self):
        """Создает идеальный плейлист Televizo"""
        print("\n🎯 СОЗДАНИЕ ИДЕАЛЬНОГО ПЛЕЙЛИСТА")
        print("=" * 40)
        
        channels = defaultdict(list)
        total_channels = 0
        
        # Читаем все категории
        category_files = [f for f in os.listdir(self.categories_dir) if f.endswith('.m3u')]
        
        for file_name in category_files:
            category_name = file_name.replace('.m3u', '')
            file_path = os.path.join(self.categories_dir, file_name)
            
            count = self.read_category_channels(file_path, category_name, channels)
            if count > 0:
                emoji = self.category_emojis.get(category_name, '📂')
                print(f"   {emoji} {category_name}: {count} каналов")
                total_channels += count
        
        # Создаем плейлисты
        os.makedirs(self.playlists_dir, exist_ok=True)
        
        # Полный плейлист
        self.write_playlist(channels, f"{self.playlists_dir}/televizo_main.m3u", 
                          total_channels, include_adult=True, title="ПОЛНАЯ ВЕРСИЯ")
        
        # Безопасный плейлист
        safe_channels = {k: v for k, v in channels.items() if k != '18+'}
        safe_total = total_channels - len(channels.get('18+', []))
        self.write_playlist(safe_channels, f"{self.playlists_dir}/televizo_safe.m3u", 
                          safe_total, include_adult=False, title="БЕЗОПАСНАЯ ВЕРСИЯ")
        
        print(f"\n🎉 Создано плейлистов с {total_channels} каналами")
        return True
    
    def read_category_channels(self, file_path, category_name, channels):
        """Читает каналы из файла категории"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            count = 0
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if line.startswith('#EXTINF'):
                    extinf_line = line
                    i += 1
                    
                    if i < len(lines):
                        url_line = lines[i].strip()
                        if url_line and not url_line.startswith('#'):
                            channels[category_name].append({
                                'extinf': extinf_line,
                                'url': url_line
                            })
                            count += 1
                
                i += 1
            
            return count
            
        except Exception as e:
            print(f"⚠️ Ошибка чтения {category_name}: {e}")
            return 0
    
    def write_playlist(self, channels, output_file, total_channels, include_adult=True, title=""):
        """Записывает плейлист в файл"""
        try:
            # Сортируем категории по приоритету
            sorted_categories = []
            for cat in self.category_priority:
                if cat in channels:
                    if not include_adult and cat == '18+':
                        continue
                    sorted_categories.append(cat)
            
            # Добавляем оставшиеся категории
            for cat in sorted(channels.keys()):
                if cat not in sorted_categories:
                    if not include_adult and cat == '18+':
                        continue
                    sorted_categories.append(cat)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                # Заголовок
                f.write('#EXTM3U url-tvg="https://iptvx.one/epg/epg_lite.xml.gz"\n')
                f.write(f'# 📺 Televizo IPTV Playlist ({title})\n')
                f.write(f'# Создан: {datetime.now().strftime("%d.%m.%Y %H:%M")}\n')
                f.write(f'# Всего каналов: {total_channels}\n')
                f.write(f'# Категорий: {len(sorted_categories)}\n')
                f.write(f'# Включает 18+ контент: {"Да" if include_adult else "Нет"}\n')
                f.write(f'# GitHub: https://github.com/vezunchik9/iptv\n')
                f.write(f'# Telegram: @SHARED_NEW\n\n')
                
                # Категории и каналы
                for category in sorted_categories:
                    category_channels = channels[category]
                    emoji = self.category_emojis.get(category, '📂')
                    display_name = category.replace('_', ' ').upper()
                    
                    f.write(f'# === {emoji} {display_name} ({len(category_channels)} каналов) ===\n\n')
                    
                    for channel in category_channels:
                        f.write(f'{channel["extinf"]}\n')
                        f.write(f'{channel["url"]}\n\n')
            
            print(f"✅ Создан: {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка записи {output_file}: {e}")
            return False

def main():
    print("🎯 МАСТЕР ИСПРАВЛЕНИЯ ПЛЕЙЛИСТОВ")
    print("=" * 50)
    print("🚀 Инженерный подход: точно в цель!")
    print()
    
    fixer = MasterPlaylistFixer()
    
    # 1. Исправляем заголовки с эмодзи
    if not fixer.fix_category_headers():
        print("❌ Не удалось исправить заголовки!")
        return
    
    # 2. Очищаем нерабочие Brazzers каналы
    fixer.clean_brazzers_channels()
    
    # 3. Создаем идеальные плейлисты
    if fixer.create_perfect_playlist():
        print("\n🎉 ВСЕ ИСПРАВЛЕНО ИДЕАЛЬНО!")
        print("\n📁 Готовые файлы:")
        print("   📄 playlists/televizo_main.m3u - полный плейлист")
        print("   📄 playlists/televizo_safe.m3u - безопасный плейлист")
        print("\n🔗 GitHub raw ссылки:")
        print("   https://raw.githubusercontent.com/vezunchik9/iptv/main/playlists/televizo_main.m3u")
        print("   https://raw.githubusercontent.com/vezunchik9/iptv/main/playlists/televizo_safe.m3u")
    else:
        print("❌ Ошибка при создании плейлистов!")

if __name__ == "__main__":
    main()
