#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматический парсер и интегратор IPTV плейлистов
Парсит потоки с донорских плейлистов и добавляет в свои категории
"""

import requests
import re
import json
import os
from datetime import datetime
from urllib.parse import urlparse
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PlaylistParser:
    def __init__(self):
        self.donors = {
            'IPTVSHARED': 'https://raw.githubusercontent.com/IPTVSHARED/iptv/refs/heads/main/IPTV_SHARED.m3u'
        }
        
        # Маппинг категорий - как донорские группы соответствуют нашим категориям
        self.category_mapping = {
            # Спортивные
            'спортивные': ['спорт', 'sport', 'футбол', 'хоккей', 'баскетбол', 'теннис', 'бокс', 'eurosport', 'match'],
            
            # Кино и сериалы
            'кино_и_сериалы': ['кино', 'cinema', 'movie', 'film', 'сериал', 'serial', 'tv1000', 'paramount', 'sony'],
            
            # Кинозалы
            'кинозалы': ['кинозал', 'cineman', 'bcu', 'vip', 'premium', 'megahit', 'comedy'],
            'кинозалы_2': ['action', 'thriller', 'fantastic', 'romantic', 'stars'],
            'кинозалы_3': ['catastrophe', 'vhs', 'marvel', 'melodrama'],
            
            # Эфирные
            'эфирные': ['первый', 'россия', 'нтв', 'стс', 'тнт', 'рен тв', 'тв3', 'пятница', 'эфирные'],
            
            # Федеральные
            'федеральные_плюс': ['федеральные', 'общественные', 'культура', 'спас', 'звезда'],
            
            # Детские
            'детские': ['детск', 'kids', 'cartoon', 'disney', 'nick', 'карусель', 'мульт'],
            
            # Музыкальные
            'музыкальные': ['музык', 'music', 'муз тв', 'mtv', 'bridge', 'жар-птица'],
            
            # Новости
            'новости': ['новост', 'news', 'рбк', 'rt', 'cnn', 'bbc', 'дождь', 'тасс'],
            
            # Познавательные
            'познавательные': ['discovery', 'national geographic', 'animal planet', 'history', 'наука', 'познават'],
            
            # Развлекательные
            'развлекательные': ['развлекат', 'entertainment', 'comedy', 'юмор', 'перец', 'че'],
            
            # Региональные
            'региoнальные': ['региональ', 'local', 'область', 'край', 'республика'],
            
            # Религиозные
            'религиозные': ['религ', 'спас', 'союз', '3 angels', 'радость моя'],
            
            # Радио
            'радио': ['радио', 'radio', 'fm', 'музыка'],
            
            # 18+
            '18+': ['18+', 'xxx', 'adult', 'erotic', 'playboy', 'brazzers'],
            
            # Инфо
            'инфо': ['инфо', 'info', 'реклама', 'поддержка', 'обновление'],
            
            # Relax
            'relax': ['relax', 'природа', 'камин', 'аквариум', 'пейзаж'],
            
            # Fashion
            'fashion': ['fashion', 'мода', 'стиль', 'красота']
        }
        
        self.stats = {
            'total_parsed': 0,
            'added_channels': 0,
            'skipped_channels': 0,
            'categories_updated': set()
        }
    
    def download_playlist(self, url):
        """Скачивает плейлист с URL"""
        try:
            logger.info(f"Скачиваем плейлист: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Определяем кодировку
            content = response.content
            try:
                playlist_content = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    playlist_content = content.decode('cp1251')
                except UnicodeDecodeError:
                    playlist_content = content.decode('latin1')
            
            logger.info(f"Плейлист скачан, размер: {len(playlist_content)} символов")
            return playlist_content
            
        except Exception as e:
            logger.error(f"Ошибка при скачивании плейлиста {url}: {e}")
            return None
    
    def parse_m3u_playlist(self, content):
        """Парсит M3U плейлист и извлекает каналы"""
        channels = []
        lines = content.splitlines()
        current_extinf = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('#EXTINF'):
                current_extinf = line
            elif line and not line.startswith('#') and current_extinf:
                # Парсим информацию о канале
                channel_info = self.parse_extinf(current_extinf)
                channel_info['url'] = line
                channels.append(channel_info)
                current_extinf = None
        
        logger.info(f"Распарсено каналов: {len(channels)}")
        return channels
    
    def parse_extinf(self, extinf_line):
        """Парсит строку #EXTINF и извлекает метаданные"""
        info = {
            'name': '',
            'group': '',
            'logo': '',
            'tvg_id': '',
            'original_extinf': extinf_line
        }
        
        # Извлекаем название канала (после последней запятой)
        name_match = re.search(r',([^,]+)$', extinf_line)
        if name_match:
            info['name'] = name_match.group(1).strip()
        
        # Извлекаем группу
        group_match = re.search(r'group-title="([^"]*)"', extinf_line)
        if group_match:
            info['group'] = group_match.group(1).strip()
        
        # Извлекаем логотип
        logo_match = re.search(r'tvg-logo="([^"]*)"', extinf_line)
        if logo_match:
            info['logo'] = logo_match.group(1).strip()
        
        # Извлекаем tvg-id
        tvg_id_match = re.search(r'tvg-id="([^"]*)"', extinf_line)
        if tvg_id_match:
            info['tvg_id'] = tvg_id_match.group(1).strip()
        
        return info
    
    def categorize_channel(self, channel):
        """Определяет категорию канала на основе названия и группы"""
        name = channel['name'].lower()
        group = channel['group'].lower()
        text_to_check = f"{name} {group}"
        
        # Проверяем каждую категорию
        for category, keywords in self.category_mapping.items():
            for keyword in keywords:
                if keyword.lower() in text_to_check:
                    return category
        
        # Если не нашли подходящую категорию, возвращаем None
        return None
    
    def load_existing_channels(self, category_file):
        """Загружает существующие каналы из файла категории"""
        if not os.path.exists(category_file):
            return set()
        
        existing_urls = set()
        try:
            with open(category_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Извлекаем все URL из файла
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        existing_urls.add(line)
        except Exception as e:
            logger.error(f"Ошибка при чтении {category_file}: {e}")
        
        return existing_urls
    
    def add_channel_to_category(self, channel, category):
        """Добавляет канал в файл категории"""
        category_file = f"categories/{category}.m3u"
        
        # Создаем папку categories если её нет
        os.makedirs("categories", exist_ok=True)
        
        # Загружаем существующие каналы
        existing_urls = self.load_existing_channels(category_file)
        
        # Проверяем, есть ли уже такой URL
        if channel['url'] in existing_urls:
            logger.debug(f"Канал уже существует: {channel['name']}")
            self.stats['skipped_channels'] += 1
            return False
        
        # Добавляем канал
        try:
            # Если файл не существует, создаем заголовок
            if not os.path.exists(category_file):
                with open(category_file, 'w', encoding='utf-8') as f:
                    f.write("#EXTM3U\n")
                    f.write(f"# Категория: {category}\n")
                    f.write("# Автоматически обновлено\n\n")
            
            # Добавляем канал в конец файла
            with open(category_file, 'a', encoding='utf-8') as f:
                f.write(f"{channel['original_extinf']}\n")
                f.write(f"{channel['url']}\n\n")
            
            logger.info(f"Добавлен канал '{channel['name']}' в категорию '{category}'")
            self.stats['added_channels'] += 1
            self.stats['categories_updated'].add(category)
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении канала в {category_file}: {e}")
            return False
    
    def update_category_headers(self):
        """Обновляет заголовки файлов категорий с количеством каналов"""
        for category in self.stats['categories_updated']:
            category_file = f"categories/{category}.m3u"
            if os.path.exists(category_file):
                try:
                    # Читаем файл
                    with open(category_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Считаем каналы
                    channel_count = sum(1 for line in lines if line.strip() and not line.startswith('#'))
                    
                    # Обновляем заголовок
                    with open(category_file, 'w', encoding='utf-8') as f:
                        f.write("#EXTM3U\n")
                        f.write(f"# Категория: {category}\n")
                        f.write(f"# Каналов: {channel_count}\n")
                        f.write(f"# Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n")
                        
                        # Записываем каналы (пропускаем старые заголовки)
                        skip_headers = True
                        for line in lines:
                            if line.startswith('#EXTINF'):
                                skip_headers = False
                            if not skip_headers:
                                f.write(line)
                
                except Exception as e:
                    logger.error(f"Ошибка при обновлении заголовка {category_file}: {e}")
    
    def process_donor_playlist(self, donor_name, url):
        """Обрабатывает один донорский плейлист"""
        logger.info(f"Обрабатываем донора: {donor_name}")
        
        # Скачиваем плейлист
        content = self.download_playlist(url)
        if not content:
            return False
        
        # Парсим каналы
        channels = self.parse_m3u_playlist(content)
        self.stats['total_parsed'] += len(channels)
        
        # Обрабатываем каждый канал
        for channel in channels:
            # Определяем категорию
            category = self.categorize_channel(channel)
            
            if category:
                # Добавляем в соответствующую категорию
                self.add_channel_to_category(channel, category)
            else:
                logger.debug(f"Не удалось категоризировать: {channel['name']} ({channel['group']})")
                self.stats['skipped_channels'] += 1
        
        return True
    
    def process_all_donors(self):
        """Обрабатывает всех доноров"""
        logger.info("Начинаем обработку всех доноров...")
        
        for donor_name, url in self.donors.items():
            try:
                self.process_donor_playlist(donor_name, url)
            except Exception as e:
                logger.error(f"Ошибка при обработке донора {donor_name}: {e}")
        
        # Обновляем заголовки категорий
        self.update_category_headers()
        
        # Выводим статистику
        self.print_statistics()
    
    def print_statistics(self):
        """Выводит статистику обработки"""
        logger.info("=" * 50)
        logger.info("СТАТИСТИКА ОБРАБОТКИ:")
        logger.info(f"Всего распарсено каналов: {self.stats['total_parsed']}")
        logger.info(f"Добавлено новых каналов: {self.stats['added_channels']}")
        logger.info(f"Пропущено каналов: {self.stats['skipped_channels']}")
        logger.info(f"Обновлено категорий: {len(self.stats['categories_updated'])}")
        
        if self.stats['categories_updated']:
            logger.info("Обновленные категории:")
            for category in sorted(self.stats['categories_updated']):
                logger.info(f"  - {category}")
        
        logger.info("=" * 50)
    
    def add_donor(self, name, url):
        """Добавляет нового донора"""
        self.donors[name] = url
        logger.info(f"Добавлен новый донор: {name} -> {url}")

def main():
    parser = PlaylistParser()
    
    # Обрабатываем всех доноров
    parser.process_all_donors()
    
    print("\n🎉 Обработка завершена!")
    print("📁 Проверьте папку 'categories/' для обновленных плейлистов")

if __name__ == "__main__":
    main()
