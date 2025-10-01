#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ БЫСТРАЯ ДЕДУПЛИКАЦИЯ ПО ИСТОЧНИКАМ
Оставляет только 3 лучших источника + 18+ + последний с 4000+ каналов
"""

import os
import re
import json
import time
from pathlib import Path
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FastDeduplicator:
    def __init__(self, base_dir="/Users/ipont/projects/iptv"):
        self.base_dir = Path(base_dir)
        self.categories_dir = self.base_dir / "categories"
        self.reports_dir = self.base_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Приоритетные источники (оставляем только эти)
        self.priority_sources = [
            "iptvshared",  # IPTVSHARED (TAPTV_PREMIUM)
            "18+"          # 18+ контент
        ]
        
        # Критерии качества URL
        self.url_quality = {
            "https": 10,
            "http": 5,
            "m3u8": 8,
            "ts": 6,
            "rtmp": 2
        }
    
    def analyze_sources(self):
        """Анализирует источники каналов"""
        logger.info("🔍 Анализируем источники...")
        
        source_stats = defaultdict(lambda: {
            'count': 0,
            'categories': set(),
            'channels': []
        })
        
        for category_file in self.categories_dir.glob("*.m3u"):
            category_name = category_file.stem
            logger.info(f"📂 Анализируем: {category_name}")
            
            channels = self.read_channels_from_file(category_file)
            
            for channel in channels:
                # Определяем источник по URL
                source = self.detect_source(channel['url'])
                
                source_stats[source]['count'] += 1
                source_stats[source]['categories'].add(category_name)
                source_stats[source]['channels'].append({
                    'name': channel['name'],
                    'url': channel['url'],
                    'category': category_name
                })
        
        # Выводим статистику
        logger.info("\n" + "="*60)
        logger.info("📊 СТАТИСТИКА ИСТОЧНИКОВ")
        logger.info("="*60)
        
        sorted_sources = sorted(source_stats.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for source, stats in sorted_sources:
            logger.info(f"{source:20} | {stats['count']:5} каналов | {len(stats['categories']):2} категорий")
        
        logger.info("="*60)
        
        return source_stats
    
    def detect_source(self, url):
        """Определяет источник по URL"""
        url_lower = url.lower()
        
        # Проверяем IPTVSHARED источники
        if 'iptvshared' in url_lower or 'taptv' in url_lower or '5.129.242.227' in url_lower:
            return 'iptvshared'
        elif '18+' in url_lower or 'adult' in url_lower or 'porn' in url_lower:
            return '18+'
        elif 'githubusercontent.com' in url_lower and 'iptv' in url_lower:
            return 'iptvshared'  # GitHub IPTV списки
        else:
            # Определяем по домену
            domain = url.split('/')[2] if '://' in url else 'unknown'
            return domain.split('.')[-2] if '.' in domain else 'unknown'
    
    def read_channels_from_file(self, file_path):
        """Читает каналы из M3U файла"""
        channels = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            current_name = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('#EXTINF'):
                    # Извлекаем название
                    parts = line.split(',', 1)
                    if len(parts) > 1:
                        current_name = parts[1].strip()
                elif line and not line.startswith('#'):
                    if current_name:
                        channels.append({
                            'name': current_name,
                            'url': line
                        })
                    current_name = None
            
        except Exception as e:
            logger.error(f"Ошибка чтения {file_path}: {e}")
        
        return channels
    
    def calculate_url_quality(self, url):
        """Вычисляет качество URL"""
        score = 0
        url_lower = url.lower()
        
        for pattern, points in self.url_quality.items():
            if pattern in url_lower:
                score += points
                break
        
        return score
    
    def select_best_channels(self, source_stats):
        """Выбирает лучшие каналы из приоритетных источников"""
        logger.info("🎯 Выбираем лучшие каналы...")
        
        selected_channels = []
        total_selected = 0
        
        # 1. Оставляем IPTVSHARED (основной)
        if 'iptvshared' in source_stats:
            iptvshared_channels = source_stats['iptvshared']['channels']
            selected_channels.extend(iptvshared_channels)
            total_selected += len(iptvshared_channels)
            logger.info(f"✅ IPTVSHARED: {len(iptvshared_channels)} каналов")
        
        # 2. Оставляем 18+ (если есть)
        if '18+' in source_stats:
            adult_channels = source_stats['18+']['channels']
            selected_channels.extend(adult_channels)
            total_selected += len(adult_channels)
            logger.info(f"✅ 18+: {len(adult_channels)} каналов")
        
        # 3. Если IPTVSHARED мало каналов, добавляем самый большой источник
        if 'iptvshared' in source_stats and source_stats['iptvshared']['count'] < 100:
            sorted_sources = sorted(
                [(s, stats) for s, stats in source_stats.items() 
                 if s not in ['iptvshared', '18+']], 
                key=lambda x: x[1]['count'], 
                reverse=True
            )
            
            if sorted_sources:
                big_source, big_stats = sorted_sources[0]
                big_channels = big_stats['channels']
                selected_channels.extend(big_channels)
                total_selected += len(big_channels)
                logger.info(f"✅ {big_source}: {len(big_channels)} каналов (дополнительный)")
        
        logger.info(f"📊 Итого выбрано: {total_selected} каналов")
        return selected_channels
    
    def deduplicate_by_name(self, channels):
        """Быстрая дедупликация по названиям (без проверки потоков)"""
        logger.info("🔄 Быстрая дедупликация по названиям...")
        
        # Группируем по нормализованным названиям
        name_groups = defaultdict(list)
        
        for channel in channels:
            normalized = self.normalize_name(channel['name'])
            if len(normalized) > 3:
                name_groups[normalized].append(channel)
        
        # Выбираем лучший из каждой группы
        unique_channels = []
        duplicates_removed = 0
        
        for normalized_name, group in name_groups.items():
            if len(group) > 1:
                # Сортируем по качеству URL
                group.sort(key=lambda x: self.calculate_url_quality(x['url']), reverse=True)
                unique_channels.append(group[0])  # Берем лучший
                duplicates_removed += len(group) - 1
            else:
                unique_channels.append(group[0])
        
        logger.info(f"🗑️ Удалено дубликатов: {duplicates_removed}")
        logger.info(f"📊 Уникальных каналов: {len(unique_channels)}")
        
        return unique_channels
    
    def normalize_name(self, name):
        """Нормализует название канала"""
        # Убираем лишние символы
        normalized = re.sub(r'[^\w\s]', '', name.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Убираем суффиксы качества
        suffixes = ['hd', 'fhd', '4k', 'uhd', 'sd', '+2', '+3', 'orig']
        for suffix in suffixes:
            if normalized.endswith(' ' + suffix):
                normalized = normalized[:-len(' ' + suffix)]
        
        return normalized
    
    def create_new_categories(self, channels):
        """Создает новые категории из выбранных каналов"""
        logger.info("📁 Создаем новые категории...")
        
        # Группируем по категориям
        category_groups = defaultdict(list)
        
        for channel in channels:
            category = channel.get('category', 'общие')
            category_groups[category].append(channel)
        
        # Создаем файлы категорий
        for category, cat_channels in category_groups.items():
            if not cat_channels:
                continue
                
            file_path = self.categories_dir / f"{category}.m3u"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('#EXTM3U\n')
                for channel in cat_channels:
                    f.write(f"#EXTINF:-1,{channel['name']}\n")
                    f.write(f"{channel['url']}\n")
            
            logger.info(f"✅ {category}: {len(cat_channels)} каналов")
    
    def create_report(self, source_stats, selected_channels):
        """Создает отчет о дедупликации"""
        # Конвертируем sets в lists для JSON
        serializable_stats = {}
        for source, stats in source_stats.items():
            serializable_stats[source] = {
                'count': stats['count'],
                'categories': list(stats['categories']),
                'channels_count': len(stats['channels'])
            }
        
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'method': 'fast_deduplication',
            'sources_analyzed': len(source_stats),
            'channels_selected': len(selected_channels),
            'sources_kept': ['iptvshared', '18+'],
            'source_stats': serializable_stats
        }
        
        report_path = self.reports_dir / f"fast_dedup_report_{int(time.time())}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📊 Отчет сохранен: {report_path}")
    
    def run(self):
        """Запускает быструю дедупликацию"""
        logger.info("⚡ БЫСТРАЯ ДЕДУПЛИКАЦИЯ")
        logger.info("=" * 50)
        
        start_time = time.time()
        
        # 1. Анализируем источники
        source_stats = self.analyze_sources()
        
        # 2. Выбираем лучшие каналы
        selected_channels = self.select_best_channels(source_stats)
        
        # 3. Дедуплицируем по названиям
        unique_channels = self.deduplicate_by_name(selected_channels)
        
        # 4. Создаем новые категории
        self.create_new_categories(unique_channels)
        
        # 5. Создаем отчет
        self.create_report(source_stats, unique_channels)
        
        elapsed = time.time() - start_time
        
        logger.info("\n" + "="*60)
        logger.info("✅ БЫСТРАЯ ДЕДУПЛИКАЦИЯ ЗАВЕРШЕНА")
        logger.info("="*60)
        logger.info(f"⏱️  Время выполнения: {elapsed:.1f} секунд")
        logger.info(f"📊 Каналов выбрано: {len(unique_channels)}")
        logger.info(f"🚀 Скорость: {len(unique_channels)/elapsed:.1f} каналов/сек")
        logger.info("="*60)

def main():
    deduplicator = FastDeduplicator()
    deduplicator.run()

if __name__ == "__main__":
    main()
