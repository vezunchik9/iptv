#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенная проверка IPTV потоков через curl
Анализирует реальную скорость загрузки и стабильность потоков
"""

import asyncio
import subprocess
import json
import time
import re
import threading
import queue
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CurlStreamChecker:
    def __init__(self, timeout=30, max_concurrent=10, test_duration=15):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.test_duration = test_duration
        self.results = {}
        self.checking = False
        
    def _check_stream_with_curl_detailed(self, url, test_duration=15):
        """Детальная проверка потока через curl с анализом скорости и стабильности"""
        try:
            # Команда curl для детального анализа потока
            cmd = [
                'curl',
                '-s',                    # Тихий режим
                '--max-time', str(test_duration),
                '--connect-timeout', '10',
                '--retry', '0',         # Не повторяем запросы
                '--retry-delay', '0',
                '--user-agent', 'VLC/3.0.0 LibVLC/3.0.0',
                '--location',            # Следуем редиректам
                '--fail-with-body',
                '--write-out', 'HTTP_CODE:%{http_code}|TIME_TOTAL:%{time_total}|SPEED_DOWNLOAD:%{speed_download}|SIZE_DOWNLOAD:%{size_download}|CONNECT_TIME:%{time_connect}|STARTTRANSFER_TIME:%{time_starttransfer}|REDIRECT_TIME:%{time_redirect}|REDIRECT_COUNT:%{num_redirects}',
                '--output', '/dev/null',
                url
            ]
            
            start_time = time.time()
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            duration = time.time() - start_time
            
            # Парсим результат curl
            if result.returncode == 0 and result.stdout:
                try:
                    # Парсим детальную информацию
                    info = {}
                    for part in result.stdout.strip().split('|'):
                        if ':' in part:
                            key, value = part.split(':', 1)
                            try:
                                # Пытаемся преобразовать в число
                                info[key] = float(value) if '.' in value else int(value)
                            except ValueError:
                                info[key] = value
                    
                    http_code = info.get('HTTP_CODE', 0)
                    time_total = info.get('TIME_TOTAL', 0)
                    speed_download = info.get('SPEED_DOWNLOAD', 0)
                    size_download = info.get('SIZE_DOWNLOAD', 0)
                    connect_time = info.get('CONNECT_TIME', 0)
                    starttransfer_time = info.get('STARTTRANSFER_TIME', 0)
                    redirect_count = info.get('REDIRECT_COUNT', 0)
                    
                    # Анализируем качество потока
                    working = False
                    quality_score = 0
                    issues = []
                    
                    # Проверка HTTP кода
                    if http_code == 200:
                        quality_score += 30
                    elif http_code in [301, 302, 307, 308]:
                        quality_score += 20
                        issues.append(f"Redirect (code {http_code})")
                    else:
                        issues.append(f"HTTP error {http_code}")
                    
                    # Проверка скорости загрузки
                    if speed_download > 100000:  # > 100KB/s
                        quality_score += 40
                    elif speed_download > 10000:  # > 10KB/s
                        quality_score += 20
                    elif speed_download > 1000:   # > 1KB/s
                        quality_score += 10
                    else:
                        issues.append(f"Low speed: {speed_download:.0f} bytes/s")
                    
                    # Проверка размера загруженных данных
                    if size_download > 1000000:  # > 1MB
                        quality_score += 20
                    elif size_download > 100000:  # > 100KB
                        quality_score += 10
                    elif size_download < 1000:    # < 1KB
                        issues.append(f"Small download: {size_download} bytes")
                    
                    # Проверка времени соединения
                    if connect_time < 2:
                        quality_score += 10
                    elif connect_time > 10:
                        issues.append(f"Slow connection: {connect_time:.1f}s")
                    
                    # Проверка времени до первого байта
                    if starttransfer_time < 5:
                        quality_score += 10
                    elif starttransfer_time > 15:
                        issues.append(f"Slow start: {starttransfer_time:.1f}s")
                    
                    # Определяем работоспособность
                    working = quality_score >= 60 and http_code in [200, 301, 302, 307, 308]
                    
                    return {
                        'method': 'curl_detailed',
                        'success': True,
                        'working': working,
                        'quality_score': quality_score,
                        'duration': duration,
                        'http_code': http_code,
                        'speed_download': speed_download,
                        'size_download': size_download,
                        'connect_time': connect_time,
                        'starttransfer_time': starttransfer_time,
                        'redirect_count': redirect_count,
                        'issues': issues,
                        'error': None if working else '; '.join(issues)
                    }
                    
                except (ValueError, KeyError) as e:
                    return {
                        'method': 'curl_detailed',
                        'success': False,
                        'working': False,
                        'duration': duration,
                        'error': f'Parse error: {str(e)}'
                    }
            
            return {
                'method': 'curl_detailed',
                'success': False,
                'working': False,
                'duration': duration,
                'error': result.stderr.strip() if result.stderr else f'curl failed with code {result.returncode}'
            }
            
        except subprocess.TimeoutExpired:
            return {
                'method': 'curl_detailed',
                'success': False,
                'working': False,
                'duration': self.timeout,
                'error': 'curl timeout'
            }
        except Exception as e:
            return {
                'method': 'curl_detailed',
                'success': False,
                'working': False,
                'duration': 0,
                'error': str(e)
            }
    
    def _check_stream_with_curl_chunks(self, url, test_duration=15):
        """Проверка потока через curl с анализом по чанкам (для HLS)"""
        try:
            # Для HLS потоков пробуем загрузить playlist и несколько сегментов
            parsed_url = urlparse(url)
            
            # Сначала проверяем доступность основного плейлиста
            playlist_cmd = [
                'curl',
                '-s',
                '--max-time', '10',
                '--connect-timeout', '5',
                '--user-agent', 'VLC/3.0.0 LibVLC/3.0.0',
                '--location',
                '--write-out', 'HTTP_CODE:%{http_code}|SIZE_DOWNLOAD:%{size_download}',
                '--output', '/dev/null',
                url
            ]
            
            result = subprocess.run(playlist_cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode != 0:
                return {
                    'method': 'curl_chunks',
                    'success': False,
                    'working': False,
                    'duration': 0,
                    'error': 'Playlist not accessible'
                }
            
            # Парсим информацию о плейлисте
            playlist_info = {}
            for part in result.stdout.strip().split('|'):
                if ':' in part:
                    key, value = part.split(':', 1)
                    try:
                        playlist_info[key] = float(value) if '.' in value else int(value)
                    except ValueError:
                        playlist_info[key] = value
            
            # Если это HLS плейлист, пробуем загрузить несколько сегментов
            if url.endswith('.m3u8') or 'm3u8' in url:
                # Пытаемся получить содержимое плейлиста
                try:
                    playlist_content_cmd = [
                        'curl',
                        '-s',
                        '--max-time', '10',
                        '--user-agent', 'VLC/3.0.0 LibVLC/3.0.0',
                        url
                    ]
                    
                    content_result = subprocess.run(
                        playlist_content_cmd, 
                        capture_output=True, 
                        text=True, 
                        timeout=10
                    )
                    
                    if content_result.returncode == 0 and content_result.stdout:
                        # Анализируем плейлист
                        lines = content_result.stdout.splitlines()
                        segment_urls = []
                        
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # Относительный URL
                                if line.startswith('/'):
                                    segment_url = f"{parsed_url.scheme}://{parsed_url.netloc}{line}"
                                elif line.startswith('http'):
                                    segment_url = line
                                else:
                                    # Относительный путь
                                    base_url = '/'.join(url.split('/')[:-1])
                                    segment_url = f"{base_url}/{line}"
                                
                                segment_urls.append(segment_url)
                        
                        # Тестируем первые несколько сегментов
                        working_segments = 0
                        total_segments = min(3, len(segment_urls))
                        
                        for i, segment_url in enumerate(segment_urls[:total_segments]):
                            segment_cmd = [
                                'curl',
                                '-s',
                                '--max-time', '5',
                                '--connect-timeout', '3',
                                '--user-agent', 'VLC/3.0.0 LibVLC/3.0.0',
                                '--write-out', 'HTTP_CODE:%{http_code}|SIZE_DOWNLOAD:%{size_download}',
                                '--output', '/dev/null',
                                segment_url
                            ]
                            
                            seg_result = subprocess.run(segment_cmd, capture_output=True, text=True, timeout=8)
                            
                            if seg_result.returncode == 0:
                                seg_info = {}
                                for part in seg_result.stdout.strip().split('|'):
                                    if ':' in part:
                                        key, value = part.split(':', 1)
                                        try:
                                            seg_info[key] = float(value) if '.' in value else int(value)
                                        except ValueError:
                                            seg_info[key] = value
                                
                                if seg_info.get('HTTP_CODE') == 200 and seg_info.get('SIZE_DOWNLOAD', 0) > 1000:
                                    working_segments += 1
                        
                        # Определяем результат на основе доступности сегментов
                        working = working_segments > 0
                        quality_score = (working_segments / total_segments) * 100 if total_segments > 0 else 0
                        
                        return {
                            'method': 'curl_chunks',
                            'success': True,
                            'working': working,
                            'quality_score': quality_score,
                            'duration': time.time() - time.time(),
                            'playlist_accessible': playlist_info.get('HTTP_CODE') == 200,
                            'segments_found': len(segment_urls),
                            'segments_tested': total_segments,
                            'segments_working': working_segments,
                            'error': None if working else f'Only {working_segments}/{total_segments} segments working'
                        }
                
                except Exception as e:
                    logger.debug(f"Error analyzing HLS playlist: {e}")
            
            # Для обычных потоков возвращаем результат проверки плейлиста
            working = playlist_info.get('HTTP_CODE') == 200 and playlist_info.get('SIZE_DOWNLOAD', 0) > 0
            
            return {
                'method': 'curl_chunks',
                'success': True,
                'working': working,
                'quality_score': 80 if working else 0,
                'duration': 0,
                'playlist_accessible': playlist_info.get('HTTP_CODE') == 200,
                'segments_found': 0,
                'segments_tested': 0,
                'segments_working': 0,
                'error': None if working else 'Playlist not accessible'
            }
            
        except Exception as e:
            return {
                'method': 'curl_chunks',
                'success': False,
                'working': False,
                'duration': 0,
                'error': str(e)
            }
    
    def check_single_stream_curl(self, channel_id, url, test_duration=None):
        """Проверка одного потока через curl с детальным анализом"""
        if test_duration is None:
            test_duration = self.test_duration
            
        start_time = time.time()
        
        result = {
            'channel_id': channel_id,
            'url': url,
            'checked_at': datetime.now().isoformat(),
            'response_time': None,
            'working': False,
            'quality_score': 0,
            'details': None,
            'error': None,
            'test_duration': test_duration
        }
        
        try:
            # Выполняем детальную проверку
            detailed_result = self._check_stream_with_curl_detailed(url, test_duration)
            
            # Если это HLS поток, дополнительно проверяем сегменты
            if url.endswith('.m3u8') or 'm3u8' in url:
                chunks_result = self._check_stream_with_curl_chunks(url, test_duration)
                
                # Объединяем результаты
                if chunks_result.get('working', False):
                    result['working'] = True
                    result['quality_score'] = max(
                        detailed_result.get('quality_score', 0),
                        chunks_result.get('quality_score', 0)
                    )
                    result['details'] = {
                        'detailed': detailed_result,
                        'chunks': chunks_result
                    }
                else:
                    result['working'] = detailed_result.get('working', False)
                    result['quality_score'] = detailed_result.get('quality_score', 0)
                    result['details'] = detailed_result
                    result['error'] = detailed_result.get('error')
            else:
                # Для обычных потоков используем только детальную проверку
                result['working'] = detailed_result.get('working', False)
                result['quality_score'] = detailed_result.get('quality_score', 0)
                result['details'] = detailed_result
                result['error'] = detailed_result.get('error')
            
            result['response_time'] = round((time.time() - start_time) * 1000, 2)
            
        except Exception as e:
            result['error'] = str(e)
            result['response_time'] = round((time.time() - start_time) * 1000, 2)
        
        return result
    
    async def check_multiple_streams_curl(self, channels, test_duration=None, progress_callback=None):
        """Проверка нескольких потоков через curl параллельно"""
        self.checking = True
        self.results = {}
        
        try:
            total = len(channels)
            completed = 0
            
            # Создаем пул потоков для выполнения проверок
            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                
                # Создаем задачи
                loop = asyncio.get_event_loop()
                tasks = []
                
                for channel in channels:
                    task = loop.run_in_executor(
                        executor,
                        self.check_single_stream_curl,
                        channel['id'],
                        channel['url'],
                        test_duration
                    )
                    tasks.append((channel, task))
                
                # Обрабатываем результаты по мере готовности
                for channel, task in tasks:
                    try:
                        result = await task
                        
                        self.results[channel['id']] = result
                        completed += 1
                        
                        if progress_callback:
                            progress_callback(completed, total, result)
                        
                    except Exception as e:
                        logger.error(f"Ошибка при проверке канала {channel['id']}: {e}")
                        completed += 1
            
            return self.results
            
        finally:
            self.checking = False
    
    def get_statistics(self):
        """Возвращает статистику проверки"""
        if not self.results:
            return {}
        
        total = len(self.results)
        working = sum(1 for r in self.results.values() if r['working'])
        
        # Статистика по качеству
        quality_scores = [r['quality_score'] for r in self.results.values() if r['quality_score'] > 0]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Статистика по типам потоков
        hls_count = sum(1 for r in self.results.values() 
                       if r['url'].endswith('.m3u8') or 'm3u8' in r['url'])
        
        # Статистика по проблемам
        speed_issues = sum(1 for r in self.results.values() 
                          if r.get('details', {}).get('issues') and 
                          any('speed' in issue.lower() for issue in r['details']['issues']))
        
        connection_issues = sum(1 for r in self.results.values() 
                               if r.get('details', {}).get('issues') and 
                               any('connection' in issue.lower() or 'connect' in issue.lower() 
                                   for issue in r['details']['issues']))
        
        # Вычисляем среднее время ответа
        response_times = [r['response_time'] for r in self.results.values() 
                         if r['response_time'] is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'total_checked': total,
            'working': working,
            'success_rate': round((working / total) * 100, 2) if total > 0 else 0,
            'avg_response_time': round(avg_response_time, 2),
            'avg_quality_score': round(avg_quality, 2),
            'hls_streams': hls_count,
            'speed_issues': speed_issues,
            'connection_issues': connection_issues,
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
            
            logger.info(f"Загружено {len(channels)} каналов для curl проверки")
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
                'checker_version': '3.1_curl_advanced',
                'settings': {
                    'timeout': self.timeout,
                    'max_concurrent': self.max_concurrent,
                    'test_duration': self.test_duration
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
    
    parser = argparse.ArgumentParser(description='Улучшенная проверка IPTV потоков через curl')
    parser.add_argument('m3u_file', help='Путь к M3U файлу')
    parser.add_argument('--output', '-o', help='Файл для сохранения отчета')
    parser.add_argument('--timeout', type=int, default=30, help='Таймаут в секундах')
    parser.add_argument('--concurrent', type=int, default=10, help='Количество одновременных проверок')
    parser.add_argument('--test-duration', type=int, default=15, help='Длительность теста каждого потока')
    
    args = parser.parse_args()
    
    # Создаем проверятель
    checker = CurlStreamChecker(
        timeout=args.timeout,
        max_concurrent=args.concurrent,
        test_duration=args.test_duration
    )
    
    print("📡 Загрузка каналов...")
    channels = checker.load_channels_from_m3u(args.m3u_file)
    
    if not channels:
        print("❌ Не удалось загрузить каналы")
        return
    
    print(f"🌐 Начинаем УЛУЧШЕННУЮ проверку {len(channels)} каналов через curl...")
    print(f"⚙️ Настройки: таймаут={args.timeout}с, одновременно={args.concurrent}, тест={args.test_duration}с")
    
    def progress_callback(completed, total, result):
        status = "✅" if result['working'] else "❌"
        quality = result.get('quality_score', 0)
        speed = 0
        if result.get('details'):
            if isinstance(result['details'], dict) and 'detailed' in result['details']:
                speed = result['details']['detailed'].get('speed_download', 0)
            elif isinstance(result['details'], dict):
                speed = result['details'].get('speed_download', 0)
        
        speed_kb = speed / 1024 if speed > 0 else 0
        print(f"[{completed}/{total}] {result['channel_id']}: {result['url'][:50]}... "
              f"{status} (качество: {quality}%, скорость: {speed_kb:.1f}KB/s)")
    
    start_time = time.time()
    results = await checker.check_multiple_streams_curl(channels, args.test_duration, progress_callback)
    duration = time.time() - start_time
    
    print(f"\n🎯 Улучшенная проверка завершена за {duration:.1f} секунд")
    
    # Статистика
    stats = checker.get_statistics()
    print(f"\n📊 СТАТИСТИКА:")
    print(f"  Всего проверено: {stats['total_checked']}")
    print(f"  Работающих: {stats['working']} ({stats['success_rate']}%)")
    print(f"  Среднее время ответа: {stats['avg_response_time']}мс")
    print(f"  Средний балл качества: {stats['avg_quality_score']}")
    print(f"  HLS потоков: {stats['hls_streams']}")
    print(f"  Проблемы со скоростью: {stats['speed_issues']}")
    print(f"  Проблемы с соединением: {stats['connection_issues']}")
    
    # Сохранение отчета
    if args.output:
        checker.save_results(args.output)
    else:
        default_filename = f"curl_stream_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        checker.save_results(default_filename)

if __name__ == "__main__":
    asyncio.run(main())
