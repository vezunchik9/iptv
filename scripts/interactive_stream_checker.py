#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интерактивная проверка IPTV потоков с визуальной обратной связью
Показывает реальный процесс проверки и может открывать плеер для демонстрации
"""

import asyncio
import subprocess
import json
import time
import re
import os
import signal
from datetime import datetime
from urllib.parse import urlparse
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InteractiveStreamChecker:
    def __init__(self, visual_mode=False, test_duration=10, show_player=False):
        self.visual_mode = visual_mode
        self.test_duration = test_duration
        self.show_player = show_player
        self.results = {}
        
        # Проверяем доступность инструментов
        self.available_tools = self._check_available_tools()
        print(f"🔧 Доступные инструменты: {', '.join(self.available_tools)}")
        
    def _check_available_tools(self):
        """Проверяет доступность различных инструментов"""
        tools = []
        
        # Проверяем VLC
        vlc_paths = [
            '/Applications/VLC.app/Contents/MacOS/VLC',  # Mac
            '/usr/local/bin/vlc',                        # Linux/Mac with symlink
            'vlc'                                        # PATH
        ]
        
        for vlc_path in vlc_paths:
            try:
                result = subprocess.run([vlc_path, '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    tools.append(f'vlc ({vlc_path})')
                    self.vlc_path = vlc_path
                    break
            except:
                continue
        
        # Проверяем curl
        try:
            result = subprocess.run(['curl', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                tools.append('curl')
        except:
            pass
        
        # Проверяем ffprobe
        try:
            result = subprocess.run(['ffprobe', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                tools.append('ffprobe')
        except:
            pass
        
        return tools
    
    def _print_separator(self, title=""):
        """Печатает красивый разделитель"""
        width = 80
        if title:
            title = f" {title} "
            padding = (width - len(title)) // 2
            print("=" * padding + title + "=" * (width - padding - len(title)))
        else:
            print("=" * width)
    
    def _print_status(self, message, status="INFO"):
        """Печатает сообщение с цветным статусом"""
        colors = {
            "INFO": "\033[94m",      # Синий
            "SUCCESS": "\033[92m",   # Зеленый
            "WARNING": "\033[93m",   # Желтый
            "ERROR": "\033[91m",     # Красный
            "RESET": "\033[0m"       # Сброс
        }
        
        color = colors.get(status, colors["INFO"])
        reset = colors["RESET"]
        
        icons = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }
        
        icon = icons.get(status, "ℹ️")
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"{color}[{timestamp}] {icon} {message}{reset}")
    
    def _test_with_vlc_visual(self, url, channel_name="Unknown", test_duration=10):
        """Тестирует поток через VLC с визуальным отображением"""
        if not hasattr(self, 'vlc_path'):
            return {
                'method': 'vlc_visual',
                'success': False,
                'working': False,
                'error': 'VLC not found'
            }
        
        self._print_status(f"Тестируем канал: {channel_name}")
        self._print_status(f"URL: {url[:60]}...")
        
        try:
            if self.show_player:
                # Запускаем VLC с интерфейсом для демонстрации
                self._print_status("Открываем VLC плеер для демонстрации...", "INFO")
                cmd = [
                    self.vlc_path,
                    '--play-and-exit',
                    '--stop-time', str(test_duration),
                    url
                ]
            else:
                # Запускаем VLC в фоновом режиме
                self._print_status("Тестируем поток в фоновом режиме...", "INFO")
                cmd = [
                    self.vlc_path,
                    '--intf', 'dummy',
                    '--no-video-title-show',
                    '--play-and-exit',
                    '--stop-time', str(test_duration),
                    '--extraintf', 'logger',
                    '--logfile', '/tmp/vlc_test.log',
                    url
                ]
            
            start_time = time.time()
            
            # Показываем прогресс
            print(f"⏳ Тестирование ({test_duration}с): ", end="", flush=True)
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            # Показываем прогресс-бар
            for i in range(test_duration):
                if process.poll() is not None:
                    break
                print("█", end="", flush=True)
                time.sleep(1)
            
            print()  # Новая строка после прогресс-бара
            
            # Завершаем процесс если он еще работает
            if process.poll() is None:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    process.wait(timeout=3)
                except:
                    process.kill()
            
            duration = time.time() - start_time
            
            # Анализируем результат
            if process.returncode == 0 or (process.returncode == -15):  # SIGTERM это нормально
                self._print_status(f"Поток работает! Тест завершен за {duration:.1f}с", "SUCCESS")
                working = True
                error = None
            else:
                self._print_status(f"Поток не работает (код: {process.returncode})", "ERROR")
                working = False
                error = f"VLC exit code: {process.returncode}"
            
            return {
                'method': 'vlc_visual',
                'success': True,
                'working': working,
                'duration': duration,
                'exit_code': process.returncode,
                'error': error
            }
            
        except Exception as e:
            self._print_status(f"Ошибка при тестировании: {str(e)}", "ERROR")
            return {
                'method': 'vlc_visual',
                'success': False,
                'working': False,
                'duration': 0,
                'error': str(e)
            }
    
    def _test_with_curl_visual(self, url, channel_name="Unknown", test_duration=10):
        """Тестирует поток через curl с визуальным отображением"""
        self._print_status(f"Тестируем канал через curl: {channel_name}")
        self._print_status(f"URL: {url[:60]}...")
        
        try:
            # Сначала быстрая проверка доступности
            self._print_status("Проверяем доступность...", "INFO")
            
            quick_cmd = [
                'curl',
                '-s', '-I',  # HEAD запрос
                '--max-time', '5',
                '--connect-timeout', '3',
                '--user-agent', 'VLC/3.0.0 LibVLC/3.0.0',
                '--location',
                url
            ]
            
            result = subprocess.run(quick_cmd, capture_output=True, text=True, timeout=8)
            
            if result.returncode != 0:
                self._print_status("Поток недоступен (не отвечает на HEAD запрос)", "ERROR")
                return {
                    'method': 'curl_visual',
                    'success': False,
                    'working': False,
                    'error': 'HEAD request failed'
                }
            
            # Анализируем заголовки
            headers = result.stdout
            status_line = headers.split('\n')[0] if headers else ""
            
            if '200 OK' in status_line:
                self._print_status("Поток доступен (200 OK)", "SUCCESS")
            elif any(code in status_line for code in ['301', '302', '307', '308']):
                self._print_status(f"Поток доступен с редиректом: {status_line.strip()}", "WARNING")
            else:
                self._print_status(f"Неожиданный ответ: {status_line.strip()}", "ERROR")
                return {
                    'method': 'curl_visual',
                    'success': False,
                    'working': False,
                    'error': f'Unexpected response: {status_line.strip()}'
                }
            
            # Теперь тестируем скачивание данных
            self._print_status(f"Тестируем загрузку данных ({test_duration}с)...", "INFO")
            
            download_cmd = [
                'curl',
                '-s',
                '--max-time', str(test_duration),
                '--connect-timeout', '5',
                '--user-agent', 'VLC/3.0.0 LibVLC/3.0.0',
                '--location',
                '--write-out', 'SPEED:%{speed_download}|SIZE:%{size_download}|TIME:%{time_total}',
                '--output', '/dev/null',
                url
            ]
            
            start_time = time.time()
            
            # Показываем прогресс
            print(f"⏳ Загрузка ({test_duration}с): ", end="", flush=True)
            
            result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=test_duration + 5)
            
            duration = time.time() - start_time
            print("█" * min(test_duration, 20))  # Завершаем прогресс-бар
            
            if result.returncode == 0 and result.stdout:
                # Парсим результат
                info = {}
                for part in result.stdout.strip().split('|'):
                    if ':' in part:
                        key, value = part.split(':', 1)
                        try:
                            info[key] = float(value)
                        except ValueError:
                            info[key] = value
                
                speed = info.get('SPEED', 0)
                size = info.get('SIZE', 0)
                
                speed_kb = speed / 1024 if speed > 0 else 0
                size_mb = size / (1024 * 1024) if size > 0 else 0
                
                if speed > 10000:  # > 10KB/s
                    self._print_status(f"Поток работает! Скорость: {speed_kb:.1f} KB/s, загружено: {size_mb:.2f} MB", "SUCCESS")
                    working = True
                    error = None
                else:
                    self._print_status(f"Поток медленный: {speed_kb:.1f} KB/s", "WARNING")
                    working = False
                    error = f"Low speed: {speed_kb:.1f} KB/s"
                
                return {
                    'method': 'curl_visual',
                    'success': True,
                    'working': working,
                    'duration': duration,
                    'speed_download': speed,
                    'size_download': size,
                    'error': error
                }
            else:
                self._print_status("Не удалось загрузить данные", "ERROR")
                return {
                    'method': 'curl_visual',
                    'success': False,
                    'working': False,
                    'duration': duration,
                    'error': 'Download failed'
                }
                
        except Exception as e:
            self._print_status(f"Ошибка при тестировании: {str(e)}", "ERROR")
            return {
                'method': 'curl_visual',
                'success': False,
                'working': False,
                'duration': 0,
                'error': str(e)
            }
    
    def check_single_stream_interactive(self, channel_id, channel_name, url):
        """Интерактивная проверка одного потока"""
        self._print_separator(f"КАНАЛ #{channel_id}: {channel_name}")
        
        start_time = time.time()
        
        result = {
            'channel_id': channel_id,
            'channel_name': channel_name,
            'url': url,
            'checked_at': datetime.now().isoformat(),
            'working': False,
            'details': None,
            'error': None
        }
        
        # Выбираем метод тестирования
        if hasattr(self, 'vlc_path') and 'vlc' in ' '.join(self.available_tools):
            self._print_status("Используем VLC для тестирования", "INFO")
            test_result = self._test_with_vlc_visual(url, channel_name, self.test_duration)
        else:
            self._print_status("Используем curl для тестирования", "INFO")
            test_result = self._test_with_curl_visual(url, channel_name, self.test_duration)
        
        result['working'] = test_result.get('working', False)
        result['details'] = test_result
        result['error'] = test_result.get('error')
        result['response_time'] = round((time.time() - start_time) * 1000, 2)
        
        # Итоговый результат
        if result['working']:
            self._print_status(f"✅ РЕЗУЛЬТАТ: Канал РАБОТАЕТ ({result['response_time']}мс)", "SUCCESS")
        else:
            self._print_status(f"❌ РЕЗУЛЬТАТ: Канал НЕ РАБОТАЕТ ({result['response_time']}мс)", "ERROR")
            if result['error']:
                self._print_status(f"Причина: {result['error']}", "WARNING")
        
        print()  # Пустая строка для разделения
        
        return result
    
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
            
            return channels
            
        except Exception as e:
            self._print_status(f"Ошибка при загрузке M3U: {e}", "ERROR")
            return []
    
    def check_channels_interactive(self, channels, max_channels=None):
        """Интерактивная проверка каналов"""
        if max_channels:
            channels = channels[:max_channels]
        
        self._print_separator("НАЧИНАЕМ ИНТЕРАКТИВНУЮ ПРОВЕРКУ")
        self._print_status(f"Будет проверено каналов: {len(channels)}")
        self._print_status(f"Длительность теста каждого: {self.test_duration}с")
        self._print_status(f"Показывать плеер: {'Да' if self.show_player else 'Нет'}")
        
        input("\n🎬 Нажмите Enter чтобы начать проверку...")
        
        results = {}
        working_count = 0
        
        for i, channel in enumerate(channels):
            self._print_status(f"Прогресс: {i+1}/{len(channels)}", "INFO")
            
            result = self.check_single_stream_interactive(
                channel['id'], 
                channel['name'], 
                channel['url']
            )
            
            results[channel['id']] = result
            
            if result['working']:
                working_count += 1
            
            # Пауза между проверками (кроме последней)
            if i < len(channels) - 1:
                if self.visual_mode:
                    input("Нажмите Enter для следующего канала...")
                else:
                    time.sleep(1)
        
        self._print_separator("ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
        self._print_status(f"Всего проверено: {len(channels)}")
        self._print_status(f"Работающих каналов: {working_count}")
        self._print_status(f"Процент успеха: {(working_count / len(channels) * 100):.1f}%")
        
        return results

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Интерактивная проверка IPTV потоков')
    parser.add_argument('m3u_file', help='Путь к M3U файлу')
    parser.add_argument('--visual', action='store_true', help='Визуальный режим с паузами')
    parser.add_argument('--show-player', action='store_true', help='Показывать плеер при тестировании')
    parser.add_argument('--test-duration', type=int, default=10, help='Длительность теста каждого потока')
    parser.add_argument('--max-channels', type=int, help='Максимум каналов для проверки')
    
    args = parser.parse_args()
    
    # Создаем проверятель
    checker = InteractiveStreamChecker(
        visual_mode=args.visual,
        test_duration=args.test_duration,
        show_player=args.show_player
    )
    
    print("🎬 ИНТЕРАКТИВНАЯ ПРОВЕРКА IPTV ПОТОКОВ")
    print("=" * 50)
    
    # Загружаем каналы
    channels = checker.load_channels_from_m3u(args.m3u_file)
    
    if not channels:
        print("❌ Не удалось загрузить каналы")
        return
    
    # Запускаем проверку
    results = checker.check_channels_interactive(channels, args.max_channels)
    
    # Сохраняем результаты
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"interactive_check_report_{timestamp}.json"
    
    report = {
        'results': results,
        'settings': {
            'visual_mode': args.visual,
            'show_player': args.show_player,
            'test_duration': args.test_duration
        },
        'generated_at': datetime.now().isoformat()
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 Отчет сохранен: {filename}")

if __name__ == "__main__":
    main()
