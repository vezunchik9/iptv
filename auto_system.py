#!/usr/bin/env python3
"""
🎯 ЕДИНАЯ СИСТЕМА УПРАВЛЕНИЯ IPTV ПЛЕЙЛИСТАМИ
==============================================

Простая система, которая всегда работает правильно:
1. Берет доноров из donors_config.json
2. Парсит и обновляет каналы
3. Проверяет и удаляет нерабочие
4. Собирает финальные плейлисты
5. Пушит в Git

Использование:
    python3 auto_system.py          # Полный цикл
    python3 auto_system.py --check  # Только проверка потоков
    python3 auto_system.py --parse  # Только парсинг доноров
"""

import os
import sys
import json
import logging
import argparse
import subprocess
import fcntl
from datetime import datetime
from pathlib import Path

class IPTVAutoSystem:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.lock_file = self.base_dir / '.update.lock'
        self.lock_fd = None
        self.acquire_lock()
        self.setup_logging()
        
    def acquire_lock(self):
        """Создает lock файл для предотвращения параллельных запусков"""
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_fd.write(f"{os.getpid()}\n{datetime.now().isoformat()}")
            self.lock_fd.flush()
        except IOError:
            print("❌ ОШИБКА: Обновление уже запущено!")
            print(f"   Lock файл: {self.lock_file}")
            if self.lock_file.exists():
                with open(self.lock_file, 'r') as f:
                    content = f.read().strip().split('\n')
                    if content:
                        print(f"   PID процесса: {content[0]}")
                        if len(content) > 1:
                            print(f"   Запущен: {content[1]}")
            sys.exit(1)
    
    def release_lock(self):
        """Освобождает lock файл"""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                self.lock_fd.close()
                self.lock_file.unlink(missing_ok=True)
            except Exception as e:
                self.logger.warning(f"Ошибка при освобождении lock: {e}")
    
    def setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.base_dir / 'auto_system.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def run_script(self, script_name, *args):
        """Запуск скрипта с обработкой ошибок"""
        try:
            cmd = [sys.executable, f"scripts/{script_name}"] + list(args)
            result = subprocess.run(cmd, cwd=self.base_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Ошибка в {script_name}: {result.stderr}")
                return False
            
            self.logger.info(f"✅ {script_name} выполнен успешно")
            return True
            
        except Exception as e:
            self.logger.error(f"Критическая ошибка в {script_name}: {e}")
            return False
    
    def parse_donors(self):
        """Парсинг доноров и обновление каналов"""
        self.logger.info("🔄 Парсинг доноров...")
        return self.run_script("playlist_parser.py")
    
    def check_streams(self):
        """Качественная проверка потоков с удалением нерабочих"""
        self.logger.info("🔍 Качественная проверка потоков...")
        
        # Проверяем все категории через real_video_checker (качественная проверка)
        categories_dir = self.base_dir / "categories"
        for category_file in categories_dir.glob("*.m3u"):
            if category_file.name.startswith('.'):
                continue
                
            self.logger.info(f"Проверяем {category_file.name}...")
            if not self.run_script("real_video_checker.py", str(category_file)):
                self.logger.warning(f"Проблемы с проверкой {category_file.name}")
        
        return True
    
    def deduplicate_channels(self):
        """Быстрая дедупликация каналов по источникам"""
        self.logger.info("⚡ Быстрая дедупликация каналов...")
        
        if not self.run_script("fast_deduplicator.py"):
            self.logger.error("Ошибка дедупликации")
            return False
        
        return True
    
    def build_playlists(self):
        """Сборка финальных плейлистов"""
        self.logger.info("📺 Сборка плейлистов...")
        
        # Обновляем эмодзи в категориях
        if not self.run_script("fix_category_emojis.py"):
            self.logger.warning("Проблемы с эмодзи")
        
        # Создаем основные плейлисты
        if not self.run_script("create_full_televizo_playlist.py"):
            self.logger.error("Ошибка создания плейлистов")
            return False
        
        return True
    
    def git_push(self):
        """Пуш изменений в Git"""
        self.logger.info("📤 Пуш в Git...")
        
        try:
            # Добавляем все изменения
            subprocess.run(["git", "add", "."], cwd=self.base_dir, check=True)
            
            # Коммит с временной меткой
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_msg = f"🤖 Автообновление плейлистов {timestamp}"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=self.base_dir, check=True)
            
            # Пуш
            subprocess.run(["git", "push"], cwd=self.base_dir, check=True)
            
            self.logger.info("✅ Изменения запушены в Git")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ошибка Git: {e}")
            return False
    
    def cleanup_old_files(self):
        """Очистка старых файлов"""
        self.logger.info("🧹 Очистка старых файлов...")
        
        try:
            # Удаляем старые бэкапы (оставляем только последние 3)
            for backup_dir in ["backups", "reports"]:
                backup_path = self.base_dir / backup_dir
                if backup_path.exists():
                    files = sorted(backup_path.glob("*"), key=os.path.getmtime, reverse=True)
                    for old_file in files[3:]:  # Оставляем только 3 последних
                        try:
                            if old_file.is_file():
                                old_file.unlink()
                                self.logger.info(f"Удален старый файл: {old_file.name}")
                        except Exception as e:
                            self.logger.warning(f"Не удалось удалить {old_file}: {e}")
            return True
        except Exception as e:
            self.logger.warning(f"Ошибка очистки файлов: {e}")
            return True  # Не критическая ошибка, продолжаем
    
    def full_cycle(self):
        """Полный цикл обновления"""
        try:
            self.logger.info("🚀 ЗАПУСК ПОЛНОГО ЦИКЛА ОБНОВЛЕНИЯ")
            self.logger.info("=" * 50)
            
            steps = [
                ("Парсинг доноров", self.parse_donors),
                ("Умная дедупликация", self.deduplicate_channels),
                ("Проверка потоков", self.check_streams),
                ("Сборка плейлистов", self.build_playlists),
                ("Очистка файлов", self.cleanup_old_files),
                ("Git push", self.git_push)
            ]
            
            for step_name, step_func in steps:
                self.logger.info(f"▶️ {step_name}...")
                if not step_func():
                    self.logger.error(f"❌ Ошибка на этапе: {step_name}")
                    return False
            
            self.logger.info("🎉 ПОЛНЫЙ ЦИКЛ ЗАВЕРШЕН УСПЕШНО!")
            return True
        finally:
            # Всегда освобождаем lock, даже при ошибке
            self.release_lock()
    
    def status(self):
        """Показать статус системы"""
        print("📊 СТАТУС СИСТЕМЫ IPTV")
        print("=" * 30)
        
        # Количество категорий
        categories = list((self.base_dir / "categories").glob("*.m3u"))
        print(f"📁 Категорий: {len(categories)}")
        
        # Количество каналов в основном плейлисте
        main_playlist = self.base_dir / "playlists" / "televizo_main.m3u"
        if main_playlist.exists():
            with open(main_playlist, 'r', encoding='utf-8') as f:
                channels = len([line for line in f if line.startswith('#EXTINF')])
            print(f"📺 Каналов в основном плейлисте: {channels}")
        
        # Последнее обновление
        if main_playlist.exists():
            mtime = datetime.fromtimestamp(main_playlist.stat().st_mtime)
            print(f"🕒 Последнее обновление: {mtime.strftime('%Y-%m-%d %H:%M')}")
        
        # Доноры
        donors_config = self.base_dir / "donors_config.json"
        if donors_config.exists():
            with open(donors_config, 'r', encoding='utf-8') as f:
                config = json.load(f)
                active_donors = sum(1 for d in config.get('donors', {}).values() if d.get('enabled', False))
            print(f"🌐 Активных доноров: {active_donors}")

def main():
    parser = argparse.ArgumentParser(description='IPTV Auto System')
    parser.add_argument('--parse', action='store_true', help='Только парсинг доноров')
    parser.add_argument('--dedup', action='store_true', help='Только дедупликация каналов')
    parser.add_argument('--check', action='store_true', help='Только проверка потоков')
    parser.add_argument('--build', action='store_true', help='Только сборка плейлистов')
    parser.add_argument('--status', action='store_true', help='Показать статус')
    
    args = parser.parse_args()
    system = IPTVAutoSystem()
    
    if args.status:
        system.status()
    elif args.parse:
        system.parse_donors()
    elif args.dedup:
        system.deduplicate_channels()
    elif args.check:
        system.check_streams()
    elif args.build:
        system.build_playlists()
    else:
        system.full_cycle()

if __name__ == "__main__":
    main()
