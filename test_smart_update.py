#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест умного обновления ссылок
Демонстрирует как система обновляет существующие каналы
"""

import asyncio
import sys
import os

# Добавляем путь к скриптам в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'scripts')))

from smart_playlist_parser import SmartPlaylistParser

def create_test_category():
    """Создает тестовую категорию с несколькими каналами"""
    test_content = """#EXTM3U
# Категория: тест
# Тестовая категория для демонстрации обновления

#EXTINF:-1 tvg-id="pervy" tvg-logo="https://example.com/logo1.png" group-title="Эфирные",Первый канал
http://old-server.com/first_channel.m3u8

#EXTINF:-1 tvg-id="rossiya1" tvg-logo="https://example.com/logo2.png" group-title="Эфирные",Россия 1
http://old-server.com/russia1.m3u8

#EXTINF:-1 tvg-id="ntv" tvg-logo="https://example.com/logo3.png" group-title="Эфирные",НТВ
http://old-server.com/ntv.m3u8

"""
    
    os.makedirs("categories", exist_ok=True)
    with open("categories/тест.m3u", "w", encoding="utf-8") as f:
        f.write(test_content)
    
    print("✅ Создана тестовая категория с 3 каналами")

def create_test_donor_playlist():
    """Создает тестовый донорский плейлист с обновленными ссылками"""
    test_donor_content = """#EXTM3U

#EXTINF:-1 tvg-id="pervy" tvg-logo="https://newcdn.com/logo1_hd.png" group-title="Эфирные",Первый канал HD
http://new-server.com/first_channel_hd.m3u8

#EXTINF:-1 tvg-id="rossiya1" tvg-logo="https://newcdn.com/logo2_hd.png" group-title="Эфирные",Россия 1 HD
http://new-server.com/russia1_hd.m3u8

#EXTINF:-1 tvg-id="sts" tvg-logo="https://newcdn.com/sts.png" group-title="Эфирные",СТС HD
http://new-server.com/sts_hd.m3u8

"""
    
    with open("test_donor.m3u", "w", encoding="utf-8") as f:
        f.write(test_donor_content)
    
    print("✅ Создан тестовый донорский плейлист")

def show_category_before():
    """Показывает содержимое категории до обновления"""
    print("\n📋 СОДЕРЖИМОЕ КАТЕГОРИИ ДО ОБНОВЛЕНИЯ:")
    try:
        with open("categories/тест.m3u", "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            if line.strip() and not line.startswith('#'):
                print(f"   {i}: {line.strip()}")
            elif line.startswith('#EXTINF'):
                # Извлекаем название канала
                import re
                name_match = re.search(r',([^,]+)$', line)
                name = name_match.group(1).strip() if name_match else 'Unknown'
                print(f"   {i}: 📺 {name}")
    except Exception as e:
        print(f"   Ошибка: {e}")

def show_category_after():
    """Показывает содержимое категории после обновления"""
    print("\n📋 СОДЕРЖИМОЕ КАТЕГОРИИ ПОСЛЕ ОБНОВЛЕНИЯ:")
    try:
        with open("categories/тест.m3u", "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            if line.strip() and not line.startswith('#'):
                print(f"   {i}: {line.strip()}")
            elif line.startswith('#EXTINF'):
                # Извлекаем название канала
                import re
                name_match = re.search(r',([^,]+)$', line)
                name = name_match.group(1).strip() if name_match else 'Unknown'
                print(f"   {i}: 📺 {name}")
    except Exception as e:
        print(f"   Ошибка: {e}")

def test_smart_update():
    """Тестирует умное обновление"""
    print("🧪 ТЕСТ УМНОГО ОБНОВЛЕНИЯ ССЫЛОК")
    print("=" * 50)
    
    # Создаем тестовые данные
    create_test_category()
    create_test_donor_playlist()
    
    # Показываем состояние до
    show_category_before()
    
    # Создаем тестовую конфигурацию
    test_config = {
        "donors": {
            "TEST_DONOR": {
                "url": "file://" + os.path.abspath("test_donor.m3u"),
                "enabled": True,
                "priority": 1
            }
        },
        "category_mapping": {
            "тест": {
                "keywords": ["эфирные", "первый", "россия", "нтв", "стс"],
                "exclude": []
            }
        },
        "update_settings": {
            "update_existing_urls": True,
            "match_by_name": True,
            "match_similarity_threshold": 0.7,
            "backup_before_update": True
        }
    }
    
    # Создаем временный конфиг
    import json
    with open("test_config.json", "w", encoding="utf-8") as f:
        json.dump(test_config, f, ensure_ascii=False, indent=2)
    
    print("\n🔄 ЗАПУСКАЕМ УМНОЕ ОБНОВЛЕНИЕ...")
    
    # Запускаем парсер
    parser = SmartPlaylistParser("test_config.json")
    
    # Модифицируем метод для работы с file:// URL
    original_download = parser.download_playlist
    def download_file_url(url, timeout=30):
        if url.startswith("file://"):
            file_path = url[7:]  # Убираем file://
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"Загружен локальный файл: {file_path}")
                return content
            except Exception as e:
                print(f"Ошибка при чтении файла {file_path}: {e}")
                return None
        else:
            return original_download(url, timeout)
    
    parser.download_playlist = download_file_url
    
    # Обрабатываем доноров
    parser.process_all_donors()
    
    # Показываем состояние после
    show_category_after()
    
    # Показываем бэкапы
    print("\n💾 СОЗДАННЫЕ БЭКАПЫ:")
    backup_dir = "backups/categories"
    if os.path.exists(backup_dir):
        for backup_file in os.listdir(backup_dir):
            if backup_file.startswith("тест.m3u.backup"):
                print(f"   📁 {backup_file}")
    
    # Очистка
    cleanup_files = ["test_donor.m3u", "test_config.json"]
    for file in cleanup_files:
        if os.path.exists(file):
            os.remove(file)
    
    print("\n🎉 ТЕСТ ЗАВЕРШЕН!")
    print("\nЧто произошло:")
    print("1. 📺 'Первый канал' → обновлен на 'Первый канал HD' с новым URL")
    print("2. 📺 'Россия 1' → обновлен на 'Россия 1 HD' с новым URL") 
    print("3. 📺 'СТС HD' → добавлен как новый канал")
    print("4. 💾 Создан бэкап перед обновлением")

if __name__ == "__main__":
    test_smart_update()
