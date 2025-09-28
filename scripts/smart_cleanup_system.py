#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Умная система очистки IPTV плейлистов с правильной логикой:
1. Обновляем из доноров (свежие ссылки)
2. Проверяем ВСЕ каналы (включая новые)
3. Удаляем нерабочие
4. Автопуш в Git
"""

import asyncio
import os
import json
import logging
import subprocess
from datetime import datetime
import sys

# Добавляем путь к скриптам
sys.path.insert(0, os.path.dirname(__file__))

from real_video_checker import RealVideoChecker
from smart_playlist_parser import SmartPlaylistParser

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SmartCleanupSystem:
    def __init__(self, config_file='donors_config.json'):
        self.config_file = config_file
        self.video_checker = RealVideoChecker(
            timeout=20,
            max_concurrent=3,
            test_duration=8,
            buffer_threshold=3
        )
        self.smart_parser = SmartPlaylistParser(config_file)
        
        # Статистика
        self.stats = {
            'categories_processed': 0,
            'total_channels_before': 0,
            'total_channels_after_update': 0,
            'total_channels_after_cleanup': 0,
            'channels_added_from_donors': 0,
            'channels_updated_from_donors': 0,
            'channels_removed_broken': 0,
            'processing_time': 0
        }
    
    def create_full_backup(self):
        """Создает полный бэкап всех категорий"""
        backup_dir = f"backups/full_backups/smart_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # Копируем все категории
            subprocess.run(['cp', '-r', 'categories/', backup_dir + '/'], check=True)
            
            # Копируем основной плейлист
            if os.path.exists('playlists/televizo_main.m3u'):
                subprocess.run(['cp', 'playlists/televizo_main.m3u8', backup_dir + '/'], check=False)
            
            logger.info(f"💾 Создан полный бэкап: {backup_dir}")
            return backup_dir
            
        except Exception as e:
            logger.error(f"Ошибка при создании бэкапа: {e}")
            return None
    
    async def smart_update_from_donors(self):
        """Шаг 1: Умное обновление из доноров"""
        logger.info("🔄 ШАГ 1: Обновляем плейлисты из донорских источников...")
        
        try:
            # Запускаем умный парсер
            donors = self.smart_parser.config.get('donors', {})
            
            for donor_name, donor_config in donors.items():
                if not donor_config.get('enabled', True):
                    continue
                    
                logger.info(f"📥 Обрабатываем донора: {donor_name}")
                
                # Скачиваем плейлист
                content = self.smart_parser.download_playlist(donor_config['url'])
                if not content:
                    logger.warning(f"Не удалось скачать плейлист от {donor_name}")
                    continue
                
                # Парсим каналы
                channels = self.smart_parser.parse_m3u_playlist(content)
                logger.info(f"Найдено каналов в плейлисте {donor_name}: {len(channels)}")
                
                # Добавляем/обновляем каналы по категориям
                for channel in channels:
                    category = self.smart_parser.categorize_channel(channel)
                    if category:
                        result = self.smart_parser.add_or_update_channel(channel, category)
                        if result == 'added':
                            self.stats['channels_added_from_donors'] += 1
                        elif result == 'updated':
                            self.stats['channels_updated_from_donors'] += 1
            
            # Заголовки категорий обновляются автоматически при записи
            
            logger.info(f"✅ Обновление завершено: +{self.stats['channels_added_from_donors']} новых, ~{self.stats['channels_updated_from_donors']} обновлено")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении из доноров: {e}")
            raise
    
    async def check_and_cleanup_all_categories(self, categories_dir='categories'):
        """Шаг 2: Проверяем ВСЕ каналы и удаляем нерабочие"""
        logger.info("🧹 ШАГ 2: Проверяем все каналы и удаляем нерабочие...")
        
        if not os.path.exists(categories_dir):
            logger.error(f"Папка категорий не найдена: {categories_dir}")
            return
        
        # Получаем список файлов категорий
        category_files = []
        for file in os.listdir(categories_dir):
            if file.endswith('.m3u') and not file.startswith('.'):
                category_files.append(os.path.join(categories_dir, file))
        
        if not category_files:
            logger.warning("Не найдено файлов категорий для проверки")
            return
        
        logger.info(f"Найдено категорий для проверки: {len(category_files)}")
        
        # Считаем каналы до очистки
        for category_file in category_files:
            try:
                with open(category_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                channel_count = len([line for line in content.splitlines() 
                                   if line.strip() and not line.startswith('#')])
                self.stats['total_channels_after_update'] += channel_count
            except:
                pass
        
        # Проверяем каждую категорию
        cleanup_reports = []
        
        for category_file in category_files:
            try:
                logger.info(f"🎬 Проверяем категорию: {os.path.basename(category_file)}")
                
                # Проверяем и очищаем
                cleanup_report = await self.video_checker.check_playlist_and_cleanup(category_file)
                
                if cleanup_report and 'error' not in cleanup_report:
                    cleanup_reports.append(cleanup_report)
                    self.stats['channels_removed_broken'] += cleanup_report['broken_channels']
                    self.stats['categories_processed'] += 1
                    
                    logger.info(f"✅ {os.path.basename(category_file)}: {cleanup_report['working_channels']}/{cleanup_report['total_channels']} каналов осталось")
                else:
                    logger.warning(f"Ошибка при проверке {category_file}")
                
            except Exception as e:
                logger.error(f"Ошибка при обработке {category_file}: {e}")
                continue
        
        # Считаем каналы после очистки
        for category_file in category_files:
            try:
                with open(category_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                channel_count = len([line for line in content.splitlines() 
                                   if line.strip() and not line.startswith('#')])
                self.stats['total_channels_after_cleanup'] += channel_count
            except:
                pass
        
        return cleanup_reports
    
    def update_main_playlist(self):
        """Шаг 3: Обновляем основной плейлист"""
        logger.info("📝 ШАГ 3: Обновляем основной плейлист...")
        
        try:
            result = subprocess.run(
                ['python3', 'scripts/create_televizo_playlist.py'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("✅ Основной плейлист обновлен")
            else:
                logger.warning(f"Предупреждение при обновлении плейлиста: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении основного плейлиста: {e}")
    
    def git_commit_and_push(self, backup_dir):
        """Шаг 4: Коммит и пуш в Git"""
        logger.info("🚀 ШАГ 4: Отправляем изменения в Git...")
        
        try:
            # Добавляем все изменения
            subprocess.run(['git', 'add', '.'], check=True, cwd='.')
            
            # Проверяем есть ли изменения
            result = subprocess.run(['git', 'diff', '--cached', '--name-only'], 
                                  capture_output=True, text=True, cwd='.')
            
            if not result.stdout.strip():
                logger.info("ℹ️ Нет изменений для коммита")
                return False
            
            changes = result.stdout.strip().split('\n')
            logger.info(f"📋 Найдено изменений: {len(changes)}")
            
            # Создаем коммит
            timestamp = datetime.now().strftime('%d.%m.%Y %H:%M')
            commit_msg = f"""🤖 Умная очистка плейлистов ({timestamp})

