#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Система проверки IPTV потоков на работоспособность
"""

import asyncio
import aiohttp
import subprocess
import json
import time
import re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading
from urllib.parse import urlparse

class StreamChecker:
    def __init__(self, timeout=10, max_concurrent=20):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.results = {}
        self.checking = False
        
    async def check_url_availability(self, session, url):
        """Быстрая проверка доступности URL"""
        try:
            async with session.head(url, timeout=self.timeout) as response:
                return {
                    'status_code': response.status,
                    'accessible': response.status in [200, 206, 301, 302],
                    'content_type': response.headers.get('content-type', ''),
                    'server': response.headers.get('server', ''),
                    'error': None
                }
        except asyncio.TimeoutError:
            return {'accessible': False, 'error': 'Timeout'}
        except Exception as e:
            return {'accessible': False, 'error': str(e)}
    
    def check_stream_with_ffprobe(self, url):
        """Детальная проверка потока с помощью ffprobe"""
        try:
            cmd = [
                'ffprobe', 
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                '-timeout', '10000000',  # 10 секунд в микросекундах
                url
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                streams = data.get('streams', [])
                format_info = data.get('format', {})
                
                video_streams = [s for s in streams if s.get('codec_type') == 'video']
                audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
                
                return {
                    'working': True,
                    'video_streams': len(video_streams),
                    'audio_streams': len(audio_streams),
                    'duration': format_info.get('duration'),
                    'bitrate': format_info.get('bit_rate'),
                    'format': format_info.get('format_name'),
                    'codecs': {
                        'video': [s.get('codec_name') for s in video_streams],
                        'audio': [s.get('codec_name') for s in audio_streams]
                    },
                    'resolution': self._get_resolution(video_streams),
                    'error': None
                }
            else:
                return {
                    'working': False,
                    'error': result.stderr or 'ffprobe failed'
                }
                
        except subprocess.TimeoutExpired:
            return {'working': False, 'error': 'Timeout (ffprobe)'}
        except FileNotFoundError:
            return {'working': False, 'error': 'ffprobe not installed'}
        except Exception as e:
            return {'working': False, 'error': str(e)}
    
    def _get_resolution(self, video_streams):
        """Извлекает разрешение из видео потоков"""
        if not video_streams:
            return None
        
        stream = video_streams[0]
        width = stream.get('width')
        height = stream.get('height')
        
        if width and height:
            return f"{width}x{height}"
        return None
    
    async def check_single_stream(self, channel_id, url, detailed=False):
        """Проверяет один поток"""
        start_time = time.time()
        
        result = {
            'channel_id': channel_id,
            'url': url,
            'checked_at': datetime.now().isoformat(),
            'response_time': None,
            'accessible': False,
            'working': False,
            'details': None,
            'error': None
        }
        
        try:
            # Быстрая проверка доступности
            connector = aiohttp.TCPConnector(limit=self.max_concurrent)
            async with aiohttp.ClientSession(
                connector=connector, 
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                availability = await self.check_url_availability(session, url)
                
            result['response_time'] = round((time.time() - start_time) * 1000, 2)  # в мс
            result['accessible'] = availability['accessible']
            result['error'] = availability.get('error')
            
            # Если доступен и нужна детальная проверка
            if availability['accessible'] and detailed:
                stream_info = await asyncio.get_event_loop().run_in_executor(
                    None, self.check_stream_with_ffprobe, url
                )
                result['working'] = stream_info.get('working', False)
                result['details'] = stream_info
                if stream_info.get('error'):
                    result['error'] = stream_info['error']
            elif availability['accessible']:
                result['working'] = True  # Если доступен, считаем работающим
                
        except Exception as e:
            result['error'] = str(e)
            result['response_time'] = round((time.time() - start_time) * 1000, 2)
        
        return result
    
    async def check_multiple_streams(self, channels, detailed=False, progress_callback=None):
        """Проверяет несколько потоков параллельно"""
        self.checking = True
        self.results = {}
        
        try:
            total = len(channels)
            completed = 0
            
            # Создаем семафор для ограничения количества одновременных проверок
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def check_with_semaphore(channel):
                nonlocal completed
                async with semaphore:
                    result = await self.check_single_stream(
                        channel['id'], 
                        channel['url'], 
                        detailed
                    )
                    
                    self.results[channel['id']] = result
                    completed += 1
                    
                    if progress_callback:
                        progress_callback(completed, total, result)
                    
                    return result
            
            # Запускаем все проверки параллельно
            tasks = [check_with_semaphore(channel) for channel in channels]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            return self.results
            
        finally:
            self.checking = False
    
    def get_statistics(self):
        """Возвращает статистику проверки"""
        if not self.results:
            return {}
        
        total = len(self.results)
        accessible = sum(1 for r in self.results.values() if r['accessible'])
        working = sum(1 for r in self.results.values() if r['working'])
        errors = sum(1 for r in self.results.values() if r['error'])
        
        avg_response_time = sum(
            r['response_time'] for r in self.results.values() 
            if r['response_time'] is not None
        ) / max(1, sum(1 for r in self.results.values() if r['response_time'] is not None))
        
        return {
            'total_checked': total,
            'accessible': accessible,
            'working': working,
            'errors': errors,
            'success_rate': round((working / total) * 100, 2) if total > 0 else 0,
            'accessibility_rate': round((accessible / total) * 100, 2) if total > 0 else 0,
            'avg_response_time': round(avg_response_time, 2),
            'checked_at': datetime.now().isoformat()
        }
    
    def save_results(self, filename):
        """Сохраняет результаты в JSON файл"""
        try:
            report = {
                'statistics': self.get_statistics(),
                'results': self.results,
                'generated_at': datetime.now().isoformat()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Отчет сохранен: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при сохранении отчета: {e}")
            return False
    
    def load_channels_from_m3u(self, m3u_file):
        """Загружает каналы из M3U файла"""
        channels = []
        
        try:
            with open(m3u_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.splitlines()
            current_extinf = None
            channel_id = 0
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('#EXTINF'):
                    current_extinf = line
                elif line and not line.startswith('#') and current_extinf:
                    # Парсим информацию о канале
                    name_match = re.search(r',(.*)$', current_extinf)
                    name = name_match.group(1).strip() if name_match else f"Channel {channel_id}"
                    
                    group_match = re.search(r'group-title="([^"]*)"', current_extinf)
                    group = group_match.group(1) if group_match else "Unknown"
                    
                    channels.append({
                        'id': channel_id,
                        'name': name,
                        'url': line,
                        'group': group
                    })
                    
                    channel_id += 1
                    current_extinf = None
            
            print(f"✅ Загружено {len(channels)} каналов для проверки")
            return channels
            
        except Exception as e:
            print(f"❌ Ошибка при загрузке M3U: {e}")
            return []

class StreamCheckerAPI:
    """API для интеграции с веб-интерфейсом"""
    
    def __init__(self):
        self.checker = StreamChecker()
        self.current_task = None
        self.progress = {'completed': 0, 'total': 0, 'current': None}
    
    def start_check(self, channels, detailed=False):
        """Запускает проверку в фоне"""
        if self.checker.checking:
            return {'status': 'error', 'message': 'Проверка уже выполняется'}
        
        def progress_callback(completed, total, result):
            self.progress = {
                'completed': completed,
                'total': total,
                'current': result['channel_id'],
                'percentage': round((completed / total) * 100, 2)
            }
        
        async def run_check():
            return await self.checker.check_multiple_streams(
                channels, detailed, progress_callback
            )
        
        self.current_task = asyncio.create_task(run_check())
        return {'status': 'started', 'message': 'Проверка запущена'}
    
    def get_progress(self):
        """Возвращает прогресс проверки"""
        return {
            'checking': self.checker.checking,
            'progress': self.progress,
            'statistics': self.checker.get_statistics() if self.checker.results else None
        }
    
    def get_results(self):
        """Возвращает результаты проверки"""
        return {
            'results': self.checker.results,
            'statistics': self.checker.get_statistics()
        }

async def main():
    """Основная функция для командной строки"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Проверка IPTV потоков')
    parser.add_argument('m3u_file', help='Путь к M3U файлу')
    parser.add_argument('--detailed', action='store_true', help='Детальная проверка с ffprobe')
    parser.add_argument('--output', '-o', help='Файл для сохранения отчета')
    parser.add_argument('--timeout', type=int, default=10, help='Таймаут в секундах')
    parser.add_argument('--concurrent', type=int, default=20, help='Количество одновременных проверок')
    
    args = parser.parse_args()
    
    checker = StreamChecker(timeout=args.timeout, max_concurrent=args.concurrent)
    
    print("📡 Загрузка каналов...")
    channels = checker.load_channels_from_m3u(args.m3u_file)
    
    if not channels:
        print("❌ Не удалось загрузить каналы")
        return
    
    print(f"🔍 Начинаем проверку {len(channels)} каналов...")
    print(f"⚙️ Настройки: таймаут={args.timeout}с, одновременно={args.concurrent}")
    
    if args.detailed:
        print("🔬 Включена детальная проверка (медленнее)")
    
    def progress_callback(completed, total, result):
        print(f"[{completed}/{total}] {result['channel_id']}: {result['url'][:50]}... "
              f"{'✅' if result['working'] else '❌'} "
              f"({result['response_time']}мс)")
    
    start_time = time.time()
    results = await checker.check_multiple_streams(channels, args.detailed, progress_callback)
    duration = time.time() - start_time
    
    print(f"\n🎯 Проверка завершена за {duration:.1f} секунд")
    
    # Статистика
    stats = checker.get_statistics()
    print(f"\n📊 СТАТИСТИКА:")
    print(f"  Всего проверено: {stats['total_checked']}")
    print(f"  Доступны: {stats['accessible']} ({stats['accessibility_rate']}%)")
    print(f"  Работают: {stats['working']} ({stats['success_rate']}%)")
    print(f"  Ошибки: {stats['errors']}")
    print(f"  Среднее время ответа: {stats['avg_response_time']}мс")
    
    # Сохранение отчета
    if args.output:
        checker.save_results(args.output)
    else:
        default_filename = f"stream_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        checker.save_results(default_filename)

if __name__ == "__main__":
    asyncio.run(main())
