#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Умный консолидатор категорий
Устраняет дублирование и правильно группирует каналы
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SmartCategoryConsolidator:
    def __init__(self, base_dir="/Users/ipont/projects/iptv"):
        self.base_dir = Path(base_dir)
        self.categories_dir = self.base_dir / "categories"
        
        # Определяем финальные категории (без дублей)
        self.final_categories = {
            # Основные категории
            "федеральные": "📺 Федеральные каналы",
            "региональные": "🏘️ Региональные каналы", 
            "новости": "📰 Новостные каналы",
            "спортивные": "⚽ Спортивные каналы",
            "музыкальные": "🎵 Музыкальные каналы",
            "детские": "👶 Детские каналы",
            "познавательные": "🧠 Познавательные каналы",
            "развлекательные": "🎉 Развлекательные каналы",
            "кино_и_сериалы": "🎬 Кино и сериалы",
            "религиозные": "⛪ Религиозные каналы",
            "инфо": "ℹ️ Информационные каналы",
            "радио": "📻 Радио",
            "18+": "🔞 18+ контент",
            "fashion": "👗 Мода и стиль",
            "relax": "🧘 Релакс и медитация",
            
            # Специальные категории
            "кинозалы": "🎭 Кинозалы",
            "специальные": "⭐ Специальные каналы"
        }
        
        # Правила маппинга старых категорий в новые
        self.category_mapping = {
            # Объединяем похожие категории
            "эфирные": "федеральные",
            "федеральные_плюс": "федеральные", 
            "региoнальные": "региональные",
            "наш_спорт": "спортивные",
            "кинозалы_2": "кинозалы",
            "кинозалы_3": "кинозалы", 
            "кинозалы_rutube": "кинозалы",
            "кинозалы_сити_эдем": "кинозалы",
            "разное": "специальные"
        }
        
        # Ключевые слова для определения категорий
        self.category_keywords = {
            "федеральные": ["первый", "россия", "нтв", "твц", "ртр", "орт", "канал", "федеральный", "общероссийский"],
            "региональные": ["регион", "область", "край", "город", "москва", "спб", "питер", "уфа", "екатеринбург"],
            "новости": ["новости", "news", "информация", "события", "сводка", "вести", "интерфакс"],
            "спортивные": ["спорт", "sport", "футбол", "хоккей", "баскетбол", "теннис", "бокс", "eurosport", "match"],
            "музыкальные": ["музыка", "music", "муз", "песня", "концерт", "клуб", "диско", "рок", "поп"],
            "детские": ["детский", "дет", "мульт", "cartoon", "дисней", "nickelodeon", "карусель", "малыш"],
            "познавательные": ["познавательный", "наука", "история", "природа", "документальный", "national geographic"],
            "развлекательные": ["развлекательный", "развлечение", "юмор", "комедия", "шоу", "ток", "реалити"],
            "кино_и_сериалы": ["кино", "фильм", "сериал", "movie", "cinema", "hbo", "netflix", "amazon"],
            "религиозные": ["религия", "православие", "церковь", "бог", "вера", "духовный", "религиозный"],
            "инфо": ["инфо", "информация", "справка", "помощь", "поддержка", "info"],
            "радио": ["радио", "radio", "fm", "am", "волна", "станция"],
            "18+": ["18+", "adult", "xxx", "porn", "секс", "эротика", "взрослый", "brazzers", "redtraffic"],
            "fashion": ["мода", "стиль", "fashion", "красота", "стилист", "дизайн"],
            "relax": ["релакс", "медитация", "йога", "спокойствие", "zen", "relax"],
            "кинозалы": ["кинозал", "кинотеатр", "зал", "рутуб", "сити", "эдем"],
            "специальные": ["специальный", "особый", "уникальный", "эксклюзив", "премиум"]
        }
        
        # Исключения (не переносить в другие категории)
        self.exclude_keywords = {
            "18+": ["новости", "детский", "религия", "спорт"],
            "детские": ["18+", "adult", "xxx", "porn", "секс", "эротика"],
            "религиозные": ["18+", "adult", "xxx", "porn", "секс", "эротика"]
        }

    def analyze_channel(self, channel_name, current_category):
        """Анализирует канал и определяет правильную категорию"""
        name_lower = channel_name.lower()
        
        # Сначала проверяем исключения
        for target_cat, exclude_words in self.exclude_keywords.items():
            if any(word in name_lower for word in exclude_words):
                if current_category != target_cat:
                    return target_cat
        
        # Ищем наиболее подходящую категорию по ключевым словам
        best_match = None
        max_score = 0
        
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in name_lower)
            if score > max_score:
                max_score = score
                best_match = category
        
        # Если нашли хорошее совпадение, используем его
        if max_score >= 2:
            return best_match
        
        # Если совпадение слабое, оставляем в текущей категории
        return current_category

    def consolidate_categories(self):
        """Консолидирует все категории, устраняя дубли"""
        logger.info("🔄 НАЧИНАЕМ КОНСОЛИДАЦИЮ КАТЕГОРИЙ")
        logger.info("=" * 50)
        
        # Собираем все каналы
        all_channels = defaultdict(list)
        
        for category_file in self.categories_dir.glob("*.m3u"):
            if category_file.name == "18+.m3u":
                continue  # Пропускаем старую категорию 18+
                
            category_name = category_file.stem
            logger.info(f"📂 Обрабатываем: {category_name}")
            
            # Читаем каналы из файла
            channels = self.read_channels_from_file(category_file)
            
            for channel in channels:
                # Определяем правильную категорию для канала
                correct_category = self.analyze_channel(channel['name'], category_name)
                
                # Применяем маппинг категорий
                if correct_category in self.category_mapping:
                    correct_category = self.category_mapping[correct_category]
                
                all_channels[correct_category].append(channel)
                logger.debug(f"  📺 {channel['name']} → {correct_category}")
        
        # Создаем новые консолидированные файлы
        self.create_consolidated_files(all_channels)
        
        # Удаляем старые дублирующиеся файлы
        self.cleanup_old_files()
        
        logger.info("✅ КОНСОЛИДАЦИЯ ЗАВЕРШЕНА")

    def read_channels_from_file(self, file_path):
        """Читает каналы из M3U файла"""
        channels = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Парсим M3U формат
            lines = content.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('#EXTINF:'):
                    # Извлекаем информацию о канале
                    extinf = line
                    if i + 1 < len(lines):
                        url = lines[i + 1].strip()
                        if url and not url.startswith('#'):
                            # Парсим название канала
                            name_match = re.search(r',(.+)$', extinf)
                            if name_match:
                                name = name_match.group(1).strip()
                                channels.append({
                                    'name': name,
                                    'url': url,
                                    'extinf': extinf
                                })
                i += 1
        except Exception as e:
            logger.error(f"Ошибка чтения файла {file_path}: {e}")
        
        return channels

    def create_consolidated_files(self, all_channels):
        """Создает консолидированные файлы категорий"""
        logger.info("📝 СОЗДАЕМ КОНСОЛИДИРОВАННЫЕ ФАЙЛЫ")
        
        for category, channels in all_channels.items():
            if not channels:
                continue
                
            file_path = self.categories_dir / f"{category}.m3u"
            
            # Удаляем дубликаты по URL
            unique_channels = {}
            for channel in channels:
                if channel['url'] not in unique_channels:
                    unique_channels[channel['url']] = channel
            
            channels = list(unique_channels.values())
            
            logger.info(f"  📂 {category}: {len(channels)} каналов")
            
            # Создаем файл
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                f.write(f"# {self.final_categories.get(category, category)}\n")
                f.write(f"# Каналов: {len(channels)}\n")
                f.write(f"# Обновлено: {self.get_current_time()}\n")
                f.write("\n")
                
                for channel in channels:
                    f.write(f"{channel['extinf']}\n")
                    f.write(f"{channel['url']}\n")
                    f.write("\n")

    def cleanup_old_files(self):
        """Удаляет старые дублирующиеся файлы"""
        logger.info("🧹 ОЧИСТКА СТАРЫХ ФАЙЛОВ")
        
        files_to_remove = [
            "эфирные.m3u",
            "федеральные_плюс.m3u", 
            "региoнальные.m3u",
            "наш_спорт.m3u",
            "кинозалы_2.m3u",
            "кинозалы_3.m3u",
            "кинозалы_rutube.m3u",
            "кинозалы_сити_эдем.m3u",
            "разное.m3u"
        ]
        
        for filename in files_to_remove:
            file_path = self.categories_dir / filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"  🗑️ Удален: {filename}")

    def get_current_time(self):
        """Возвращает текущее время в нужном формате"""
        from datetime import datetime
        return datetime.now().strftime("%d.%m.%Y %H:%M")

def main():
    consolidator = SmartCategoryConsolidator()
    consolidator.consolidate_categories()

if __name__ == "__main__":
    main()
