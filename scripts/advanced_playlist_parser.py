#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Продвинутый парсер плейлистов с конфигурацией и валидацией
"""

import requests
import re
import json
import os
import asyncio
import aiohttp
from datetime import datetime
from urllib.parse import urlparse
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedPlaylistParser:
    def __init__(self, config_file='donors_config.json'):
        self.config = self.load_config(config_file)
        self.stats = {
            'total_parsed': 0,
            'added_channels': 0,
            'skipped_channels': 0,
            'invalid_channels': 0,
            'categories_updated': set(),
            'donors_processed': 0,
            'donors_failed': 0
        }
    
    def load_config(self, config_file):
        """Загружает конфигурацию из JSON файла"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Конфигурация загружена из {config_file}")
            return config
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации: {e}")
            # Возвращаем базовую конфигурацию
            return {
                "donors": {},
                "category_mapping": {},
                "settings": {"auto_update": True}
            }
    
    def download_playlist(self, url, timeout=30):
        """Скачивает плейлист с URL"""
        try:
            logger.info(f"Скачиваем плейлист: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # Определяем кодировку
            content = response.content
            encodings = ['utf-8', 'cp1251', 'latin1', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    playlist_content = content.decode(encoding)
                    logger.info(f"Плейлист декодирован с кодировкой {encoding}, размер: {len(playlist_content)} символов")
                    return playlist_content
                except UnicodeDecodeError:
                    continue
            
            # Если ничего не сработало, используем errors='ignore'
            playlist_content = content.decode('utf-8', errors='ignore')
            logger.warning("Использована принудительная декодировка с игнорированием ошибок")
            return playlist_content
            
        except Exception as e:
            logger.error(f"Ошибка при скачивании плейлиста {url}: {e}")
            return None
    
    def parse_m3u_playlist(self, content):
        """Парсит M3U плейлист и извлекает каналы"""
        channels = []
        lines = content.splitlines()
        current_extinf = None
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            if line.startswith('#EXTINF'):
                current_extinf = line
            elif line and not line.startswith('#') and current_extinf:
                try:
                    # Парсим информацию о канале
                    channel_info = self.parse_extinf(current_extinf)
                    channel_info['url'] = line
                    channel_info['line_number'] = line_num
                    
                    # Базовая валидация URL
                    if self.is_valid_url(line):
                        channels.append(channel_info)
                    else:
                        logger.debug(f"Невалидный URL на строке {line_num}: {line}")
                        self.stats['invalid_channels'] += 1
                        
                except Exception as e:
                    logger.debug(f"Ошибка при парсинге канала на строке {line_num}: {e}")
                    self.stats['invalid_channels'] += 1
                
                current_extinf = None
        
        logger.info(f"Распарсено каналов: {len(channels)}, невалидных: {self.stats['invalid_channels']}")
        return channels
    
    def is_valid_url(self, url):
        """Проверяет валидность URL"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except:
            return False
    
    def parse_extinf(self, extinf_line):
        """Парсит строку #EXTINF и извлекает метаданные"""
        info = {
            'name': '',
            'group': '',
            'logo': '',
            'tvg_id': '',
            'catchup': '',
            'original_extinf': extinf_line
        }
        
        # Извлекаем название канала (после последней запятой)
        name_match = re.search(r',([^,]+)$', extinf_line)
        if name_match:
            info['name'] = name_match.group(1).strip()
        
        # Извлекаем различные атрибуты
        attributes = {
            'group': r'group-title="([^"]*)"',
            'logo': r'tvg-logo="([^"]*)"',
            'tvg_id': r'tvg-id="([^"]*)"',
            'catchup': r'catchup="([^"]*)"'
        }
        
        for attr, pattern in attributes.items():
            match = re.search(pattern, extinf_line)
            if match:
                info[attr] = match.group(1).strip()
        
        return info
    
    def categorize_channel(self, channel):
        """Определяет категорию канала на основе конфигурации"""
        name = channel['name'].lower()
        group = channel['group'].lower()
        text_to_check = f"{name} {group}"
        
        # Проверяем каждую категорию из конфигурации
        for category, rules in self.config.get('category_mapping', {}).items():
            keywords = rules.get('keywords', [])
            exclude = rules.get('exclude', [])
            
            # Проверяем ключевые слова
            keyword_found = False
            for keyword in keywords:
                if keyword.lower() in text_to_check:
                    keyword_found = True
                    break
            
            if keyword_found:
                # Проверяем исключения
                excluded = False
                for exclude_word in exclude:
                    if exclude_word.lower() in text_to_check:
                        excluded = True
                        break
                
                if not excluded:
                    return category
        
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
        
        # Проверяем дубликаты
        if self.config.get('settings', {}).get('check_duplicates', True):
            if channel['url'] in existing_urls:
                logger.debug(f"Канал уже существует: {channel['name']}")
                self.stats['skipped_channels'] += 1
                return False
        
        # Проверяем лимит каналов в категории
        max_channels = self.config.get('settings', {}).get('max_channels_per_category', 1000)
        if len(existing_urls) >= max_channels:
            logger.warning(f"Достигнут лимит каналов в категории {category}: {max_channels}")
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
    
    async def validate_channel_url(self, session, url, timeout=5):
        """Асинхронно проверяет доступность URL канала"""
        try:
            async with session.head(url, timeout=timeout) as response:
                return response.status in [200, 206, 301, 302, 307, 308]
        except:
            return False
    
    async def validate_channels(self, channels, max_concurrent=10):
        """Асинхронно валидирует список каналов"""
        if not self.config.get('settings', {}).get('validate_urls', False):
            return channels
        
        logger.info(f"Валидируем {len(channels)} каналов...")
        
        connector = aiohttp.TCPConnector(limit=max_concurrent)
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            for channel in channels:
                task = self.validate_channel_url(session, channel['url'])
                tasks.append((channel, task))
            
            valid_channels = []
            for channel, task in tasks:
                try:
                    is_valid = await task
                    if is_valid:
                        valid_channels.append(channel)
                    else:
                        self.stats['invalid_channels'] += 1
                except:
                    self.stats['invalid_channels'] += 1
        
        logger.info(f"Валидных каналов: {len(valid_channels)}")
        return valid_channels
    
    def process_donor_playlist(self, donor_name, donor_config):
        """Обрабатывает один донорский плейлист"""
        if not donor_config.get('enabled', True):
            logger.info(f"Донор {donor_name} отключен")
            return False
        
        logger.info(f"Обрабатываем донора: {donor_name}")
        
        # Скачиваем плейлист
        content = self.download_playlist(donor_config['url'])
        if not content:
            self.stats['donors_failed'] += 1
            return False
        
        # Парсим каналы
        channels = self.parse_m3u_playlist(content)
        self.stats['total_parsed'] += len(channels)
        
        # Валидируем каналы если включено
        if self.config.get('settings', {}).get('validate_urls', False):
            channels = asyncio.run(self.validate_channels(channels))
        
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
        
        self.stats['donors_processed'] += 1
        return True
    
    def process_all_donors(self):
        """Обрабатывает всех доноров из конфигурации"""
        logger.info("Начинаем обработку всех доноров...")
        
        donors = self.config.get('donors', {})
        if not donors:
            logger.warning("Нет доноров в конфигурации")
            return
        
        # Сортируем доноров по приоритету
        sorted_donors = sorted(donors.items(), key=lambda x: x[1].get('priority', 999))
        
        for donor_name, donor_config in sorted_donors:
            try:
                self.process_donor_playlist(donor_name, donor_config)
            except Exception as e:
                logger.error(f"Ошибка при обработке донора {donor_name}: {e}")
                self.stats['donors_failed'] += 1
        
        # Обновляем заголовки категорий
        self.update_category_headers()
        
        # Выводим статистику
        self.print_statistics()
    
    def print_statistics(self):
        """Выводит статистику обработки"""
        logger.info("=" * 60)
        logger.info("СТАТИСТИКА ОБРАБОТКИ ПЛЕЙЛИСТОВ:")
        logger.info(f"Доноров обработано: {self.stats['donors_processed']}")
        logger.info(f"Доноров с ошибками: {self.stats['donors_failed']}")
        logger.info(f"Всего распарсено каналов: {self.stats['total_parsed']}")
        logger.info(f"Добавлено новых каналов: {self.stats['added_channels']}")
        logger.info(f"Пропущено каналов: {self.stats['skipped_channels']}")
        logger.info(f"Невалидных каналов: {self.stats['invalid_channels']}")
        logger.info(f"Обновлено категорий: {len(self.stats['categories_updated'])}")
        
        if self.stats['categories_updated']:
            logger.info("Обновленные категории:")
            for category in sorted(self.stats['categories_updated']):
                category_file = f"categories/{category}.m3u"
                if os.path.exists(category_file):
                    with open(category_file, 'r', encoding='utf-8') as f:
                        channel_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
                    logger.info(f"  - {category}: {channel_count} каналов")
        
        logger.info("=" * 60)
    
    def add_donor(self, name, url, enabled=True, priority=999):
        """Добавляет нового донора в конфигурацию"""
        if 'donors' not in self.config:
            self.config['donors'] = {}
        
        self.config['donors'][name] = {
            'url': url,
            'enabled': enabled,
            'priority': priority,
            'description': f'Добавлен автоматически {datetime.now().strftime("%d.%m.%Y")}'
        }
        
        # Сохраняем конфигурацию
        try:
            with open('donors_config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"Добавлен новый донор: {name} -> {url}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении конфигурации: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Продвинутый парсер IPTV плейлистов')
    parser.add_argument('--config', default='donors_config.json', help='Файл конфигурации')
    parser.add_argument('--validate', action='store_true', help='Валидировать URL каналов')
    parser.add_argument('--add-donor', nargs=2, metavar=('NAME', 'URL'), help='Добавить нового донора')
    
    args = parser.parse_args()
    
    parser_instance = AdvancedPlaylistParser(args.config)
    
    if args.validate:
        parser_instance.config['settings']['validate_urls'] = True
    
    if args.add_donor:
        name, url = args.add_donor
        parser_instance.add_donor(name, url)
        return
    
    # Обрабатываем всех доноров
    parser_instance.process_all_donors()
    
    print("\n🎉 Обработка завершена!")
    print("📁 Проверьте папку 'categories/' для обновленных плейлистов")

if __name__ == "__main__":
    main()
