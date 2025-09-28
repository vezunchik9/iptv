#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Реальная проверка IPTV потоков через плеер
Тестирует реальное воспроизведение и буферизацию как в IPTV Checker
"""

import asyncio
import subprocess
import json
import time
import re
import threading
import queue
import signal
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealStreamChecker:
    def __init__(self, timeout=30, max_concurrent=5, buffer_test_duration=15):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.buffer_test_duration = buffer_test_duration
        self.results = {}
        self.checking = False
        
        # Проверяем доступность плееров
        self.available_players = self._check_available_players()
        
        logger.info(f"Доступные плееры: {', '.join(self.available_players)}")
        
    def _check_available_players(self):
        """Проверяет доступность различных плееров"""
        players = []
        
        # Проверяем VLC
        try:
            result = subprocess.run(['vlc', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                players.append('vlc')
        except:
            pass
        
        # Проверяем ffplay
        try:
            result = subprocess.run(['ffplay', '-version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                players.append('ffplay')
        except:
            pass
        
        # Проверяем mpv
        try:
            result = subprocess.run(['mpv', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                players.append('mpv')
        except:
            pass
        
        return players
    
    def _check_with_vlc(self, url, test_duration=15):
        """Проверка потока через VLC"""
        try:
            # Команда VLC для тестирования потока
            cmd = [
                'vlc',
                '--intf', 'dummy',  # Не показывать интерфейс
                '--no-video-title-show',
                '--no-audio',
                '--no-video',  # Отключаем видео и аудио для ускорения
                '--play-and-exit',
                '--extraintf', 'logger',
                '--logfile', '/dev/null',
                '--run-time', str(test_duration),
                '--stop-time', str(test_duration),
                url
            ]
            
            start_time = time.time()
            
            # Запускаем VLC с таймаутом
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            try:
                # Ждем завершения или таймаута
                stdout, stderr = process.communicate(timeout=self.timeout)
                
                duration = time.time() - start_time
                
                # Анализируем результат
                if process.returncode == 0:
                    return {
                        'method': 'vlc',
                        'success': True,
                        'working': True,
                        'duration': duration,
                        'buffering_events': 0,  # VLC не предоставляет детальную информацию о буферизации
                        'error': None
                    }
                else:
                    return {
                        'method': 'vlc',
                        'success': False,
                        'working': False,
                        'duration': duration,
                        'buffering_events': 0,
                        'error': f'VLC exit code: {process.returncode}'
                    }
                    
            except subprocess.TimeoutExpired:
                # Прерываем процесс
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    process.wait(timeout=5)
                except:
                    process.kill()
                
                return {
                    'method': 'vlc',
                    'success': False,
                    'working': False,
                    'duration': self.timeout,
                    'buffering_events': 0,
                    'error': 'VLC timeout'
                }
                
        except Exception as e:
            return {
                'method': 'vlc',
                'success': False,
                'working': False,
                'duration': 0,
                'buffering_events': 0,
                'error': str(e)
            }
    
    def _check_with_ffplay(self, url, test_duration=15):
        """Проверка потока через ffplay с анализом буферизации"""
        try:
            # Команда ffplay для тестирования потока
            cmd = [
                'ffplay',
                '-nodisp',  # Не показывать видео
                '-an',      # Отключить аудио
                '-t', str(test_duration),  # Длительность теста
                '-hide_banner',
                '-loglevel', 'info',
                '-stats',   # Показывать статистику
                url
            ]
            
            start_time = time.time()
            buffering_events = 0
            last_position = 0
            position_stalls = 0
            
            # Запускаем ffplay
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            try:
                # Читаем вывод в реальном времени
                while True:
                    line = process.stderr.readline()
                    if not line:
                        break
                    
                    # Анализируем строки статистики ffplay
                    # Пример: frame=  123 fps=25 q=28.0 size=    1024kB time=00:00:05.00 bitrate=1677.7kbits/s
                    if 'time=' in line:
                        # Извлекаем время
                        time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
                        if time_match:
                            current_position = int(time_match.group(1)) * 3600 + int(time_match.group(2)) * 60 + int(time_match.group(3)) + float(time_match.group(4)) / 100
                            
                            # Проверяем на буферизацию (время не меняется)
                            if current_position == last_position:
                                position_stalls += 1
                                if position_stalls >= 3:  # 3 раза подряд без изменения времени = буферизация
                                    buffering_events += 1
                                    position_stalls = 0
                            else:
                                position_stalls = 0
                                last_position = current_position
                    
                    # Проверяем на ошибки
                    if any(keyword in line.lower() for keyword in ['error', 'failed', 'timeout', 'connection refused']):
                        buffering_events += 10  # Большая ошибка
                
                # Ждем завершения процесса
                process.wait(timeout=5)
                duration = time.time() - start_time
                
                # Определяем результат на основе буферизации
                working = buffering_events < 5  # Если меньше 5 событий буферизации - поток рабочий
                
                return {
                    'method': 'ffplay',
                    'success': True,
                    'working': working,
                    'duration': duration,
                    'buffering_events': buffering_events,
                    'error': None if working else f'Too many buffering events: {buffering_events}'
                }
                
            except subprocess.TimeoutExpired:
                # Прерываем процесс
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    process.wait(timeout=5)
                except:
                    process.kill()
                
                return {
                    'method': 'ffplay',
                    'success': False,
                    'working': False,
                    'duration': self.timeout,
                    'buffering_events': 10,
                    'error': 'ffplay timeout'
                }
                
        except Exception as e:
            return {
                'method': 'ffplay',
                'success': False,
                'working': False,
                'duration': 0,
                'buffering_events': 0,
                'error': str(e)
            }
    
    def _check_with_mpv(self, url, test_duration=15):
        """Проверка потока через mpv"""
        try:
            # Команда mpv для тестирования потока
            cmd = [
                'mpv',
                '--no-video',      # Отключить видео
                '--no-audio',      # Отключить аудио
                '--length=' + str(test_duration),  # Длительность теста
                '--no-terminal',
                '--really-quiet',
                '--no-config',
                '--no-input-default-bindings',
                '--no-input-vo-keyboard',
                url
            ]
            
            start_time = time.time()
            
            # Запускаем mpv
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            try:
                stdout, stderr = process.communicate(timeout=self.timeout)
                duration = time.time() - start_time
                
                # Анализируем результат
                if process.returncode == 0:
                    return {
                        'method': 'mpv',
                        'success': True,
                        'working': True,
                        'duration': duration,
                        'buffering_events': 0,
                        'error': None
                    }
                else:
                    return {
                        'method': 'mpv',
                        'success': False,
                        'working': False,
                        'duration': duration,
                        'buffering_events': 0,
                        'error': f'mpv exit code: {process.returncode}'
                    }
                    
            except subprocess.TimeoutExpired:
                # Прерываем процесс
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    process.wait(timeout=5)
                except:
                    process.kill()
                
                return {
                    'method': 'mpv',
                    'success': False,
                    'working': False,
                    'duration': self.timeout,
                    'buffering_events': 0,
                    'error': 'mpv timeout'
                }
                
        except Exception as e:
            return {
                'method': 'mpv',
                'success': False,
                'working': False,
                'duration': 0,
                'buffering_events': 0,
                'error': str(e)
            }
    
    def _check_with_curl_stream(self, url, test_duration=15):
        """Проверка потока через curl с анализом скорости"""
        try:
            # Команда curl для тестирования потока
            cmd = [
                'curl',
                '-s',                    # Тихий режим
                '--max-time', str(test_duration),
                '--connect-timeout', '10',
                '--retry', '1',
                '--retry-delay', '1',
                '--user-agent', 'VLC/3.0.0 LibVLC/3.0.0',
                '--location',            # Следуем редиректам
                '--fail-with-body',
                '--write-out', '%{http_code}:%{time_total}:%{speed_download}',
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
                    parts = result.stdout.strip().split(':')
                    if len(parts) >= 3:
                        http_code = int(parts[0])
                        time_total = float(parts[1])
                        speed_download = float(parts[2]) if parts[2] != '0' else 0
                        
                        # Определяем работоспособность на основе HTTP кода и скорости
                        working = (http_code == 200 and speed_download > 1000)  # Минимум 1KB/s
                        
                        return {
                            'method': 'curl_stream',
                            'success': True,
                            'working': working,
                            'duration': duration,
                            'buffering_events': 0 if working else 1,
                            'http_code': http_code,
                            'speed_download': speed_download,
                            'error': None if working else f'Low speed: {speed_download} bytes/s'
                        }
                except (ValueError, IndexError):
                    pass
            
            return {
                'method': 'curl_stream',
                'success': False,
                'working': False,
                'duration': duration,
                'buffering_events': 1,
                'error': result.stderr.strip() if result.stderr else 'curl failed'
            }
            
        except Exception as e:
            return {
                'method': 'curl_stream',
                'success': False,
                'working': False,
                'duration': 0,
                'buffering_events': 0,
                'error': str(e)
            }
    
    def check_single_stream_real(self, channel_id, url, player=None, test_duration=None):
        """Реальная проверка одного потока через плеер"""
        if test_duration is None:
            test_duration = self.buffer_test_duration
            
        start_time = time.time()
        
        result = {
            'channel_id': channel_id,
            'url': url,
            'checked_at': datetime.now().isoformat(),
            'response_time': None,
            'working': False,
            'details': None,
            'error': None,
            'test_duration': test_duration,
            'player_used': None
        }
        
        try:
            # Выбираем плеер для тестирования
            if player and player in self.available_players:
                players_to_test = [player]
            else:
                players_to_test = self.available_players
            
            if not players_to_test:
                result['error'] = 'No players available'
                result['response_time'] = round((time.time() - start_time) * 1000, 2)
                return result
            
            best_result = None
            
            # Тестируем каждый доступный плеер
            for player_name in players_to_test:
                logger.debug(f"Тестируем {url} через {player_name}")
                
                if player_name == 'vlc':
                    player_result = self._check_with_vlc(url, test_duration)
                elif player_name == 'ffplay':
                    player_result = self._check_with_ffplay(url, test_duration)
                elif player_name == 'mpv':
                    player_result = self._check_with_mpv(url, test_duration)
                else:
                    continue
                
                # Сохраняем лучший результат
                if best_result is None or player_result.get('working', False):
                    best_result = player_result
                    result['player_used'] = player_name
                
                # Если нашли рабочий поток, прерываем тестирование
                if player_result.get('working', False):
                    break
            
            # Если ни один плеер не сработал, пробуем curl
            if not best_result or not best_result.get('working', False):
                curl_result = self._check_with_curl_stream(url, test_duration)
                if curl_result.get('working', False):
                    best_result = curl_result
                    result['player_used'] = 'curl'
            
            # Устанавливаем результат
            if best_result:
                result['working'] = best_result.get('working', False)
                result['details'] = best_result
                result['error'] = best_result.get('error')
            else:
                result['error'] = 'All players failed'
            
            result['response_time'] = round((time.time() - start_time) * 1000, 2)
            
        except Exception as e:
            result['error'] = str(e)
            result['response_time'] = round((time.time() - start_time) * 1000, 2)
        
        return result
    
    async def check_multiple_streams_real(self, channels, player=None, test_duration=None, progress_callback=None):
        """Реальная проверка нескольких потоков параллельно"""
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
                        self.check_single_stream_real,
                        channel['id'],
                        channel['url'],
                        player,
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
        
        # Статистика по плеерам
        player_stats = {}
        for result in self.results.values():
            player = result.get('player_used', 'unknown')
            if player not in player_stats:
                player_stats[player] = {'total': 0, 'working': 0}
            
            player_stats[player]['total'] += 1
            if result['working']:
                player_stats[player]['working'] += 1
        
        # Статистика по буферизации
        buffering_stats = []
        for result in self.results.values():
            details = result.get('details', {})
            if details and 'buffering_events' in details:
                buffering_stats.append(details['buffering_events'])
        
        avg_buffering = sum(buffering_stats) / len(buffering_stats) if buffering_stats else 0
        
        # Вычисляем среднее время ответа
        response_times = [r['response_time'] for r in self.results.values() 
                         if r['response_time'] is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'total_checked': total,
            'working': working,
            'success_rate': round((working / total) * 100, 2) if total > 0 else 0,
            'avg_response_time': round(avg_response_time, 2),
            'avg_buffering_events': round(avg_buffering, 2),
            'player_statistics': player_stats,
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
            
            logger.info(f"Загружено {len(channels)} каналов для реальной проверки")
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
                'checker_version': '3.0_real',
                'settings': {
                    'timeout': self.timeout,
                    'max_concurrent': self.max_concurrent,
                    'buffer_test_duration': self.buffer_test_duration,
                    'available_players': self.available_players
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
    
    parser = argparse.ArgumentParser(description='Реальная проверка IPTV потоков через плеер')
    parser.add_argument('m3u_file', help='Путь к M3U файлу')
    parser.add_argument('--output', '-o', help='Файл для сохранения отчета')
    parser.add_argument('--timeout', type=int, default=30, help='Таймаут в секундах')
    parser.add_argument('--concurrent', type=int, default=5, help='Количество одновременных проверок')
    parser.add_argument('--test-duration', type=int, default=15, help='Длительность теста каждого потока')
    parser.add_argument('--player', choices=['vlc', 'ffplay', 'mpv'], help='Конкретный плеер для тестирования')
    
    args = parser.parse_args()
    
    # Создаем проверятель
    checker = RealStreamChecker(
        timeout=args.timeout,
        max_concurrent=args.concurrent,
        buffer_test_duration=args.test_duration
    )
    
    if not checker.available_players:
        print("❌ Не найдено ни одного доступного плеера (VLC, ffplay, mpv)")
        print("Установите хотя бы один из них:")
        print("  macOS: brew install vlc ffmpeg mpv")
        print("  Ubuntu: sudo apt install vlc ffmpeg mpv")
        return
    
    print("📡 Загрузка каналов...")
    channels = checker.load_channels_from_m3u(args.m3u_file)
    
    if not channels:
        print("❌ Не удалось загрузить каналы")
        return
    
    print(f"🎬 Начинаем РЕАЛЬНУЮ проверку {len(channels)} каналов...")
    print(f"⚙️ Настройки: таймаут={args.timeout}с, одновременно={args.concurrent}, тест={args.test_duration}с")
    print(f"🎮 Плееры: {', '.join(checker.available_players)}")
    
    def progress_callback(completed, total, result):
        status = "✅" if result['working'] else "❌"
        player = result.get('player_used', 'unknown')
        buffering = result.get('details', {}).get('buffering_events', 0)
        print(f"[{completed}/{total}] {result['channel_id']}: {result['url'][:50]}... "
              f"{status} ({result['response_time']}мс, {player}, буферизация: {buffering})")
    
    start_time = time.time()
    results = await checker.check_multiple_streams_real(
        channels, 
        args.player, 
        args.test_duration, 
        progress_callback
    )
    duration = time.time() - start_time
    
    print(f"\n🎯 Реальная проверка завершена за {duration:.1f} секунд")
    
    # Статистика
    stats = checker.get_statistics()
    print(f"\n📊 СТАТИСТИКА:")
    print(f"  Всего проверено: {stats['total_checked']}")
    print(f"  Работающих: {stats['working']} ({stats['success_rate']}%)")
    print(f"  Среднее время ответа: {stats['avg_response_time']}мс")
    print(f"  Средние события буферизации: {stats['avg_buffering_events']}")
    
    # Статистика по плеерам
    if 'player_statistics' in stats:
        print(f"\n🎮 СТАТИСТИКА ПО ПЛЕЕРАМ:")
        for player, player_stats in stats['player_statistics'].items():
            total = player_stats.get('total', 0)
            working = player_stats.get('working', 0)
            rate = (working / total * 100) if total > 0 else 0
            print(f"  {player}: {working}/{total} ({rate:.1f}%)")
    
    # Сохранение отчета
    if args.output:
        checker.save_results(args.output)
    else:
        default_filename = f"real_stream_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        checker.save_results(default_filename)

if __name__ == "__main__":
    asyncio.run(main())
