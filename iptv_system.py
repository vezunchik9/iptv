#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простая IPTV система
Парсит один донор и создает плейлист
"""

import requests
import re
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('iptv_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IPTVSystem:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.donor_url = "https://raw.githubusercontent.com/IPTVSHARED/iptv/refs/heads/main/IPTV_SHARED.m3u"
        
        # Простые категории
        self.categories = {
            'спортивные': ['спорт', 'sport', 'футбол', 'хоккей', 'баскетбол', 'теннис', 'бокс', 'eurosport', 'match'],
            'кино_и_сериалы': ['кино', 'cinema', 'movie', 'film', 'сериал', 'serial', 'tv1000', 'paramount', 'sony'],
            'кинозалы': ['кинозал', 'cineman', 'bcu', 'vip', 'premium', 'megahit', 'comedy', 'action', 'thriller'],
            'эфирные': ['первый', 'россия', 'нтв', 'стс', 'тнт', 'рен тв', 'тв3', 'пятница', 'эфирные'],
            'федеральные_плюс': ['федеральные', 'общественные', 'культура', 'спас', 'звезда'],
            'детские': ['детск', 'kids', 'cartoon', 'disney', 'nick', 'карусель', 'мульт'],
            'музыкальные': ['музык', 'music', 'муз тв', 'mtv', 'bridge', 'жар-птица'],
            'новости': ['новост', 'news', 'cnn', 'bbc', 'rt', 'дождь', 'медуза'],
            'познавательные': ['познавательн', 'документальн', 'наука', 'история', 'природа', 'discovery'],
            'развлекательные': ['развлекательн', 'юмор', 'comedy', 'развлечения', 'шоу'],
            'региональные': ['регион', 'областн', 'краев', 'республик', 'москв', 'спб'],
            'религиозные': ['религиозн', 'православн', 'церковн', 'бог', 'вера'],
            'радио': ['радио', 'radio', 'fm', 'am'],
            '18+': ['18+', 'adult', 'xxx', 'порно', 'эротика']
        }

    def parse_playlist(self):
        """Парсит плейлист и создает категории"""
        logger.info("🔄 Парсим плейлист...")
        
        try:
            response = requests.get(self.donor_url, timeout=30)
            response.raise_for_status()
            content = response.text
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки плейлиста: {e}")
            return False

        # Парсим каналы
        channels = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXTINF:'):
                extinf = line
                # Ищем URL в следующих строках
                j = i + 1
                while j < len(lines):
                    url_line = lines[j].strip()
                    if url_line.startswith('http'):
                        channels.append({
                            'extinf': extinf,
                            'url': url_line
                        })
                        i = j + 1
                        break
                    elif url_line == '' or url_line.startswith('#'):
                        j += 1
                    else:
                        i += 1
                        break
                else:
                    i += 1
            else:
                i += 1

        logger.info(f"📺 Найдено каналов: {len(channels)}")

        # Распределяем по категориям
        category_files = {}
        for category, keywords in self.categories.items():
            category_files[category] = []

        for channel in channels:
            # Извлекаем название из EXTINF
            title_match = re.search(r'tvg-name="([^"]*)"', channel['extinf'])
            if title_match:
                title = title_match.group(1).lower()
            else:
                # Если нет tvg-name, берем из названия после запятой
                title_part = channel['extinf'].split(',', 1)
                if len(title_part) > 1:
                    title = title_part[1].strip().lower()
                else:
                    title = ""

            # Определяем категорию
            assigned = False
            for category, keywords in self.categories.items():
                for keyword in keywords:
                    if keyword.lower() in title:
                        category_files[category].append(channel)
                        assigned = True
                        break
                if assigned:
                    break

            # Если не определили категорию, добавляем в "разное"
            if not assigned:
                if 'разное' not in category_files:
                    category_files['разное'] = []
                category_files['разное'].append(channel)

        # Создаем файлы категорий
        categories_dir = self.base_dir / "categories"
        categories_dir.mkdir(exist_ok=True)

        for category, channels_list in category_files.items():
            if channels_list:
                file_path = categories_dir / f"{category}.m3u"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("#EXTM3U\n")
                    for channel in channels_list:
                        f.write(f"{channel['extinf']}\n")
                        f.write(f"{channel['url']}\n")
                
                logger.info(f"✅ {category}: {len(channels_list)} каналов")

        return True

    def create_playlist(self):
        """Создает основной плейлист"""
        logger.info("📺 Создание плейлиста...")
        
        try:
            # Читаем все категории и создаем один плейлист
            categories_dir = self.base_dir / "categories"
            if not categories_dir.exists():
                logger.error("Папка categories не найдена!")
                return False

            all_channels = []
            total_channels = 0

            # Читаем все файлы категорий
            for m3u_file in categories_dir.glob("*.m3u"):
                if m3u_file.name.startswith('.'):
                    continue
                    
                logger.info(f"Читаем {m3u_file.name}...")
                
                try:
                    with open(m3u_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Парсим каналы
                    i = 0
                    while i < len(lines):
                        line = lines[i].strip()
                        if line.startswith('#EXTINF:'):
                            extinf = line
                            # Ищем URL в следующих строках (пропускаем пустые строки)
                            j = i + 1
                            while j < len(lines):
                                url_line = lines[j].strip()
                                if url_line.startswith('http'):
                                    all_channels.append({
                                        'extinf': extinf,
                                        'url': url_line
                                    })
                                    total_channels += 1
                                    i = j + 1
                                    break
                                elif url_line == '':
                                    j += 1
                                elif url_line.startswith('#'):
                                    j += 1
                                else:
                                    i += 1
                                    break
                            else:
                                i += 1
                        else:
                            i += 1
                            
                except Exception as e:
                    logger.error(f"Ошибка чтения {m3u_file}: {e}")
                    continue

            # Создаем основной плейлист
            main_playlist = self.base_dir / "televizo_main.m3u"
            with open(main_playlist, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                for channel in all_channels:
                    f.write(f"{channel['extinf']}\n")
                    f.write(f"{channel['url']}\n")

            logger.info(f"✅ Создан плейлист: {total_channels} каналов")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка создания плейлиста: {e}")
            return False

    def git_push(self):
        """Пуш в Git"""
        logger.info("📤 Пуш в Git...")
        
        try:
            # Добавляем все изменения
            subprocess.run(['git', 'add', '.'], check=True, cwd=self.base_dir)
            
            # Проверяем есть ли изменения
            result = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=self.base_dir)
            if result.returncode == 0:
                logger.info("ℹ️ Нет изменений для коммита")
                return True
            
            # Коммит
            commit_msg = f"🤖 Обновление плейлиста {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True, cwd=self.base_dir)
            
            # Пуш
            subprocess.run(['git', 'push'], check=True, cwd=self.base_dir)
            
            logger.info("✅ Изменения запушены в Git")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Ошибка Git: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Исключение Git: {e}")
            return False

    def show_statistics(self):
        """Показывает статистику"""
        logger.info("📊 Статистика:")
        
        # Считаем каналы в плейлисте
        main_playlist = self.base_dir / "televizo_main.m3u"
        if main_playlist.exists():
            with open(main_playlist, 'r', encoding='utf-8') as f:
                content = f.read()
                channel_count = content.count('#EXTINF:')
                logger.info(f"📺 Всего каналов: {channel_count}")
        
        # Считаем категории
        categories_dir = self.base_dir / "categories"
        if categories_dir.exists():
            category_files = list(categories_dir.glob("*.m3u"))
            logger.info(f"📁 Категорий: {len(category_files)}")

    def run(self):
        """Запуск системы"""
        logger.info("🚀 ЗАПУСК IPTV СИСТЕМЫ")
        logger.info("=" * 50)
        
        # Парсим плейлист
        if not self.parse_playlist():
            logger.error("❌ Ошибка парсинга")
            return False
        
        # Создаем плейлист
        if not self.create_playlist():
            logger.error("❌ Ошибка создания плейлиста")
            return False
        
        # Пуш в Git
        self.git_push()
        
        # Показываем статистику
        self.show_statistics()
        
        logger.info("✅ СИСТЕМА ЗАВЕРШЕНА")
        return True

if __name__ == "__main__":
    system = IPTVSystem()
    system.run()