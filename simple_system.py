#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простая система IPTV - только парсинг и создание плейлистов
Без проверки потоков, без лишних файлов
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimpleIPTVSystem:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.playlists_dir = self.base_dir / "playlists"
        self.playlists_dir.mkdir(exist_ok=True)
        
    def run_script(self, script_name, *args):
        """Запускает Python скрипт"""
        script_path = self.base_dir / "scripts" / script_name
        if not script_path.exists():
            logger.error(f"Скрипт не найден: {script_path}")
            return False
            
        cmd = [sys.executable, str(script_path)] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info(f"✅ {script_name} выполнен успешно")
                return True
            else:
                logger.error(f"❌ Ошибка в {script_name}: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Таймаут в {script_name}")
            return False
        except Exception as e:
            logger.error(f"❌ Исключение в {script_name}: {e}")
            return False
    
    def parse_donors(self):
        """Парсинг доноров"""
        logger.info("🔄 Парсинг доноров...")
        return self.run_script("playlist_parser.py")
    
    def deduplicate_channels(self):
        """Быстрая дедупликация"""
        logger.info("⚡ Дедупликация каналов...")
        return self.run_script("fast_deduplicator.py")
    
    def create_playlists(self):
        """Создание плейлистов"""
        logger.info("📺 Создание плейлистов...")
        
        # Создаем основной плейлист (с 18+)
        if not self.run_script("create_full_televizo_playlist.py"):
            return False
            
        # Создаем безопасный плейлист (без 18+)
        logger.info("📺 Создание безопасного плейлиста...")
        return self.create_safe_playlist()
    
    def create_safe_playlist(self):
        """Создает безопасный плейлист без 18+ контента"""
        try:
            main_playlist = self.playlists_dir / "televizo_main.m3u"
            safe_playlist = self.playlists_dir / "televizo_safe.m3u"
            
            if not main_playlist.exists():
                logger.error("Основной плейлист не найден!")
                return False
            
            # Читаем основной плейлист и фильтруем 18+
            with open(main_playlist, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            safe_lines = []
            skip_next = False
            
            for line in lines:
                if skip_next:
                    skip_next = False
                    continue
                    
                if line.startswith('#EXTINF:'):
                    if '18+' in line or '🔞' in line:
                        skip_next = True
                        continue
                
                safe_lines.append(line)
            
            # Сохраняем безопасный плейлист
            with open(safe_playlist, 'w', encoding='utf-8') as f:
                f.writelines(safe_lines)
            
            logger.info(f"✅ Безопасный плейлист создан: {safe_playlist}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания безопасного плейлиста: {e}")
            return False
    
    def git_push(self):
        """Пуш в Git"""
        logger.info("📤 Пуш в Git...")
        
        try:
            # Добавляем все изменения
            subprocess.run(['git', 'add', '.'], check=True, cwd=self.base_dir)
            
            # Коммит
            commit_msg = f"🤖 Простое обновление плейлистов {datetime.now().strftime('%Y-%m-%d %H:%M')}"
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
        """Показывает статистику плейлистов"""
        logger.info("\n📊 СТАТИСТИКА ПЛЕЙЛИСТОВ")
        logger.info("=" * 50)
        
        main_playlist = self.playlists_dir / "televizo_main.m3u"
        safe_playlist = self.playlists_dir / "televizo_safe.m3u"
        
        if main_playlist.exists():
            with open(main_playlist, 'r', encoding='utf-8') as f:
                main_channels = len([line for line in f if line.startswith('http')])
            logger.info(f"📺 televizo_main.m3u: {main_channels} каналов")
        
        if safe_playlist.exists():
            with open(safe_playlist, 'r', encoding='utf-8') as f:
                safe_channels = len([line for line in f if line.startswith('http')])
            logger.info(f"📺 televizo_safe.m3u: {safe_channels} каналов")
        
        # Размеры файлов
        if main_playlist.exists():
            size = main_playlist.stat().st_size / 1024
            logger.info(f"📁 Размер main: {size:.1f} KB")
        
        if safe_playlist.exists():
            size = safe_playlist.stat().st_size / 1024
            logger.info(f"📁 Размер safe: {size:.1f} KB")
    
    def run(self):
        """Запуск простой системы"""
        logger.info("🚀 ПРОСТАЯ СИСТЕМА IPTV")
        logger.info("=" * 50)
        logger.info("📺 Только парсинг и создание плейлистов")
        logger.info("⚡ Без проверки потоков")
        logger.info("")
        
        steps = [
            ("Парсинг доноров", self.parse_donors),
            ("Дедупликация", self.deduplicate_channels),
            ("Создание плейлистов", self.create_playlists),
            ("Git push", self.git_push)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"▶️ {step_name}...")
            if not step_func():
                logger.error(f"❌ Ошибка на этапе: {step_name}")
                return False
        
        self.show_statistics()
        logger.info("🎉 ПРОСТАЯ СИСТЕМА ЗАВЕРШЕНА УСПЕШНО!")
        return True

if __name__ == "__main__":
    system = SimpleIPTVSystem()
    success = system.run()
    sys.exit(0 if success else 1)
