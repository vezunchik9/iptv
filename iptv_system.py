#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV System - только парсинг и создание плейлиста
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
        logging.FileHandler('iptv_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IPTVSystem:
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
    
    def create_playlist(self):
        """Создание плейлиста"""
        logger.info("📺 Создание плейлиста...")
        
        try:
            # Читаем все категории и создаем один плейлист
            categories_dir = self.base_dir / "categories"
            if not categories_dir.exists():
                logger.error("Папка categories не найдена!")
                return False
            
            all_channels = []
            total_channels = 0
            
            # Читаем все .m3u файлы из categories
            for m3u_file in categories_dir.glob("*.m3u"):
                if m3u_file.name.startswith('.'):
                    continue
                    
                logger.info(f"Читаем {m3u_file.name}...")
                
                try:
                    with open(m3u_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Парсим каналы
                    i = 0
                    while i < len(lines):
                        line = lines[i].strip()
                        if line.startswith('#EXTINF:'):
                            extinf = line
                            # Ищем URL в следующих строках (пропускаем пустые строки)
                            j = i + 1
                            while j < len(lines):
                                url_line = lines[j].strip()
                                if url_line.startswith('http'):
                                    all_channels.append({
                                        'extinf': extinf,
                                        'url': url_line
                                    })
                                    total_channels += 1
                                    i = j + 1
                                    break
                                elif url_line == '':
                                    j += 1
                                elif url_line.startswith('#'):
                                    j += 1
                                else:
                                    i += 1
                                    break
                            else:
                                i += 1
                        else:
                            i += 1
                        
                except Exception as e:
                    logger.warning(f"Ошибка чтения {m3u_file.name}: {e}")
                    continue
            
            # Создаем плейлист
            playlist_file = self.playlists_dir / "televizo.m3u"
            
            with open(playlist_file, 'w', encoding='utf-8') as f:
                f.write('#EXTM3U url-tvg="https://iptvx.one/epg/epg_lite.xml.gz"\n')
                f.write('# 📺 Televizo IPTV Playlist\n')
                f.write(f'# Создан: {datetime.now().strftime("%d.%m.%Y %H:%M")}\n')
                f.write(f'# Всего каналов: {total_channels}\n')
                f.write('# GitHub: https://github.com/vezunchik9/iptv\n')
                f.write('# Telegram: @SHARED_NEW\n\n')
                
                # Добавляем каналы
                for channel in all_channels:
                    f.write(f'{channel["extinf"]}\n')
                    f.write(f'{channel["url"]}\n\n')
            
            logger.info(f"✅ Плейлист создан: {playlist_file}")
            logger.info(f"📊 Каналов: {total_channels}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания плейлиста: {e}")
            return False
    
    def git_push(self):
        """Пуш в Git"""
        logger.info("📤 Пуш в Git...")
        
        try:
            # Добавляем все изменения
            subprocess.run(['git', 'add', '.'], check=True, cwd=self.base_dir)
            
            # Коммит
            commit_msg = f"🤖 Обновление плейлиста {datetime.now().strftime('%Y-%m-%d %H:%M')}"
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
        """Показывает статистику"""
        logger.info("\n📊 СТАТИСТИКА")
        logger.info("=" * 30)
        
        playlist_file = self.playlists_dir / "televizo.m3u"
        
        if playlist_file.exists():
            with open(playlist_file, 'r', encoding='utf-8') as f:
                channels = len([line for line in f if line.startswith('http')])
            logger.info(f"📺 televizo.m3u: {channels} каналов")
            
            size = playlist_file.stat().st_size / 1024
            logger.info(f"📁 Размер: {size:.1f} KB")
        else:
            logger.warning("Плейлист не найден!")
    
    def run(self):
        """Запуск системы"""
        logger.info("🚀 IPTV SYSTEM")
        logger.info("=" * 30)
        logger.info("📺 Парсинг доноров и создание плейлиста")
        logger.info("")
        
        steps = [
            ("Парсинг доноров", self.parse_donors),
            ("Создание плейлиста", self.create_playlist),
            ("Git push", self.git_push)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"▶️ {step_name}...")
            if not step_func():
                logger.error(f"❌ Ошибка на этапе: {step_name}")
                return False
        
        self.show_statistics()
        logger.info("🎉 СИСТЕМА ЗАВЕРШЕНА УСПЕШНО!")
        return True

if __name__ == "__main__":
    system = IPTVSystem()
    success = system.run()
    sys.exit(0 if success else 1)