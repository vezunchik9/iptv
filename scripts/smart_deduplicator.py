#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Умная система дедупликации каналов
Выбирает лучший поток из дублирующихся каналов
"""

import os
import re
import json
import hashlib
import time
import subprocess
from pathlib import Path
from collections import defaultdict
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SmartDeduplicator:
    def __init__(self, base_dir="/Users/ipont/projects/iptv"):
        self.base_dir = Path(base_dir)
        self.categories_dir = self.base_dir / "categories"
        self.reports_dir = self.base_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Настройки проверки качества
        self.quality_checks = {
            "timeout": 10,
            "max_redirects": 3,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # Критерии оценки качества потока
        self.quality_criteria = {
            "url_quality": {
                "https": 10,
                "http": 5,
                "m3u8": 8,
                "ts": 6,
                "flv": 3,
                "rtmp": 2
            },
            "domain_quality": {
                "cdn": 10,
                "stream": 8,
                "live": 7,
                "iptv": 6,
                "ott": 5,
                "localhost": 1,
                "127.0.0.1": 1
            },
            "resolution_quality": {
                "4k": 10,
                "uhd": 10,
                "fhd": 8,
                "hd": 6,
                "720p": 6,
                "480p": 4,
                "360p": 2
            }
        }

    def normalize_channel_name(self, name):
        """Нормализует название канала для сравнения"""
        # Убираем лишние символы и приводим к нижнему регистру
        normalized = re.sub(r'[^\w\s]', '', name.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Убираем общие суффиксы
        suffixes = ['hd', 'fhd', '4k', 'uhd', 'sd', '+2', '+3', '+0', 'orig', 'original']
        for suffix in suffixes:
            if normalized.endswith(' ' + suffix):
                normalized = normalized[:-len(' ' + suffix)]
        
        return normalized

    def calculate_url_quality_score(self, url):
        """Вычисляет качество URL потока"""
        score = 0
        url_lower = url.lower()
        
        # Проверяем протокол
        for protocol, points in self.quality_criteria["url_quality"].items():
            if protocol in url_lower:
                score += points
                break
        
        # Проверяем домен
        for domain, points in self.quality_criteria["domain_quality"].items():
            if domain in url_lower:
                score += points
        
        # Проверяем разрешение
        for resolution, points in self.quality_criteria["resolution_quality"].items():
            if resolution in url_lower:
                score += points
        
        # Бонус за длину URL (более длинные обычно стабильнее)
        score += min(len(url) / 100, 5)
        
        return score

    def check_stream_availability(self, url):
        """Проверяет доступность потока"""
        try:
            # Быстрая проверка через curl
            cmd = [
                'curl', '-s', '-I', '--max-time', str(self.quality_checks["timeout"]),
                '--max-redirs', str(self.quality_checks["max_redirects"]),
                '-A', self.quality_checks["user_agent"],
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                # Анализируем заголовки
                headers = result.stdout.lower()
                if any(code in headers for code in ['200', '302', '301']):
                    return True
                if 'content-type' in headers and 'video' in headers:
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Ошибка проверки {url}: {e}")
            return False

    def deduplicate_channels(self):
        """Основная функция дедупликации"""
        logger.info("🔄 НАЧИНАЕМ УМНУЮ ДЕДУПЛИКАЦИЮ")
        logger.info("=" * 50)
        
        # Собираем все каналы из всех категорий
        all_channels = []
        
        for category_file in self.categories_dir.glob("*.m3u"):
            if category_file.name == "18+.m3u":
                continue  # Пропускаем 18+ для безопасности
                
            category_name = category_file.stem
            logger.info(f"📂 Обрабатываем категорию: {category_name}")
            
            channels = self.read_channels_from_file(category_file)
            for channel in channels:
                channel['category'] = category_name
                channel['normalized_name'] = self.normalize_channel_name(channel['name'])
                channel['url_quality_score'] = self.calculate_url_quality_score(channel['url'])
                all_channels.append(channel)
        
        logger.info(f"📊 Всего каналов собрано: {len(all_channels)}")
        
        # Группируем по нормализованным названиям
        duplicates = defaultdict(list)
        unique_channels = []
        
        for channel in all_channels:
            normalized = channel['normalized_name']
            if len(normalized) > 3:  # Игнорируем слишком короткие названия
                duplicates[normalized].append(channel)
            else:
                unique_channels.append(channel)
        
        logger.info(f"🔍 Найдено групп дубликатов: {len(duplicates)}")
        
        # Обрабатываем каждую группу дубликатов
        processed_count = 0
        removed_groups = 0
        for normalized_name, channels in duplicates.items():
            if len(channels) > 1:
                logger.info(f"  🔄 Обрабатываем дубликаты: '{normalized_name}' ({len(channels)} каналов)")
                
                # Выбираем лучший канал
                best_channel = self.select_best_channel(channels)
                if best_channel:
                    unique_channels.append(best_channel)
                    processed_count += len(channels) - 1
                    logger.info(f"    ✅ Выбран: {best_channel['name']} (качество: {best_channel['url_quality_score']:.1f})")
                else:
                    processed_count += len(channels)
                    removed_groups += 1
                    logger.info(f"    ❌ Удалена группа: {normalized_name} (все потоки не работают)")
            else:
                # Проверяем единственный канал
                if self.check_stream_availability(channels[0]['url']):
                    unique_channels.append(channels[0])
                else:
                    processed_count += 1
                    logger.info(f"    ❌ Удален нерабочий канал: {channels[0]['name']}")
        
        logger.info(f"📊 Удалено дубликатов: {processed_count}")
        logger.info(f"📊 Итоговое количество каналов: {len(unique_channels)}")
        
        # Создаем новые файлы категорий
        self.create_deduplicated_categories(unique_channels)
        
        # Создаем отчет
        self.create_deduplication_report(duplicates, processed_count)
        
        logger.info("✅ ДЕДУПЛИКАЦИЯ ЗАВЕРШЕНА")

    def select_best_channel(self, channels):
        """Выбирает лучший канал из группы дубликатов"""
        # Сортируем по качеству URL
        channels.sort(key=lambda x: x['url_quality_score'], reverse=True)
        
        # Проверяем доступность топ-3 каналов
        for i, channel in enumerate(channels[:3]):
            logger.debug(f"    🔍 Проверяем доступность: {channel['name']}")
            if self.check_stream_availability(channel['url']):
                logger.debug(f"    ✅ Поток работает: {channel['name']}")
                return channel
            else:
                logger.debug(f"    ❌ Поток не работает: {channel['name']}")
        
        # Если ни один не работает - НЕ ВОЗВРАЩАЕМ НИЧЕГО
        logger.warning(f"    ❌ ВСЕ ПОТОКИ НЕ РАБОТАЮТ - УДАЛЯЕМ ГРУППУ")
        return None

    def read_channels_from_file(self, file_path):
        """Читает каналы из M3U файла"""
        channels = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('#EXTINF:'):
                    if i + 1 < len(lines):
                        url = lines[i + 1].strip()
                        if url and not url.startswith('#'):
                            name_match = re.search(r',(.+)$', line)
                            if name_match:
                                name = name_match.group(1).strip()
                                channels.append({
                                    'name': name,
                                    'url': url,
                                    'extinf': line
                                })
                i += 1
        except Exception as e:
            logger.error(f"Ошибка чтения файла {file_path}: {e}")
        
        return channels

    def create_deduplicated_categories(self, unique_channels):
        """Создает новые файлы категорий без дубликатов"""
        logger.info("📝 СОЗДАЕМ ОЧИЩЕННЫЕ КАТЕГОРИИ")
        
        # Группируем по категориям
        categories = defaultdict(list)
        for channel in unique_channels:
            categories[channel['category']].append(channel)
        
        # Создаем файлы
        for category, channels in categories.items():
            file_path = self.categories_dir / f"{category}.m3u"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                f.write(f"# {self.get_category_emoji(category)} {category.title()}\n")
                f.write(f"# Каналов: {len(channels)}\n")
                f.write(f"# Обновлено: {self.get_current_time()}\n")
                f.write(f"# Дедупликация: активна\n")
                f.write("\n")
                
                for channel in channels:
                    f.write(f"{channel['extinf']}\n")
                    f.write(f"{channel['url']}\n")
                    f.write("\n")
            
            logger.info(f"  📂 {category}: {len(channels)} каналов")

    def get_category_emoji(self, category):
        """Возвращает эмодзи для категории"""
        emojis = {
            "федеральные": "📺",
            "региональные": "🏘️",
            "новости": "📰",
            "спортивные": "⚽",
            "музыкальные": "🎵",
            "детские": "👶",
            "познавательные": "🧠",
            "развлекательные": "🎉",
            "кино_и_сериалы": "🎬",
            "религиозные": "⛪",
            "инфо": "ℹ️",
            "радио": "📻",
            "18+": "🔞",
            "fashion": "👗",
            "relax": "🧘",
            "кинозалы": "🎭"
        }
        return emojis.get(category, "📺")

    def create_deduplication_report(self, duplicates, removed_count):
        """Создает отчет о дедупликации"""
        report = {
            "timestamp": self.get_current_time(),
            "total_duplicates_removed": removed_count,
            "duplicate_groups": len(duplicates),
            "groups_details": {}
        }
        
        for normalized_name, channels in duplicates.items():
            if len(channels) > 1:
                report["groups_details"][normalized_name] = {
                    "count": len(channels),
                    "channels": [
                        {
                            "name": ch['name'],
                            "url": ch['url'],
                            "quality_score": ch['url_quality_score'],
                            "category": ch['category']
                        } for ch in channels
                    ]
                }
        
        # Сохраняем отчет
        report_file = self.reports_dir / f"deduplication_report_{int(time.time())}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📊 Отчет сохранен: {report_file}")

    def get_current_time(self):
        """Возвращает текущее время в нужном формате"""
        from datetime import datetime
        return datetime.now().strftime("%d.%m.%Y %H:%M")

def main():
    deduplicator = SmartDeduplicator()
    deduplicator.deduplicate_channels()

if __name__ == "__main__":
    main()