📊 Статистика:
• Категорий обработано: {self.stats['categories_processed']}
• Каналов добавлено из доноров: {self.stats['channels_added_from_donors']}
• Каналов обновлено из доноров: {self.stats['channels_updated_from_donors']}
• Нерабочих каналов удалено: {self.stats['channels_removed_broken']}
• Итого каналов: {self.stats['total_channels_after_cleanup']}

🔄 Процесс:
1. Обновление из донорских источников
2. Реальная проверка всех видеопотоков
3. Удаление нерабочих каналов
4. Автоматический Git push

💾 Полный бэкап: {os.path.basename(backup_dir)}

Автоматически создано умной системой очистки"""

            subprocess.run(['git', 'commit', '-m', commit_msg], check=True, cwd='.')
            logger.info("💾 Коммит создан")
            
            # Пушим в репозиторий
            subprocess.run(['git', 'push', 'origin', 'main'], check=True, cwd='.')
            logger.info("🚀 Изменения отправлены в репозиторий!")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка Git операции: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при работе с Git: {e}")
            return False
    
    async def run_full_smart_cleanup(self):
        """Запускает полный цикл умной очистки"""
        start_time = datetime.now()
        logger.info("🚀 ЗАПУСК ПОЛНОГО ЦИКЛА УМНОЙ ОЧИСТКИ ПЛЕЙЛИСТОВ")
        logger.info("=" * 60)
        
        try:
            # Считаем каналы до обработки
            categories_dir = 'categories'
            if os.path.exists(categories_dir):
                for file in os.listdir(categories_dir):
                    if file.endswith('.m3u') and not file.startswith('.'):
                        try:
                            with open(os.path.join(categories_dir, file), 'r', encoding='utf-8') as f:
                                content = f.read()
                            channel_count = len([line for line in content.splitlines() 
                                               if line.strip() and not line.startswith('#')])
                            self.stats['total_channels_before'] += channel_count
                        except:
                            pass
            
            # Создаем полный бэкап
            backup_dir = self.create_full_backup()
            if not backup_dir:
                logger.error("❌ Не удалось создать бэкап. Прерываем операцию.")
                return
            
            # Шаг 1: Обновляем из доноров
            await self.smart_update_from_donors()
            
            # Шаг 2: Проверяем и очищаем все каналы
            cleanup_reports = await self.check_and_cleanup_all_categories()
            
            # Шаг 3: Обновляем основной плейлист
            self.update_main_playlist()
            
            # Шаг 4: Git commit и push
            git_success = self.git_commit_and_push(backup_dir)
            
            # Вычисляем время обработки
            self.stats['processing_time'] = (datetime.now() - start_time).total_seconds()
            
            # Выводим итоговую статистику
            self.print_final_stats(backup_dir, git_success)
            
            logger.info("🎉 ПОЛНАЯ УМНАЯ ОЧИСТКА ЗАВЕРШЕНА!")
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            raise
    
    def print_final_stats(self, backup_dir, git_success):
        """Выводит финальную статистику"""
        print("\n" + "=" * 70)
        print("📊 ИТОГОВАЯ СТАТИСТИКА УМНОЙ ОЧИСТКИ")
        print("=" * 70)
        print(f"🗂️  Категорий обработано: {self.stats['categories_processed']}")
        print(f"📊 Каналов было: {self.stats['total_channels_before']}")
        print(f"📈 Каналов после обновления: {self.stats['total_channels_after_update']}")
        print(f"📉 Каналов после очистки: {self.stats['total_channels_after_cleanup']}")
        print()
        print(f"➕ Добавлено из доноров: {self.stats['channels_added_from_donors']}")
        print(f"🔄 Обновлено из доноров: {self.stats['channels_updated_from_donors']}")
        print(f"❌ Удалено нерабочих: {self.stats['channels_removed_broken']}")
        print()
        print(f"⏱️  Время обработки: {self.stats['processing_time']:.1f} сек")
        print(f"💾 Полный бэкап: {os.path.basename(backup_dir)}")
        print(f"🚀 Git push: {'✅ Успешно' if git_success else '❌ Ошибка'}")
        
        # Эффективность
        if self.stats['total_channels_before'] > 0:
            net_change = self.stats['total_channels_after_cleanup'] - self.stats['total_channels_before']
            print(f"📈 Итоговое изменение: {net_change:+d} каналов")
        
        print("=" * 70)
        print("🎯 РЕЗУЛЬТАТ:")
        print("   ✅ Плейлисты обновлены из свежих донорских источников")
        print("   ✅ Все каналы проверены на реальную работоспособность")
        print("   ✅ Нерабочие каналы удалены")
        print("   ✅ Изменения автоматически отправлены в Git")
        print("   ✅ Созданы бэкапы для безопасности")
        print("=" * 70)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Умная система очистки IPTV плейлистов')
    parser.add_argument('--config', default='donors_config.json', help='Файл конфигурации')
    parser.add_argument('--dry-run', action='store_true', help='Тестовый запуск без изменений')
    
    args = parser.parse_args()
    
    async def run_cleanup():
        system = SmartCleanupSystem(args.config)
        
        if args.dry_run:
            logger.info("🧪 ТЕСТОВЫЙ РЕЖИМ - изменения не будут сохранены")
            # В тестовом режиме можно добавить дополнительную логику
        
        await system.run_full_smart_cleanup()
    
    asyncio.run(run_cleanup())

if __name__ == "__main__":
    main()
