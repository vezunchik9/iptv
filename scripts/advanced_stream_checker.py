#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенная система проверки IPTV потоков на работоспособность
Использует множественные методы проверки для более точных результатов
"""

import asyncio
import aiohttp
import subprocess
import json
import time
import re
import ssl
import socket
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading
from urllib.parse import urlparse
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedStreamChecker:
    def __init__(self, timeout=15, max_concurrent=15, retry_attempts=2):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.retry_attempts = retry_attempts
        self.results = {}
        self.checking = False
        
        # Настройки для различных типов проверок
        self.check_methods = {
            'http_head': True,
            'http_get': True,
            'curl_check': True,
            'ffprobe_check': False,  # По умолчанию выключено, так как медленно
            'socket_check': True
        }
        
    async def check_with_http_head(self, session, url):
        """Проверка через HTTP HEAD запрос"""
        try:
            async with session.head(url, timeout=self.timeout, allow_redirects=True) as response:
                return {
                    'method': 'http_head',
                    'success': True,
                    'status_code': response.status,
                    'accessible': response.status in [200, 206, 301, 302, 307, 308],
                    'content_type': response.headers.get('content-type', ''),
                    'server': response.headers.get('server', ''),
                    'content_length': response.headers.get('content-length'),
                    'error': None
                }
        except Exception as e:
            return {
                'method': 'http_head',
                'success': False,
                'accessible': False,
                'error': str(e)
            }
    
    async def check_with_http_get(self, session, url):
        """Проверка через HTTP GET запрос (читаем только первые байты)"""
        try:
            # Читаем только первые 1KB для проверки доступности
            async with session.get(url, timeout=self.timeout, allow_redirects=True) as response:
                # Читаем небольшой кусок данных
                chunk = await response.content.read(1024)
                
                return {
                    'method': 'http_get',
                    'success': True,
                    'status_code': response.status,
                    'accessible': response.status in [200, 206] and len(chunk) > 0,
                    'content_type': response.headers.get('content-type', ''),
                    'bytes_read': len(chunk),
                    'error': None
                }
        except Exception as e:
            return {
                'method': 'http_get',
                'success': False,
                'accessible': False,
                'error': str(e)
            }
    
    def check_with_curl(self, url):
        """Проверка через curl"""
        try:
            # Используем curl для проверки с различными опциями
            cmd = [
                'curl', '-s', '--max-time', str(self.timeout),
                '--connect-timeout', '10',
                '--retry', '1',
                '--retry-delay', '1',
                '--user-agent', 'VLC/3.0.0 LibVLC/3.0.0',
                '--head',  # Используем HEAD запрос
                '--location',  # Следуем редиректам
                '--fail-with-body',  # Возвращаем ошибку только при реальных проблемах
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 5
            )
            
            # Анализируем результат curl
            if result.returncode == 0:
                # Ищем HTTP статус код в выводе
                status_match = re.search(r'HTTP/\d\.\d (\d+)', result.stdout)
                status_code = int(status_match.group(1)) if status_match else 0
                
                return {
                    'method': 'curl',
                    'success': True,
                    'status_code': status_code,
                    'accessible': status_code in [200, 206, 301, 302, 307, 308],
                    'error': None
                }
            else:
                # Анализируем stderr для понимания ошибки
                error_msg = result.stderr.strip() if result.stderr else 'Unknown curl error'
                return {
                    'method': 'curl',
                    'success': False,
                    'accessible': False,
                    'error': error_msg
                }
                
        except subprocess.TimeoutExpired:
            return {
                'method': 'curl',
                'success': False,
                'accessible': False,
                'error': 'Curl timeout'
            }
        except FileNotFoundError:
            return {
                'method': 'curl',
                'success': False,
                'accessible': False,
                'error': 'Curl not found'
            }
        except Exception as e:
            return {
                'method': 'curl',
                'success': False,
                'accessible': False,
                'error': str(e)
            }
    
    def check_with_ffprobe(self, url):
        """Детальная проверка потока с помощью ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                '-timeout', str(self.timeout * 1000000),  # в микросекундах
                '-f', 'hls',  # Указываем формат для HLS потоков
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 5
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                streams = data.get('streams', [])
                format_info = data.get('format', {})
                
                video_streams = [s for s in streams if s.get('codec_type') == 'video']
                audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
                
                return {
                    'method': 'ffprobe',
                    'success': True,
                    'accessible': True,
                    'video_streams': len(video_streams),
                    'audio_streams': len(audio_streams),
                    'duration': format_info.get('duration'),
                    'bitrate': format_info.get('bit_rate'),
                    'format': format_info.get('format_name'),
                    'codecs': {
                        'video': [s.get('codec_name') for s in video_streams],
                        'audio': [s.get('codec_name') for s in audio_streams]
                    },
                    'error': None
                }
            else:
                return {
                    'method': 'ffprobe',
                    'success': False,
                    'accessible': False,
                    'error': result.stderr or 'ffprobe failed'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'method': 'ffprobe',
                'success': False,
                'accessible': False,
                'error': 'ffprobe timeout'
            }
        except FileNotFoundError:
            return {
                'method': 'ffprobe',
                'success': False,
                'accessible': False,
                'error': 'ffprobe not installed'
            }
        except Exception as e:
            return {
                'method': 'ffprobe',
                'success': False,
                'accessible': False,
                'error': str(e)
            }
    
    def check_socket_connection(self, url):
        """Проверка TCP соединения к хосту"""
        try:
            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port
            
            # Определяем порт по умолчанию
            if not port:
                if parsed.scheme == 'https':
                    port = 443
                elif parsed.scheme == 'http':
                    port = 80
                else:
                    port = 80
            
            # Создаем сокет
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            # Пытаемся подключиться
            result = sock.connect_ex((host, port))
            sock.close()
            
            return {
                'method': 'socket',
                'success': result == 0,
                'accessible': result == 0,
                'host': host,
                'port': port,
                'error': f'Connection failed with code {result}' if result != 0 else None
            }
            
        except Exception as e:
            return {
                'method': 'socket',
                'success': False,
                'accessible': False,
                'error': str(e)
            }
    
    async def check_single_stream_advanced(self, channel_id, url, detailed=False):
        """Улучшенная проверка одного потока с множественными методами"""
        start_time = time.time()
        
        result = {
            'channel_id': channel_id,
            'url': url,
            'checked_at': datetime.now().isoformat(),
            'response_time': None,
            'accessible': False,
            'working': False,
            'details': None,
            'error': None,
            'check_methods': {}
        }
        
        # Список методов проверки в порядке приоритета
        methods_to_use = []
        
        if self.check_methods['http_head']:
            methods_to_use.append('http_head')
        if self.check_methods['http_get']:
            methods_to_use.append('http_get')
        if self.check_methods['curl_check']:
            methods_to_use.append('curl')
        if self.check_methods['socket_check']:
            methods_to_use.append('socket')
        if detailed and self.check_methods['ffprobe_check']:
            methods_to_use.append('ffprobe')
        
        try:
            # Создаем HTTP сессию для HTTP проверок
            connector = aiohttp.TCPConnector(
                limit=self.max_concurrent,
                ssl=False,  # Отключаем проверку SSL для IPTV потоков
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:
                
                # Выполняем проверки параллельно
                tasks = []
                
                for method in methods_to_use:
                    if method in ['http_head', 'http_get']:
                        if method == 'http_head':
                            tasks.append(self.check_with_http_head(session, url))
                        elif method == 'http_get':
                            tasks.append(self.check_with_http_get(session, url))
                    elif method == 'curl':
                        # curl запускаем в отдельном потоке
                        tasks.append(asyncio.get_event_loop().run_in_executor(
                            None, self.check_with_curl, url
                        ))
                    elif method == 'socket':
                        # socket проверку тоже в отдельном потоке
                        tasks.append(asyncio.get_event_loop().run_in_executor(
                            None, self.check_socket_connection, url
                        ))
                    elif method == 'ffprobe':
                        # ffprobe тоже в отдельном потоке
                        tasks.append(asyncio.get_event_loop().run_in_executor(
                            None, self.check_with_ffprobe, url
                        ))
                
                # Ждем результаты всех проверок
                if tasks:
                    method_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Обрабатываем результаты
                    for i, method_result in enumerate(method_results):
                        method_name = methods_to_use[i]
                        
                        if isinstance(method_result, Exception):
                            result['check_methods'][method_name] = {
                                'success': False,
                                'error': str(method_result)
                            }
                        else:
                            result['check_methods'][method_name] = method_result
                            
                            # Если хотя бы один метод показал, что поток доступен
                            if method_result.get('accessible', False):
                                result['accessible'] = True
                                result['working'] = True
                                
                                # Сохраняем детали от первого успешного метода
                                if not result['details']:
                                    result['details'] = method_result
                
                # Если ни один метод не показал доступность, ищем ошибки
                if not result['accessible']:
                    # Собираем все ошибки
                    errors = []
                    for method_name, method_result in result['check_methods'].items():
                        if not method_result.get('success', False):
                            error = method_result.get('error', 'Unknown error')
                            errors.append(f"{method_name}: {error}")
                    
                    result['error'] = '; '.join(errors) if errors else 'All check methods failed'
            
            result['response_time'] = round((time.time() - start_time) * 1000, 2)
            
        except Exception as e:
            result['error'] = str(e)
            result['response_time'] = round((time.time() - start_time) * 1000, 2)
        
        return result
    
    async def check_multiple_streams_advanced(self, channels, detailed=False, progress_callback=None):
        """Улучшенная проверка нескольких потоков параллельно"""
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
                    # Повторные попытки для надежности
                    for attempt in range(self.retry_attempts + 1):
                        result = await self.check_single_stream_advanced(
                            channel['id'],
                            channel['url'],
                            detailed
                        )
                        
                        # Если получили успешный результат или это последняя попытка
                        if result['accessible'] or attempt == self.retry_attempts:
                            break
                        
                        # Небольшая задержка перед повтором
                        if attempt < self.retry_attempts:
                            await asyncio.sleep(1)
                    
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
        """Возвращает улучшенную статистику проверки"""
        if not self.results:
            return {}
        
        total = len(self.results)
        accessible = sum(1 for r in self.results.values() if r['accessible'])
        working = sum(1 for r in self.results.values() if r['working'])
        
        # Статистика по методам проверки
        method_stats = {}
        for result in self.results.values():
            for method_name, method_result in result.get('check_methods', {}).items():
                if method_name not in method_stats:
                    method_stats[method_name] = {'total': 0, 'success': 0}
                
                method_stats[method_name]['total'] += 1
                if method_result.get('success', False):
                    method_stats[method_name]['success'] += 1
        
        # Вычисляем среднее время ответа
        response_times = [r['response_time'] for r in self.results.values() 
                         if r['response_time'] is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'total_checked': total,
            'accessible': accessible,
            'working': working,
            'success_rate': round((working / total) * 100, 2) if total > 0 else 0,
            'accessibility_rate': round((accessible / total) * 100, 2) if total > 0 else 0,
            'avg_response_time': round(avg_response_time, 2),
            'method_statistics': method_stats,
            'checked_at': datetime.now().isoformat()
        }
    
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
            
            logger.info(f"Загружено {len(channels)} каналов для проверки")
            return channels
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке M3U: {e}")
            return []
    
    def save_results(self, filename):
        """Сохраняет результаты в JSON файл"""
        try:
            report = {
                'statistics': self.get_statistics(),
                'results': self.results,
                'generated_at': datetime.now().isoformat(),
                'checker_version': '2.0_advanced',
                'settings': {
                    'timeout': self.timeout,
                    'max_concurrent': self.max_concurrent,
                    'retry_attempts': self.retry_attempts,
                    'check_methods': self.check_methods
                }
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Отчет сохранен: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении отчета: {e}")
            return False

async def main():
    """Основная функция для командной строки"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Улучшенная проверка IPTV потоков')
    parser.add_argument('m3u_file', help='Путь к M3U файлу')
    parser.add_argument('--detailed', action='store_true', help='Детальная проверка с ffprobe')
    parser.add_argument('--output', '-o', help='Файл для сохранения отчета')
    parser.add_argument('--timeout', type=int, default=15, help='Таймаут в секундах')
    parser.add_argument('--concurrent', type=int, default=15, help='Количество одновременных проверок')
    parser.add_argument('--retry', type=int, default=2, help='Количество повторных попыток')
    parser.add_argument('--methods', nargs='+', 
                       choices=['http_head', 'http_get', 'curl', 'socket', 'ffprobe'],
                       help='Методы проверки (по умолчанию: http_head, http_get, curl, socket)')
    
    args = parser.parse_args()
    
    # Создаем проверятель
    checker = AdvancedStreamChecker(
        timeout=args.timeout, 
        max_concurrent=args.concurrent,
        retry_attempts=args.retry
    )
    
    # Настраиваем методы проверки
    if args.methods:
        # Сбрасываем все методы
        for method in checker.check_methods:
            checker.check_methods[method] = False
        # Включаем только указанные
        for method in args.methods:
            if method in checker.check_methods:
                checker.check_methods[method] = True
    
    # Включаем ffprobe если нужна детальная проверка
    if args.detailed:
        checker.check_methods['ffprobe_check'] = True
    
    print("📡 Загрузка каналов...")
    channels = checker.load_channels_from_m3u(args.m3u_file)
    
    if not channels:
        print("❌ Не удалось загрузить каналы")
        return
    
    print(f"🔍 Начинаем улучшенную проверку {len(channels)} каналов...")
    print(f"⚙️ Настройки: таймаут={args.timeout}с, одновременно={args.concurrent}, повторов={args.retry}")
    
    active_methods = [method for method, enabled in checker.check_methods.items() if enabled]
    print(f"🔧 Методы проверки: {', '.join(active_methods)}")
    
    def progress_callback(completed, total, result):
        status = "✅" if result['working'] else "❌"
        methods_used = len(result.get('check_methods', {}))
        print(f"[{completed}/{total}] {result['channel_id']}: {result['url'][:50]}... "
              f"{status} ({result['response_time']}мс, {methods_used} методов)")
    
    start_time = time.time()
    results = await checker.check_multiple_streams_advanced(channels, args.detailed, progress_callback)
    duration = time.time() - start_time
    
    print(f"\n🎯 Проверка завершена за {duration:.1f} секунд")
    
    # Статистика
    stats = checker.get_statistics()
    print(f"\n📊 СТАТИСТИКА:")
    print(f"  Всего проверено: {stats['total_checked']}")
    print(f"  Доступны: {stats['accessible']} ({stats['accessibility_rate']}%)")
    print(f"  Работают: {stats['working']} ({stats['success_rate']}%)")
    print(f"  Среднее время ответа: {stats['avg_response_time']}мс")
    
    # Статистика по методам
    if 'method_statistics' in stats:
        print(f"\n🔧 СТАТИСТИКА ПО МЕТОДАМ:")
        for method, method_stats in stats['method_statistics'].items():
            success_rate = (method_stats['success'] / method_stats['total']) * 100
            print(f"  {method}: {method_stats['success']}/{method_stats['total']} ({success_rate:.1f}%)")
    
    # Сохранение отчета
    if args.output:
        checker.save_results(args.output)
    else:
        default_filename = f"advanced_stream_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        checker.save_results(default_filename)

if __name__ == "__main__":
    asyncio.run(main())
