#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Умный парсер плейлистов с обновлением существующих ссылок
Может обновлять URL каналов по названию или добавлять новые
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

class SmartPlaylistParser:
    def __init__(self, config_file='donors_config.json'):
        self.config = self.load_config(config_file)
        self.stats = {
            'total_parsed': 0,
            'added_channels': 0,
            'updated_channels': 0,
            'skipped_channels': 0,
            'categories_updated': set()
        }
    
    def load_config(self, config_file):
        """Загружает конфигурацию из JSON файла"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Добавляем настройки обновления если их нет
            if 'update_settings' not in config:
                config['update_settings'] = {
                    'update_existing_urls': True,
                    'match_by_name': True,
                    'match_similarity_threshold': 0.8,
                    'backup_before_update': True
                }
            
            logger.info(f"Конфигурация загружена из {config_file}")
            return config
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации: {e}")
            return {
                "donors": {},
                "category_mapping": {},
                "settings": {"auto_update": True},
                "update_settings": {
                    "update_existing_urls": True,
                    "match_by_name": True,
                    "match_similarity_threshold": 0.8,
                    "backup_before_update": True
                }
            }
    
    def download_playlist(self, url, timeout=30):
        """Скачивает плейлист с URL"""
        try:
            logger.info(f"Скачиваем плейлист: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # Определяем кодировку
            content = response.content
            encodings = ['utf-8', 'cp1251', 'latin1']
            
            for encoding in encodings:
                try:
                    playlist_content = content.decode(encoding)
                    logger.info(f"Плейлист декодирован с кодировкой {encoding}, размер: {len(playlist_content)} символов")
                    return playlist_content
                except UnicodeDecodeError:
                    continue
            
            # Если ничего не сработало
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
        
        # Извлекаем различные атрибуты
        attributes = {
            'group': r'group-title="([^"]*)"',
            'logo': r'tvg-logo="([^"]*)"',
            'tvg_id': r'tvg-id="([^"]*)"'
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
    
    def normalize_channel_name(self, name):
        """Нормализует название канала для сравнения"""
        # Убираем лишние символы и приводим к нижнему регистру
        normalized = re.sub(r'[^\w\s]', '', name.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def calculate_similarity(self, name1, name2):
        """Вычисляет схожесть названий каналов (простая версия)"""
        norm1 = self.normalize_channel_name(name1)
        norm2 = self.normalize_channel_name(name2)
        
        if norm1 == norm2:
            return 1.0
        
        # Простая проверка на вхождение
        if norm1 in norm2 or norm2 in norm1:
            return 0.8
        
        # Проверка по словам
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if words1 and words2:
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            return intersection / union if union > 0 else 0.0
        
        return 0.0
    
    def load_existing_channels(self, category_file):
        """Загружает существующие каналы из файла категории с их метаданными"""
        if not os.path.exists(category_file):
            return {}
        
        existing_channels = {}  # {url: {'name': name, 'extinf': extinf_line}}
        
        try:
            with open(category_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            current_extinf = None
            for line in lines:
                line = line.strip()
                
                if line.startswith('#EXTINF'):
                    current_extinf = line
                elif line and not line.startswith('#') and current_extinf:
                    # Извлекаем название из EXTINF
                    name_match = re.search(r',([^,]+)$', current_extinf)
                    name = name_match.group(1).strip() if name_match else 'Unknown'
                    
                    existing_channels[line] = {
                        'name': name,
                        'extinf': current_extinf
                    }
                    current_extinf = None
                    
        except Exception as e:
            logger.error(f"Ошибка при чтении {category_file}: {e}")
        
        return existing_channels
    
    def find_matching_channel(self, new_channel, existing_channels):
        """Ищет совпадающий канал по названию"""
        if not self.config.get('update_settings', {}).get('match_by_name', True):
            return None
        
        threshold = self.config.get('update_settings', {}).get('match_similarity_threshold', 0.8)
        new_name = new_channel['name']
        
        best_match = None
        best_similarity = 0.0
        
        for url, channel_info in existing_channels.items():
            existing_name = channel_info['name']
            similarity = self.calculate_similarity(new_name, existing_name)
            
            if similarity >= threshold and similarity > best_similarity:
                best_similarity = similarity
                best_match = url
        
        return best_match
    
    def backup_category_file(self, category_file):
        """Создает бэкап файла категории"""
        if not os.path.exists(category_file):
            return
        
        backup_dir = "backups/categories"
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        category_name = os.path.basename(category_file)
        backup_file = f"{backup_dir}/{category_name}.backup.{timestamp}"
        
        try:
            with open(category_file, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            logger.info(f"Создан бэкап: {backup_file}")
        except Exception as e:
            logger.error(f"Ошибка при создании бэкапа: {e}")
    
    def update_channel_in_category(self, old_url, new_channel, category_file):
        """Обновляет URL канала в файле категории"""
        try:
            # Читаем файл
            with open(category_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Ищем и заменяем URL
            updated_lines = []
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if line == old_url:
                    # Заменяем EXTINF строку (предыдущая строка)
                    if i > 0 and updated_lines[-1].strip().startswith('#EXTINF'):
                        updated_lines[-1] = new_channel['original_extinf'] + '\n'
                    # Заменяем URL
                    updated_lines.append(new_channel['url'] + '\n')
                    logger.info(f"Обновлен URL для канала '{new_channel['name']}': {old_url} -> {new_channel['url']}")
                else:
                    updated_lines.append(lines[i])
                
                i += 1
            
            # Записываем обновленный файл
            with open(category_file, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении канала в {category_file}: {e}")
            return False
    
    def is_channel_filtered(self, channel):
        """Проверяет, нужно ли исключить канал по глобальным фильтрам"""
        filters = self.config.get('global_filters', {})
        
        # Проверяем исключения по названию канала
        exclude_channels = filters.get('exclude_channels', [])
        for exclude_pattern in exclude_channels:
            if exclude_pattern.lower() in channel['name'].lower():
                logger.info(f"Канал '{channel['name']}' исключен по фильтру названия: {exclude_pattern}")
                return True
        
        # Проверяем исключения по URL
        exclude_urls = filters.get('exclude_urls', [])
        for exclude_pattern in exclude_urls:
            if exclude_pattern in channel['url']:
                logger.info(f"Канал '{channel['name']}' исключен по фильтру URL: {exclude_pattern}")
                return True
        
        # Проверяем минимальную длину URL
        min_url_length = filters.get('min_url_length', 10)
        if len(channel['url']) < min_url_length:
            logger.info(f"Канал '{channel['name']}' исключен: URL слишком короткий")
            return True
        
        # Проверяем регулярные выражения
        exclude_patterns = filters.get('exclude_patterns', [])
        for pattern in exclude_patterns:
            if re.search(pattern, channel['name'], re.IGNORECASE):
                logger.info(f"Канал '{channel['name']}' исключен по паттерну: {pattern}")
                return True
        
        return False

    def add_or_update_channel(self, channel, category):
        """Добавляет новый канал или обновляет существующий"""
        # Проверяем глобальные фильтры
        if self.is_channel_filtered(channel):
            self.stats['skipped_channels'] += 1
            return False
            
        category_file = f"categories/{category}.m3u"
        
        # Создаем папку categories если её нет
        os.makedirs("categories", exist_ok=True)
        
        # Загружаем существующие каналы
        existing_channels = self.load_existing_channels(category_file)
        
        # Проверяем точное совпадение URL
        if channel['url'] in existing_channels:
            logger.debug(f"Канал с таким URL уже существует: {channel['name']}")
            self.stats['skipped_channels'] += 1
            return False
        
        # Ищем канал с похожим названием для обновления
        if self.config.get('update_settings', {}).get('update_existing_urls', True):
            matching_url = self.find_matching_channel(channel, existing_channels)
            
            if matching_url:
                # Создаем бэкап если включено
                if self.config.get('update_settings', {}).get('backup_before_update', True):
                    self.backup_category_file(category_file)
                
                # Обновляем существующий канал
                if self.update_channel_in_category(matching_url, channel, category_file):
                    self.stats['updated_channels'] += 1
                    self.stats['categories_updated'].add(category)
                    return True
        
        # Добавляем как новый канал
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
            
            logger.info(f"Добавлен новый канал '{channel['name']}' в категорию '{category}'")
            self.stats['added_channels'] += 1
            self.stats['categories_updated'].add(category)
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении канала в {category_file}: {e}")
            return False
    
    def process_donor_playlist(self, donor_name, donor_config):
        """Обрабатывает один донорский плейлист"""
        if not donor_config.get('enabled', True):
            logger.info(f"Донор {donor_name} отключен")
            return False
        
        logger.info(f"Обрабатываем донора: {donor_name}")
        
        # Скачиваем плейлист
        content = self.download_playlist(donor_config['url'])
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
                # Добавляем или обновляем канал
                self.add_or_update_channel(channel, category)
            else:
                logger.debug(f"Не удалось категоризировать: {channel['name']} ({channel['group']})")
                self.stats['skipped_channels'] += 1
        
        return True
    
    def process_all_donors(self):
        """Обрабатывает всех доноров из конфигурации"""
        logger.info("Начинаем умную обработку всех доноров...")
        
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
        
        # Выводим статистику
        self.print_statistics()
    
    def print_statistics(self):
        """Выводит статистику обработки"""
        logger.info("=" * 60)
        logger.info("СТАТИСТИКА УМНОЙ ОБРАБОТКИ:")
        logger.info(f"Всего распарсено каналов: {self.stats['total_parsed']}")
        logger.info(f"Добавлено новых каналов: {self.stats['added_channels']}")
        logger.info(f"Обновлено существующих каналов: {self.stats['updated_channels']}")
        logger.info(f"Пропущено каналов: {self.stats['skipped_channels']}")
        logger.info(f"Обновлено категорий: {len(self.stats['categories_updated'])}")
        
        if self.stats['categories_updated']:
            logger.info("Обновленные категории:")
            for category in sorted(self.stats['categories_updated']):
                logger.info(f"  - {category}")
        
        logger.info("=" * 60)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Умный парсер IPTV плейлистов с обновлением ссылок')
    parser.add_argument('--config', default='donors_config.json', help='Файл конфигурации')
    parser.add_argument('--no-update', action='store_true', help='Не обновлять существующие ссылки')
    parser.add_argument('--similarity', type=float, default=0.8, help='Порог схожести названий (0.0-1.0)')
    
    args = parser.parse_args()
    
    parser_instance = SmartPlaylistParser(args.config)
    
    if args.no_update:
        parser_instance.config['update_settings']['update_existing_urls'] = False
    
    if args.similarity:
        parser_instance.config['update_settings']['match_similarity_threshold'] = args.similarity
    
    # Обрабатываем всех доноров
    parser_instance.process_all_donors()
    
    print("\n🎉 Умная обработка завершена!")
    print("📁 Проверьте папку 'categories/' для обновленных плейлистов")
    print("💾 Бэкапы сохранены в 'backups/categories/'")

if __name__ == "__main__":
    main()
