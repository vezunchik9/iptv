#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Реальная проверка видеопотоков IPTV с удалением нерабочих каналов
Тестирует реальное воспроизведение видео, а не просто HTTP доступность
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
import tempfile
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealVideoChecker:
    def __init__(self, timeout=30, max_concurrent=3, test_duration=10, buffer_threshold=3):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.test_duration = test_duration
        self.buffer_threshold = buffer_threshold  # Сколько буферизаций считать критичным
        self.results = {}
        self.checking = False
        
        # Проверяем доступность инструментов
        self.available_tools = self._check_available_tools()
        logger.info(f"Доступные инструменты: {', '.join(self.available_tools)}")
        
        if not self.available_tools:
            logger.error("Не найдено ни одного инструмента для проверки видео!")
            raise RuntimeError("Установите ffmpeg, vlc, или mpv для проверки видеопотоков")
    
    def _check_available_tools(self):
        """Проверяет доступность инструментов для проверки видео"""
        tools = []
        
        # Проверяем ffmpeg/ffprobe
        try:
            subprocess.run(['ffprobe', '-version'], capture_output=True, timeout=5)
            tools.append('ffprobe')
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Проверяем VLC
        try:
            subprocess.run(['vlc', '--version'], capture_output=True, timeout=5)
            tools.append('vlc')
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Проверяем mpv
        try:
            subprocess.run(['mpv', '--version'], capture_output=True, timeout=5)
            tools.append('mpv')
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Проверяем curl (для HLS анализа)
        try:
            subprocess.run(['curl', '--version'], capture_output=True, timeout=5)
            tools.append('curl')
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return tools
    
    async def check_video_stream_real(self, url):
        """Реальная проверка видеопотока"""
        logger.info(f"🎬 Проверяем видеопоток: {url}")
        
        # Пробуем разные методы в порядке надежности
        methods = []
        
        # Сначала curl - он лучше обнаруживает заглушки
        if 'curl' in self.available_tools:
            methods.append(self._check_with_curl_video)
        if 'ffprobe' in self.available_tools:
            methods.append(self._check_with_ffprobe)
        if 'vlc' in self.available_tools:
            methods.append(self._check_with_vlc)
        if 'mpv' in self.available_tools:
            methods.append(self._check_with_mpv)
        
        for method in methods:
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, method, url
                )
                
                if result['success']:
                    logger.info(f"✅ Поток работает: {url} (метод: {result['method']})")
                    return result
                else:
                    logger.debug(f"❌ Метод {result['method']} не подтвердил работоспособность: {result.get('error')}")
                    
            except Exception as e:
                logger.debug(f"Ошибка в методе {method.__name__}: {e}")
                continue
        
        logger.warning(f"❌ Поток не работает: {url}")
        return {
            'success': False,
            'working': False,
            'method': 'all_failed',
            'error': 'Все методы проверки не смогли подтвердить работоспособность потока',
            'details': {}
        }
    
    def _check_with_ffprobe(self, url):
        """Проверка через ffprobe - самый надежный метод"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                '-analyzeduration', '3000000',  # 3 секунды анализа
                '-probesize', '1000000',       # 1MB для анализа
                '-timeout', str(self.timeout * 1000000),  # в микросекундах
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
            
            if result.returncode == 0:
                try:
                    probe_data = json.loads(result.stdout)
                    
                    # Проверяем наличие видео потоков
                    video_streams = [s for s in probe_data.get('streams', []) if s.get('codec_type') == 'video']
                    audio_streams = [s for s in probe_data.get('streams', []) if s.get('codec_type') == 'audio']
                    
                    # Анализируем метаданные на предмет информационных сообщений
                    format_tags = probe_data.get('format', {}).get('tags', {})
                    stream_tags = {}
                    for stream in video_streams + audio_streams:
                        stream_tags.update(stream.get('tags', {}))
                    
                    # Объединяем все теги для анализа
                    all_tags = {**format_tags, **stream_tags}
                    tag_text = ' '.join(str(v).lower() for v in all_tags.values())
                    
                    # Паттерны для информационных сообщений
                    info_patterns = [
                        r'обратитесь к поставщику',
                        r'contact.*provider',
                        r'subscription.*required',
                        r'premium.*required',
                        r'доступ.*запрещен',
                        r'access.*denied',
                        r'channel.*unavailable',
                        r'канал.*недоступен',
                        r'personal.*account',
                        r'личный.*кабинет',
                        r'уважаемый.*пользователь',
                        r'dear.*user',
                        r'для.*просмотра.*данного.*канала',
                        r'to.*view.*this.*channel',
                        r'вам.*необходимо',
                        r'you.*need.*to',
                        r'в.*личном.*кабинете',
                        r'in.*your.*personal.*account',
                        r'узнать.*дополнительную',
                        r'find.*out.*additional',
                        r'информацию',
                        r'information',
                        r'пожалуйста.*обратитесь',
                        r'please.*contact',
                        r'подписка.*истекла',
                        r'subscription.*expired',
                        r'требуется.*подписка',
                        r'subscription.*required',
                        r'канал.*заблокирован',
                        r'channel.*blocked',
                        r'недоступен.*в.*вашем.*регионе',
                        r'unavailable.*in.*your.*region'
                    ]
                    
                    # Проверяем на информационные сообщения
                    info_message_count = 0
                    for pattern in info_patterns:
                        info_message_count += len(re.findall(pattern, tag_text, re.IGNORECASE))
                    
                    if info_message_count > 0:
                        return {
                            'success': False,
                            'working': False,
                            'method': 'ffprobe',
                            'duration': duration,
                            'error': f'Обнаружено информационное сообщение в метаданных (сообщений: {info_message_count})',
                            'details': {'info_messages': info_message_count, 'tags_analyzed': len(all_tags)}
                        }
                    
                    if video_streams:
                        video_info = video_streams[0]
                        return {
                            'success': True,
                            'working': True,
                            'method': 'ffprobe',
                            'duration': duration,
                            'details': {
                                'video_codec': video_info.get('codec_name'),
                                'resolution': f"{video_info.get('width')}x{video_info.get('height')}",
                                'fps': video_info.get('r_frame_rate'),
                                'bitrate': probe_data.get('format', {}).get('bit_rate'),
                                'has_audio': len(audio_streams) > 0,
                                'format': probe_data.get('format', {}).get('format_name'),
                                'info_messages': 0
                            },
                            'error': None
                        }
                    else:
                        return {
                            'success': False,
                            'working': False,
                            'method': 'ffprobe',
                            'duration': duration,
                            'error': 'Не найдены видеопотоки в стриме'
                        }
                        
                except json.JSONDecodeError:
                    return {
                        'success': False,
                        'working': False,
                        'method': 'ffprobe',
                        'duration': duration,
                        'error': 'Не удалось распарсить ответ ffprobe'
                    }
            else:
                error_msg = result.stderr.strip() if result.stderr else 'Unknown error'
                return {
                    'success': False,
                    'working': False,
                    'method': 'ffprobe',
                    'duration': duration,
                    'error': f'ffprobe error: {error_msg}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'working': False,
                'method': 'ffprobe',
                'duration': self.timeout,
                'error': 'Таймаут при проверке потока'
            }
        except Exception as e:
            return {
                'success': False,
                'working': False,
                'method': 'ffprobe',
                'duration': 0,
                'error': str(e)
            }
    
    def _check_with_vlc(self, url):
        """Проверка через VLC с анализом буферизации и содержимого"""
        try:
            # Создаем временный файл для логов VLC
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.log', delete=False) as log_file:
                log_path = log_file.name
            
            cmd = [
                'vlc',
                '--intf', 'dummy',           # Без интерфейса
                '--quiet',                   # Тихий режим
                '--run-time', str(self.test_duration),  # Время воспроизведения
                '--stop-time', str(self.test_duration),
                '--no-video',               # Без видеовывода
                '--no-audio',               # Без аудиовывода
                '--logfile', log_path,      # Файл логов
                '--verbose', '2',           # Уровень логирования
                url,
                'vlc://quit'                # Автовыход
            ]
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            duration = time.time() - start_time
            
            # Анализируем логи VLC
            buffer_count = 0
            error_count = 0
            info_message_count = 0
            
            try:
                with open(log_path, 'r') as f:
                    log_content = f.read()
                
                # Ищем признаки буферизации и ошибок
                buffer_patterns = [
                    r'buffering',
                    r'cache',
                    r'stalled',
                    r'waiting for data',
                    r'prebuffering'
                ]
                
                error_patterns = [
                    r'error',
                    r'failed',
                    r'cannot',
                    r'unable to',
                    r'connection refused'
                ]
                
                # Паттерны для информационных сообщений (не рабочие каналы)
                info_message_patterns = [
                    r'обратитесь к поставщику',
                    r'contact.*provider',
                    r'subscription.*required',
                    r'premium.*required',
                    r'доступ.*запрещен',
                    r'access.*denied',
                    r'channel.*unavailable',
                    r'канал.*недоступен',
                    r'personal.*account',
                    r'личный.*кабинет',
                    r'дополнительную.*информацию',
                    r'additional.*information',
                    r'уважаемый.*пользователь',
                    r'dear.*user',
                    r'для.*просмотра.*данного.*канала',
                    r'to.*view.*this.*channel',
                    r'вам.*необходимо',
                    r'you.*need.*to',
                    r'в.*личном.*кабинете',
                    r'in.*your.*personal.*account',
                    r'узнать.*дополнительную',
                    r'find.*out.*additional',
                    r'информацию',
                    r'information',
                    r'пожалуйста.*обратитесь',
                    r'please.*contact',
                    r'подписка.*истекла',
                    r'subscription.*expired',
                    r'требуется.*подписка',
                    r'subscription.*required',
                    r'канал.*заблокирован',
                    r'channel.*blocked',
                    r'недоступен.*в.*вашем.*регионе',
                    r'unavailable.*in.*your.*region'
                ]
                
                for pattern in buffer_patterns:
                    buffer_count += len(re.findall(pattern, log_content, re.IGNORECASE))
                
                for pattern in error_patterns:
                    error_count += len(re.findall(pattern, log_content, re.IGNORECASE))
                
                # Ищем информационные сообщения
                for pattern in info_message_patterns:
                    info_message_count += len(re.findall(pattern, log_content, re.IGNORECASE))
                
                # Удаляем временный файл
                os.unlink(log_path)
                
            except Exception as e:
                logger.debug(f"Ошибка при чтении логов VLC: {e}")
            
            # Определяем результат
            if error_count > 0:
                return {
                    'success': False,
                    'working': False,
                    'method': 'vlc',
                    'duration': duration,
                    'error': f'Обнаружены ошибки в потоке (ошибок: {error_count})',
                    'details': {'buffer_count': buffer_count, 'error_count': error_count, 'info_messages': info_message_count}
                }
            elif info_message_count > 0:
                return {
                    'success': False,
                    'working': False,
                    'method': 'vlc',
                    'duration': duration,
                    'error': f'Обнаружено информационное сообщение вместо контента (сообщений: {info_message_count})',
                    'details': {'buffer_count': buffer_count, 'error_count': error_count, 'info_messages': info_message_count}
                }
            elif buffer_count >= self.buffer_threshold:
                return {
                    'success': False,
                    'working': False,
                    'method': 'vlc',
                    'duration': duration,
                    'error': f'Слишком много буферизации (буферизаций: {buffer_count})',
                    'details': {'buffer_count': buffer_count, 'error_count': error_count, 'info_messages': info_message_count}
                }
            elif duration < 2:  # Если VLC завершился слишком быстро, это подозрительно
                return {
                    'success': False,
                    'working': False,
                    'method': 'vlc',
                    'duration': duration,
                    'error': f'VLC завершился слишком быстро (длительность: {duration:.2f}с) - возможная заглушка',
                    'details': {'buffer_count': buffer_count, 'error_count': error_count, 'info_messages': info_message_count}
                }
            else:
                return {
                    'success': True,
                    'working': True,
                    'method': 'vlc',
                    'duration': duration,
                    'details': {'buffer_count': buffer_count, 'error_count': error_count, 'info_messages': info_message_count},
                    'error': None
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'working': False,
                'method': 'vlc',
                'duration': self.timeout,
                'error': 'Таймаут при проверке через VLC'
            }
        except Exception as e:
            return {
                'success': False,
                'working': False,
                'method': 'vlc',
                'duration': 0,
                'error': str(e)
            }
    
    def _check_with_mpv(self, url):
        """Проверка через mpv"""
        try:
            cmd = [
                'mpv',
                '--no-video',               # Без видеовывода
                '--no-audio',               # Без аудиовывода
                '--length', str(self.test_duration),  # Время воспроизведения
                '--quiet',                  # Тихий режим
                '--really-quiet',           # Очень тихий режим
                '--msg-level=all=info',     # Уровень сообщений
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
            
            # mpv возвращает 0 при успешном воспроизведении
            if result.returncode == 0:
                return {
                    'success': True,
                    'working': True,
                    'method': 'mpv',
                    'duration': duration,
                    'details': {},
                    'error': None
                }
            else:
                error_msg = result.stderr.strip() if result.stderr else 'Unknown mpv error'
                return {
                    'success': False,
                    'working': False,
                    'method': 'mpv',
                    'duration': duration,
                    'error': f'mpv error: {error_msg}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'working': False,
                'method': 'mpv',
                'duration': self.timeout,
                'error': 'Таймаут при проверке через mpv'
            }
        except Exception as e:
            return {
                'success': False,
                'working': False,
                'method': 'mpv',
                'duration': 0,
                'error': str(e)
            }
    
    def _check_with_curl_video(self, url):
        """Проверка через curl с анализом видеоданных"""
        try:
            parsed_url = urlparse(url)
            is_hls = parsed_url.path.endswith('.m3u8') or 'm3u8' in parsed_url.query
            
            if is_hls:
                return self._check_hls_with_curl(url)
            else:
                return self._check_direct_stream_with_curl(url)
                
        except Exception as e:
            return {
                'success': False,
                'working': False,
                'method': 'curl',
                'duration': 0,
                'error': str(e)
            }
    
    def _check_hls_with_curl(self, url):
        """Проверка HLS потока через curl"""
        try:
            # Сначала загружаем плейлист
            cmd_playlist = [
                'curl', '-s', '-L', '--max-time', '10',
                '--user-agent', 'VLC/3.0.0 LibVLC/3.0.0',
                url
            ]
            
            start_time = time.time()
            result = subprocess.run(cmd_playlist, capture_output=True, text=True, timeout=15)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'working': False,
                    'method': 'curl_hls',
                    'duration': time.time() - start_time,
                    'error': 'Не удалось загрузить HLS плейлист'
                }
            
            playlist_content = result.stdout
            
            # Проверяем содержимое плейлиста на информационные сообщения
            info_patterns = [
                r'обратитесь к поставщику',
                r'contact.*provider',
                r'subscription.*required',
                r'premium.*required',
                r'доступ.*запрещен',
                r'access.*denied',
                r'channel.*unavailable',
                r'канал.*недоступен',
                r'personal.*account',
                r'личный.*кабинет',
                r'уважаемый.*пользователь',
                r'dear.*user',
                r'для.*просмотра.*данного.*канала',
                r'to.*view.*this.*channel',
                r'вам.*необходимо',
                r'you.*need.*to',
                r'в.*личном.*кабинете',
                r'in.*your.*personal.*account',
                r'узнать.*дополнительную',
                r'find.*out.*additional',
                r'информацию',
                r'information',
                r'пожалуйста.*обратитесь',
                r'please.*contact',
                r'подписка.*истекла',
                r'subscription.*expired',
                r'требуется.*подписка',
                r'subscription.*required',
                r'канал.*заблокирован',
                r'channel.*blocked',
                r'недоступен.*в.*вашем.*регионе',
                r'unavailable.*in.*your.*region'
            ]
            
            info_message_count = 0
            for pattern in info_patterns:
                info_message_count += len(re.findall(pattern, playlist_content, re.IGNORECASE))
            
            if info_message_count > 0:
                return {
                    'success': False,
                    'working': False,
                    'method': 'curl_hls',
                    'duration': time.time() - start_time,
                    'error': f'Обнаружено информационное сообщение в плейлисте (сообщений: {info_message_count})',
                    'details': {'info_messages': info_message_count}
                }
            
            # Ищем сегменты в плейлисте
            segment_urls = []
            for line in playlist_content.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith('http'):
                        segment_urls.append(line)
                    else:
                        # Относительный URL
                        base_url = url.rsplit('/', 1)[0] + '/'
                        segment_urls.append(base_url + line)
            
            if not segment_urls:
                return {
                    'success': False,
                    'working': False,
                    'method': 'curl_hls',
                    'duration': time.time() - start_time,
                    'error': 'Не найдены сегменты в HLS плейлисте'
                }
            
            # Проверяем первые несколько сегментов
            segments_to_check = segment_urls[:min(3, len(segment_urls))]
            successful_segments = 0
            total_size = 0
            small_segments = 0
            
            for segment_url in segments_to_check:
                cmd_segment = [
                    'curl', '-s', '-L', '--max-time', '5',
                    '--user-agent', 'VLC/3.0.0 LibVLC/3.0.0',
                    '--write-out', '%{http_code}:%{size_download}',
                    '--output', '/dev/null',
                    segment_url
                ]
                
                seg_result = subprocess.run(cmd_segment, capture_output=True, text=True, timeout=10)
                
                if seg_result.returncode == 0:
                    output_parts = seg_result.stdout.strip().split(':')
                    if len(output_parts) >= 2:
                        http_code = int(output_parts[0])
                        size = int(output_parts[1])
                        
                        if http_code == 200:
                            total_size += size
                            if size > 1000:  # Минимум 1KB для видеосегмента
                                successful_segments += 1
                            else:
                                small_segments += 1
            
            duration = time.time() - start_time
            
            # Проверяем на подозрительно маленькие сегменты (возможная заглушка)
            if small_segments >= 2 and total_size < 500000:  # Меньше 500KB суммарно
                return {
                    'success': False,
                    'working': False,
                    'method': 'curl_hls',
                    'duration': duration,
                    'error': f'Обнаружены подозрительно маленькие сегменты (размер: {total_size} байт, маленьких: {small_segments})',
                    'details': {
                        'segments_checked': len(segments_to_check),
                        'successful_segments': successful_segments,
                        'small_segments': small_segments,
                        'total_size': total_size
                    }
                }
            
            # Дополнительная проверка: если все сегменты очень маленькие, это заглушка
            if len(segments_to_check) > 0 and total_size < 100000:  # Меньше 100KB суммарно
                return {
                    'success': False,
                    'working': False,
                    'method': 'curl_hls',
                    'duration': duration,
                    'error': f'Слишком маленький общий размер сегментов (размер: {total_size} байт) - возможная заглушка',
                    'details': {
                        'segments_checked': len(segments_to_check),
                        'successful_segments': successful_segments,
                        'total_size': total_size
                    }
                }
            
            # Если большинство сегментов загрузились успешно
            if successful_segments >= len(segments_to_check) * 0.6:  # 60% успешных
                return {
                    'success': True,
                    'working': True,
                    'method': 'curl_hls',
                    'duration': duration,
                    'details': {
                        'segments_checked': len(segments_to_check),
                        'successful_segments': successful_segments,
                        'success_rate': successful_segments / len(segments_to_check),
                        'total_size': total_size
                    },
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'working': False,
                    'method': 'curl_hls',
                    'duration': duration,
                    'error': f'Слишком мало рабочих сегментов: {successful_segments}/{len(segments_to_check)}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'working': False,
                'method': 'curl_hls',
                'duration': 0,
                'error': str(e)
            }
    
    def _check_direct_stream_with_curl(self, url):
        """Проверка прямого потока через curl"""
        try:
            cmd = [
                'curl', '-s', '-L',
                '--max-time', str(self.test_duration),
                '--user-agent', 'VLC/3.0.0 LibVLC/3.0.0',
                '--write-out', '%{http_code}:%{size_download}:%{speed_download}',
                '--output', '/dev/null',
                url
            ]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            duration = time.time() - start_time
            
            if result.returncode == 0:
                output_parts = result.stdout.strip().split(':')
                if len(output_parts) >= 3:
                    http_code = int(output_parts[0])
                    size_downloaded = int(float(output_parts[1]))
                    speed = float(output_parts[2])
                    
                    # Проверяем критерии успешности
                    if http_code == 200 and size_downloaded > 10000 and speed > 1000:  # 10KB+ и скорость 1KB/s+
                        return {
                            'success': True,
                            'working': True,
                            'method': 'curl_direct',
                            'duration': duration,
                            'details': {
                                'http_code': http_code,
                                'size_downloaded': size_downloaded,
                                'speed_kbps': speed / 1024
                            },
                            'error': None
                        }
                    else:
                        return {
                            'success': False,
                            'working': False,
                            'method': 'curl_direct',
                            'duration': duration,
                            'error': f'Низкое качество потока: код={http_code}, размер={size_downloaded}, скорость={speed:.0f}B/s'
                        }
            
            return {
                'success': False,
                'working': False,
                'method': 'curl_direct',
                'duration': duration,
                'error': 'Ошибка curl или неожиданный формат ответа'
            }
            
        except Exception as e:
            return {
                'success': False,
                'working': False,
                'method': 'curl_direct',
                'duration': 0,
                'error': str(e)
            }
    
    async def check_playlist_and_cleanup(self, playlist_file):
        """Проверяет плейлист и удаляет нерабочие каналы"""
        logger.info(f"🧹 Проверяем и очищаем плейлист: {playlist_file}")
        
        if not os.path.exists(playlist_file):
            logger.error(f"Файл не найден: {playlist_file}")
            return {'error': 'Файл не найден'}
        
        # Читаем плейлист
        try:
            with open(playlist_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Ошибка при чтении файла: {e}")
            return {'error': str(e)}
        
        # Парсим каналы
        channels = []
        current_extinf = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if line.startswith('#EXTINF'):
                current_extinf = {'extinf': line, 'line_num': i}
            elif line and not line.startswith('#') and current_extinf:
                # Извлекаем название канала
                name_match = re.search(r',([^,]+)$', current_extinf['extinf'])
                name = name_match.group(1).strip() if name_match else 'Unknown'
                
                channels.append({
                    'name': name,
                    'url': line,
                    'extinf': current_extinf['extinf'],
                    'extinf_line': current_extinf['line_num'],
                    'url_line': i
                })
                current_extinf = None
        
        logger.info(f"Найдено каналов для проверки: {len(channels)}")
        
        # Проверяем каналы
        working_channels = []
        broken_channels = []
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def check_channel(channel):
            async with semaphore:
                result = await self.check_video_stream_real(channel['url'])
                
                if result['working']:
                    working_channels.append(channel)
                    logger.info(f"✅ {channel['name']}: OK")
                else:
                    broken_channels.append({
                        **channel,
                        'check_result': result
                    })
                    logger.warning(f"❌ {channel['name']}: {result.get('error', 'Не работает')}")
        
        # Запускаем проверку всех каналов
        tasks = [check_channel(channel) for channel in channels]
        await asyncio.gather(*tasks)
        
        # Создаем бэкап
        backup_file = f"{playlist_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            logger.info(f"💾 Создан бэкап: {backup_file}")
        except Exception as e:
            logger.error(f"Ошибка при создании бэкапа: {e}")
        
        # Перезаписываем плейлист с рабочими каналами (или пустой если все нерабочие)
        try:
            with open(playlist_file, 'w', encoding='utf-8') as f:
                # Записываем заголовок
                f.write("#EXTM3U\n")
                f.write(f"# Очищенный плейлист - {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
                f.write(f"# Рабочих каналов: {len(working_channels)}\n")
                f.write(f"# Удалено нерабочих: {len(broken_channels)}\n")
                
                if len(working_channels) == 0:
                    f.write("# ⚠️ ВСЕ КАНАЛЫ ОКАЗАЛИСЬ НЕРАБОЧИМИ И БЫЛИ УДАЛЕНЫ\n")
                    f.write("# Запустите умное обновление для восстановления из доноров\n")
                
                f.write("\n")
                
                # Записываем рабочие каналы (если есть)
                for channel in working_channels:
                    f.write(f"{channel['extinf']}\n")
                    f.write(f"{channel['url']}\n\n")
            
            if working_channels:
                logger.info(f"✅ Плейлист очищен: {len(working_channels)} рабочих каналов")
            else:
                logger.warning(f"⚠️ Все каналы удалены! Плейлист пуст: {playlist_file}")
                
        except Exception as e:
            logger.error(f"Ошибка при записи очищенного плейлиста: {e}")
            return {'error': f'Ошибка записи: {e}'}
        
        # Формируем отчет
        report = {
            'playlist_file': playlist_file,
            'backup_file': backup_file,
            'total_channels': len(channels),
            'working_channels': len(working_channels),
            'broken_channels': len(broken_channels),
            'cleanup_percentage': (len(broken_channels) / len(channels) * 100) if channels else 0,
            'broken_list': [
                {
                    'name': ch['name'],
                    'url': ch['url'],
                    'error': ch['check_result'].get('error', 'Unknown error'),
                    'method': ch['check_result'].get('method', 'unknown')
                }
                for ch in broken_channels
            ]
        }
        
        return report

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Реальная проверка и очистка IPTV плейлистов')
    parser.add_argument('playlist', help='Путь к файлу плейлиста')
    parser.add_argument('--timeout', type=int, default=30, help='Таймаут проверки (секунды)')
    parser.add_argument('--concurrent', type=int, default=3, help='Количество одновременных проверок')
    parser.add_argument('--test-duration', type=int, default=10, help='Длительность теста (секунды)')
    parser.add_argument('--buffer-threshold', type=int, default=3, help='Порог буферизации')
    
    args = parser.parse_args()
    
    async def run_check():
        checker = RealVideoChecker(
            timeout=args.timeout,
            max_concurrent=args.concurrent,
            test_duration=args.test_duration,
            buffer_threshold=args.buffer_threshold
        )
        
        report = await checker.check_playlist_and_cleanup(args.playlist)
        
        if 'error' in report:
            print(f"❌ Ошибка: {report['error']}")
            return
        
        print("\n" + "="*60)
        print("📊 ОТЧЕТ ПО ОЧИСТКЕ ПЛЕЙЛИСТА")
        print("="*60)
        print(f"📁 Файл: {report['playlist_file']}")
        print(f"💾 Бэкап: {report['backup_file']}")
        print(f"📊 Всего каналов: {report['total_channels']}")
        print(f"✅ Рабочих: {report['working_channels']}")
        print(f"❌ Нерабочих: {report['broken_channels']}")
        print(f"🧹 Очищено: {report['cleanup_percentage']:.1f}%")
        
        if report['broken_list']:
            print(f"\n❌ УДАЛЕННЫЕ КАНАЛЫ:")
            for i, broken in enumerate(report['broken_list'][:10], 1):  # Показываем первые 10
                print(f"   {i}. {broken['name']}: {broken['error']}")
            
            if len(report['broken_list']) > 10:
                print(f"   ... и еще {len(report['broken_list']) - 10} каналов")
        
        print("\n🎉 Очистка завершена!")
    
    asyncio.run(run_check())

if __name__ == "__main__":
    main()
