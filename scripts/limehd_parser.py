#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер каналов LimeHD.TV
Извлекает прямые ссылки на потоки из бесплатного сервиса LimeHD
"""

import re
import json
import requests
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LimeHDParser:
    def __init__(self):
        self.base_url = "https://limehd.tv"
        self.api_url = "https://api.limehd.tv"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://limehd.tv',
            'Referer': 'https://limehd.tv/'
        })
        
    def get_channels_list(self):
        """Получает список всех каналов"""
        try:
            # Пробуем разные API endpoints
            endpoints = [
                f"{self.api_url}/v1/channels",
                f"{self.api_url}/channels",
                f"{self.base_url}/api/channels"
            ]
            
            for endpoint in endpoints:
                try:
                    logger.info(f"Пробуем endpoint: {endpoint}")
                    response = self.session.get(endpoint, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"✅ Получены данные с {endpoint}")
                        return data
                        
                except Exception as e:
                    logger.debug(f"Ошибка {endpoint}: {e}")
                    continue
            
            # Если API не работает, пробуем парсить HTML
            logger.info("API недоступен, пробуем парсить HTML...")
            return self.parse_html()
            
        except Exception as e:
            logger.error(f"Ошибка получения каналов: {e}")
            return None
    
    def parse_html(self):
        """Парсит HTML страницу для извлечения каналов"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            html = response.text
            
            # Ищем JSON данные в HTML (часто встраивают)
            patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                r'window\.channels\s*=\s*(\[.+?\]);',
                r'var\s+channels\s*=\s*(\[.+?\]);',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        logger.info(f"✅ Найдены данные в HTML")
                        return data
                    except:
                        continue
            
            logger.warning("Не удалось извлечь данные из HTML")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка парсинга HTML: {e}")
            return None
    
    def get_stream_url(self, channel_id):
        """Получает прямую ссылку на поток канала"""
        try:
            # Пробуем разные форматы API для получения потока
            endpoints = [
                f"{self.api_url}/v1/channels/{channel_id}/stream",
                f"{self.api_url}/stream/{channel_id}",
                f"{self.base_url}/api/stream/{channel_id}"
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.session.get(endpoint, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Ищем URL в разных форматах ответа
                        if isinstance(data, dict):
                            stream_url = (
                                data.get('url') or 
                                data.get('stream_url') or 
                                data.get('hls') or
                                data.get('stream', {}).get('url')
                            )
                            if stream_url:
                                return stream_url
                        elif isinstance(data, str):
                            return data
                            
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Ошибка получения потока для {channel_id}: {e}")
            return None
    
    def parse_channels(self):
        """Парсит все каналы и извлекает потоки"""
        logger.info("🍋 Начинаем парсинг LimeHD...")
        
        channels_data = self.get_channels_list()
        if not channels_data:
            logger.error("❌ Не удалось получить список каналов")
            return []
        
        channels = []
        
        # Обрабатываем разные форматы данных
        if isinstance(channels_data, dict):
            channels_list = (
                channels_data.get('channels') or 
                channels_data.get('data') or 
                channels_data.get('items') or
                []
            )
        elif isinstance(channels_data, list):
            channels_list = channels_data
        else:
            logger.error("Неизвестный формат данных")
            return []
        
        logger.info(f"📺 Найдено каналов: {len(channels_list)}")
        
        for idx, channel in enumerate(channels_list, 1):
            try:
                if isinstance(channel, dict):
                    channel_id = channel.get('id') or channel.get('channel_id')
                    name = channel.get('name') or channel.get('title')
                    category = channel.get('category') or channel.get('group') or 'общие'
                    logo = channel.get('logo') or channel.get('icon')
                    
                    # Получаем прямую ссылку на поток
                    stream_url = channel.get('stream_url') or channel.get('url')
                    
                    if not stream_url and channel_id:
                        stream_url = self.get_stream_url(channel_id)
                    
                    if stream_url and name:
                        channels.append({
                            'name': name,
                            'url': stream_url,
                            'category': category,
                            'logo': logo,
                            'source': 'LimeHD'
                        })
                        
                        if idx % 10 == 0:
                            logger.info(f"  Обработано: {idx}/{len(channels_list)}")
                
            except Exception as e:
                logger.debug(f"Ошибка обработки канала: {e}")
                continue
        
        logger.info(f"✅ Успешно спарсено каналов: {len(channels)}")
        return channels
    
    def save_to_m3u(self, channels, output_file="limehd_channels.m3u"):
        """Сохраняет каналы в M3U формат"""
        try:
            output_path = Path(__file__).parent.parent / "categories" / output_file
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('#EXTM3U\n')
                
                for channel in channels:
                    name = channel['name']
                    url = channel['url']
                    category = channel.get('category', 'общие')
                    logo = channel.get('logo', '')
                    
                    # Формируем EXTINF строку
                    extinf_params = []
                    if logo:
                        extinf_params.append(f'tvg-logo="{logo}"')
                    extinf_params.append(f'group-title="{category}"')
                    
                    params_str = ' '.join(extinf_params)
                    f.write(f'#EXTINF:-1 {params_str},{name}\n')
                    f.write(f'{url}\n')
            
            logger.info(f"💾 Сохранено в: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения M3U: {e}")
            return False
    
    def generate_report(self, channels):
        """Создает отчет о парсинге"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'source': 'LimeHD',
            'total_channels': len(channels),
            'categories': {},
            'channels': []
        }
        
        # Группируем по категориям
        for channel in channels:
            category = channel.get('category', 'общие')
            if category not in report['categories']:
                report['categories'][category] = 0
            report['categories'][category] += 1
            
            report['channels'].append({
                'name': channel['name'],
                'category': category,
                'has_logo': bool(channel.get('logo'))
            })
        
        # Сохраняем отчет
        report_path = Path(__file__).parent.parent / "reports" / f"limehd_report_{int(datetime.now().timestamp())}.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📊 Отчет сохранен: {report_path}")
        
        # Выводим статистику
        print("\n" + "=" * 50)
        print("📊 СТАТИСТИКА ПАРСИНГА LIMEHD")
        print("=" * 50)
        print(f"Всего каналов: {report['total_channels']}")
        print(f"\nПо категориям:")
        for cat, count in sorted(report['categories'].items(), key=lambda x: x[1], reverse=True):
            print(f"  - {cat}: {count}")
        print("=" * 50 + "\n")
        
        return report

def main():
    parser = LimeHDParser()
    
    # Парсим каналы
    channels = parser.parse_channels()
    
    if channels:
        # Сохраняем в M3U
        parser.save_to_m3u(channels)
        
        # Генерируем отчет
        parser.generate_report(channels)
        
        logger.info("✅ Парсинг LimeHD завершен успешно!")
    else:
        logger.error("❌ Не удалось спарсить каналы")
        sys.exit(1)

if __name__ == "__main__":
    import sys
    main()

