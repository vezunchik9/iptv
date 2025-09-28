#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Система очистки и восстановления IPTV плейлистов
Удаляет нерабочие каналы и восстанавливает их из донорских источников
"""

import asyncio
import os
import json
import logging
from datetime import datetime
import sys

# Добавляем путь к скриптам
sys.path.insert(0, os.path.dirname(__file__))

from real_video_checker import RealVideoChecker
from smart_playlist_parser import SmartPlaylistParser

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CleanupAndRestoreSystem:
    def __init__(self, config_file='donors_config.json'):
        self.config_file = config_file
        self.video_checker = RealVideoChecker(
            timeout=30,
            max_concurrent=3,
            test_duration=8,
            buffer_threshold=3
        )
        self.smart_parser = SmartPlaylistParser(config_file)
        
        # Статистика
        self.stats = {
            'total_checked': 0,
            'total_removed': 0,
            'total_restored': 0,
            'categories_processed': 0,
            'processing_time': 0
        }
    
    async def cleanup_single_category(self, category_file):
        """Очищает одну категорию от нерабочих каналов"""
        logger.info(f"🧹 Очищаем категорию: {category_file}")
        
        if not os.path.exists(category_file):
            logger.warning(f"Файл не найден: {category_file}")
            return None
        
        # Проверяем и очищаем
        report = await self.video_checker.check_playlist_and_cleanup(category_file)
        
        if 'error' in report:
            logger.error(f"Ошибка при очистке {category_file}: {report['error']}")
            return None
        
        logger.info(f"✅ Категория очищена: {report['working_channels']}/{report['total_channels']} каналов осталось")
        
        # Обновляем статистику
        self.stats['total_checked'] += report['total_channels']
        self.stats['total_removed'] += report['broken_channels']
        self.stats['categories_processed'] += 1
        
        return report
    
    async def restore_from_donors(self, category_name):
        """Восстанавливает каналы из донорских источников"""
        logger.info(f"🔄 Восстанавливаем каналы для категории: {category_name}")
        
        # Запускаем умный парсер для конкретной категории
        try:
            # Временно модифицируем конфигурацию для обработки только одной категории
            original_mapping = self.smart_parser.config.get('category_mapping', {})
            
            if category_name in original_mapping:
                # Создаем временную конфигурацию только для этой категории
                temp_mapping = {category_name: original_mapping[category_name]}
                self.smart_parser.config['category_mapping'] = temp_mapping
                
                # Запускаем парсинг
                donors = self.smart_parser.config.get('donors', {})
                restored_count = 0
                
                for donor_name, donor_config in donors.items():
                    if donor_config.get('enabled', True):
                        logger.info(f"Проверяем донора {donor_name} для восстановления...")
                        
                        # Скачиваем плейлист донора
                        content = self.smart_parser.download_playlist(donor_config['url'])
                        if content:
                            # Парсим каналы
                            channels = self.smart_parser.parse_m3u_playlist(content)
                            
                            # Добавляем подходящие каналы
                            for channel in channels:
                                category = self.smart_parser.categorize_channel(channel)
                                if category == category_name:
                                    added = self.smart_parser.add_or_update_channel(channel, category)
                                    if added:
                                        restored_count += 1
                
                # Восстанавливаем оригинальную конфигурацию
                self.smart_parser.config['category_mapping'] = original_mapping
                
                logger.info(f"✅ Восстановлено каналов: {restored_count}")
                self.stats['total_restored'] += restored_count
                
                return restored_count
            else:
                logger.warning(f"Категория {category_name} не найдена в конфигурации")
                return 0
                
        except Exception as e:
            logger.error(f"Ошибка при восстановлении категории {category_name}: {e}")
            return 0
    
    async def process_all_categories(self, categories_dir='categories'):
        """Обрабатывает все категории: очистка + восстановление"""
        start_time = datetime.now()
        logger.info("🚀 Запускаем полную очистку и восстановление всех категорий")
        
        if not os.path.exists(categories_dir):
            logger.error(f"Папка категорий не найдена: {categories_dir}")
            return
        
        # Получаем список файлов категорий
        category_files = []
        for file in os.listdir(categories_dir):
            if file.endswith('.m3u') and not file.startswith('.'):
                category_files.append(os.path.join(categories_dir, file))
        
        if not category_files:
            logger.warning("Не найдено файлов категорий для обработки")
            return
        
        logger.info(f"Найдено категорий для обработки: {len(category_files)}")
        
        # Обрабатываем каждую категорию
        cleanup_reports = []
        
        for category_file in category_files:
            try:
                # Очищаем категорию
                cleanup_report = await self.cleanup_single_category(category_file)
                
                if cleanup_report:
                    cleanup_reports.append(cleanup_report)
                    
                    # Если удалили много каналов, пытаемся восстановить
                    if cleanup_report['broken_channels'] > 0:
                        category_name = os.path.basename(category_file).replace('.m3u', '')
                        await self.restore_from_donors(category_name)
                
            except Exception as e:
                logger.error(f"Ошибка при обработке {category_file}: {e}")
                continue
        
        # Обновляем заголовки категорий
        self.smart_parser.update_category_headers()
        
        # Вычисляем время обработки
        self.stats['processing_time'] = (datetime.now() - start_time).total_seconds()
        
        # Создаем отчет
        await self.create_cleanup_report(cleanup_reports)
        
        logger.info("🎉 Полная очистка и восстановление завершена!")
    
    async def create_cleanup_report(self, cleanup_reports):
        """Создает детальный отчет по очистке"""
        report_file = f"reports/cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Создаем папку для отчетов
        os.makedirs("reports", exist_ok=True)
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'categories_processed': self.stats['categories_processed'],
                'total_channels_checked': self.stats['total_checked'],
                'total_channels_removed': self.stats['total_removed'],
                'total_channels_restored': self.stats['total_restored'],
                'processing_time_seconds': self.stats['processing_time'],
                'cleanup_efficiency': (self.stats['total_removed'] / self.stats['total_checked'] * 100) if self.stats['total_checked'] > 0 else 0,
                'restore_efficiency': (self.stats['total_restored'] / self.stats['total_removed'] * 100) if self.stats['total_removed'] > 0 else 0
            },
            'category_details': []
        }
        
        # Добавляем детали по категориям
        for report in cleanup_reports:
            category_detail = {
                'category': os.path.basename(report['playlist_file']).replace('.m3u', ''),
                'total_channels': report['total_channels'],
                'working_channels': report['working_channels'],
                'removed_channels': report['broken_channels'],
                'cleanup_percentage': report['cleanup_percentage'],
                'backup_file': report['backup_file'],
                'broken_channels_list': report['broken_list'][:5]  # Первые 5 для краткости
            }
            report_data['category_details'].append(category_detail)
        
        # Сохраняем отчет
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📊 Отчет сохранен: {report_file}")
            
            # Выводим краткую статистику в консоль
            self.print_summary_stats(report_data)
            
        except Exception as e:
            logger.error(f"Ошибка при создании отчета: {e}")
    
    def print_summary_stats(self, report_data):
        """Выводит краткую статистику в консоль"""
        summary = report_data['summary']
        
        print("\n" + "="*70)
        print("📊 ИТОГОВАЯ СТАТИСТИКА ОЧИСТКИ И ВОССТАНОВЛЕНИЯ")
        print("="*70)
        print(f"🗂️  Обработано категорий: {summary['categories_processed']}")
        print(f"🔍 Проверено каналов: {summary['total_channels_checked']}")
        print(f"❌ Удалено нерабочих: {summary['total_channels_removed']}")
        print(f"✅ Восстановлено новых: {summary['total_channels_restored']}")
        print(f"⏱️  Время обработки: {summary['processing_time_seconds']:.1f} сек")
        print(f"🧹 Эффективность очистки: {summary['cleanup_efficiency']:.1f}%")
        print(f"🔄 Эффективность восстановления: {summary['restore_efficiency']:.1f}%")
        
        if report_data['category_details']:
            print(f"\n📁 ДЕТАЛИ ПО КАТЕГОРИЯМ:")
            for detail in report_data['category_details']:
                if detail['removed_channels'] > 0:
                    print(f"   {detail['category']}: -{detail['removed_channels']} каналов ({detail['cleanup_percentage']:.1f}%)")
        
        print("="*70)
    
    async def smart_cleanup_mode(self, min_channels_threshold=5):
        """Умный режим очистки - обрабатывает только проблемные категории"""
        logger.info("🧠 Запускаем умный режим очистки")
        
        categories_dir = 'categories'
        if not os.path.exists(categories_dir):
            logger.error(f"Папка категорий не найдена: {categories_dir}")
            return
        
        # Анализируем категории и выбираем кандидатов для очистки
        candidates = []
        
        for file in os.listdir(categories_dir):
            if file.endswith('.m3u') and not file.startswith('.'):
                category_file = os.path.join(categories_dir, file)
                
                try:
                    # Считаем каналы в категории
                    with open(category_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    channel_count = len([line for line in content.splitlines() 
                                       if line.strip() and not line.startswith('#')])
                    
                    # Если каналов достаточно для проверки
                    if channel_count >= min_channels_threshold:
                        candidates.append({
                            'file': category_file,
                            'name': file.replace('.m3u', ''),
                            'channel_count': channel_count
                        })
                
                except Exception as e:
                    logger.debug(f"Ошибка при анализе {category_file}: {e}")
        
        # Сортируем по количеству каналов (сначала большие категории)
        candidates.sort(key=lambda x: x['channel_count'], reverse=True)
        
        logger.info(f"Выбрано категорий для умной очистки: {len(candidates)}")
        
        # Обрабатываем выбранные категории
        for candidate in candidates:
            logger.info(f"🎯 Обрабатываем: {candidate['name']} ({candidate['channel_count']} каналов)")
            
            # Очищаем
            cleanup_report = await self.cleanup_single_category(candidate['file'])
            
            if cleanup_report and cleanup_report['broken_channels'] > 0:
                # Восстанавливаем если есть что восстанавливать
                await self.restore_from_donors(candidate['name'])

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Система очистки и восстановления IPTV плейлистов')
    parser.add_argument('--mode', choices=['full', 'smart', 'category'], default='smart',
                       help='Режим работы: full (все категории), smart (только проблемные), category (одна категория)')
    parser.add_argument('--category', help='Имя категории для режима category')
    parser.add_argument('--config', default='donors_config.json', help='Файл конфигурации')
    parser.add_argument('--min-channels', type=int, default=5, help='Минимум каналов для обработки')
    
    args = parser.parse_args()
    
    async def run_cleanup():
        system = CleanupAndRestoreSystem(args.config)
        
        if args.mode == 'full':
            await system.process_all_categories()
        elif args.mode == 'smart':
            await system.smart_cleanup_mode(args.min_channels)
        elif args.mode == 'category':
            if not args.category:
                print("❌ Для режима 'category' укажите --category")
                return
            
            category_file = f"categories/{args.category}.m3u"
            cleanup_report = await system.cleanup_single_category(category_file)
            
            if cleanup_report and cleanup_report['broken_channels'] > 0:
                await system.restore_from_donors(args.category)
    
    asyncio.run(run_cleanup())

if __name__ == "__main__":
    main()
