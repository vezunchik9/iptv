#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Веб-админка для управления IPTV каналами
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import re
import os
import sys
from datetime import datetime
import subprocess
import threading
import time
import asyncio

# Добавляем путь к scripts для импорта
sys.path.append('../scripts')

# Импорт нашего проверщика потоков
try:
    from stream_checker import StreamChecker, StreamCheckerAPI
    STREAM_CHECKER_AVAILABLE = True
except ImportError:
    print("⚠️ Модуль stream_checker недоступен. Проверка потоков отключена.")
    STREAM_CHECKER_AVAILABLE = False

app = Flask(__name__)

class IPTVManager:
    def __init__(self, playlist_file):
        self.playlist_file = playlist_file
        self.channels = []
        self.categories = {}
        self.load_channels()
    
    def load_channels(self):
        """Загружает каналы из M3U файла"""
        try:
            with open(self.playlist_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.splitlines()
            current_extinf = None
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                if line.startswith('#EXTINF'):
                    current_extinf = line
                elif line and not line.startswith('#') and current_extinf:
                    # Парсим информацию о канале
                    channel_data = self.parse_extinf_line(current_extinf, line, i)
                    if channel_data:
                        self.channels.append(channel_data)
                        
                        # Группируем по категориям
                        category = channel_data['group']
                        if category not in self.categories:
                            self.categories[category] = []
                        self.categories[category].append(len(self.channels) - 1)
                    
                    current_extinf = None
            
            print(f"✅ Загружено {len(self.channels)} каналов в {len(self.categories)} категориях")
            
        except Exception as e:
            print(f"❌ Ошибка при загрузке каналов: {e}")
    
    def parse_extinf_line(self, extinf_line, url, line_number):
        """Парсит строку #EXTINF"""
        try:
            # Извлекаем tvg-id
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', extinf_line)
            tvg_id = tvg_id_match.group(1) if tvg_id_match else ""
            
            # Извлекаем tvg-logo
            tvg_logo_match = re.search(r'tvg-logo="([^"]*)"', extinf_line)
            tvg_logo = tvg_logo_match.group(1) if tvg_logo_match else ""
            
            # Извлекаем group-title
            group_match = re.search(r'group-title="([^"]*)"', extinf_line)
            group = group_match.group(1) if group_match else "Разное"
            
            # Извлекаем название канала
            name_match = re.search(r',(.*)$', extinf_line)
            name = name_match.group(1).strip() if name_match else "Без названия"
            
            return {
                'id': len(self.channels),
                'name': name,
                'url': url,
                'tvg_id': tvg_id,
                'tvg_logo': tvg_logo,
                'group': group,
                'enabled': True,
                'working': None,  # Статус проверки
                'last_check': None,
                'line_number': line_number,
                'original_extinf': extinf_line
            }
        except Exception as e:
            print(f"⚠️ Ошибка при парсинге канала: {e}")
            return None
    
    def save_channels(self):
        """Сохраняет изменения в M3U файл"""
        try:
            # Создаем резервную копию
            backup_file = f"{self.playlist_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            subprocess.run(['cp', self.playlist_file, backup_file])
            
            # Генерируем новый плейлист
            content = '#EXTM3U url-tvg="https://iptvx.one/epg/epg_lite.xml.gz"\n'
            content += f'# Televizo IPTV Playlist\n'
            content += f'# Обновлен: {datetime.now().strftime("%d.%m.%Y %H:%M")}\n'
            content += f'# Всего каналов: {len([c for c in self.channels if c["enabled"]])}\n'
            content += f'# Категорий: {len(self.categories)}\n'
            content += f'# GitHub: https://github.com/vezunchik9/iptv\n\n'
            
            # Группируем по категориям
            for category in sorted(self.categories.keys()):
                channels_in_category = [self.channels[i] for i in self.categories[category] if self.channels[i]['enabled']]
                
                if channels_in_category:
                    content += f'# === {category} ({len(channels_in_category)} каналов) ===\n\n'
                    
                    for channel in channels_in_category:
                        # Формируем EXTINF строку
                        extinf = f'#EXTINF:-1'
                        if channel['tvg_id']:
                            extinf += f' tvg-id="{channel["tvg_id"]}"'
                        if channel['tvg_logo']:
                            extinf += f' tvg-logo="{channel["tvg_logo"]}"'
                        extinf += f' group-title="{channel["group"]}"'
                        extinf += f',{channel["name"]}\n'
                        
                        content += extinf
                        content += f'{channel["url"]}\n\n'
            
            # Сохраняем файл
            with open(self.playlist_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Плейлист сохранен: {self.playlist_file}")
            
            # Автоматически пушим на GitHub
            self.push_to_github()
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при сохранении: {e}")
            return False
    
    def push_to_github(self):
        """Автоматически пушит изменения на GitHub"""
        try:
            subprocess.run(['git', 'add', '.'], cwd='..', check=True)
            subprocess.run(['git', 'commit', '-m', f'🔄 Обновление плейлиста через веб-админку - {datetime.now().strftime("%d.%m.%Y %H:%M")}'], cwd='..', check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], cwd='..', check=True)
            print("✅ Изменения отправлены на GitHub")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Ошибка при отправке на GitHub: {e}")

# Глобальные объекты
manager = IPTVManager('../playlists/televizo_main.m3u')
stream_checker_api = StreamCheckerAPI() if STREAM_CHECKER_AVAILABLE else None

@app.route('/')
def index():
    """Главная страница с таблицей каналов"""
    return render_template('index.html', 
                         channels=manager.channels, 
                         categories=list(manager.categories.keys()))

@app.route('/api/channels')
def api_channels():
    """API для получения списка каналов"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    # Фильтрация
    filtered_channels = manager.channels
    
    if category:
        filtered_channels = [c for c in filtered_channels if c['group'] == category]
    
    if search:
        search = search.lower()
        filtered_channels = [c for c in filtered_channels if 
                           search in c['name'].lower() or 
                           search in c['group'].lower()]
    
    # Пагинация
    start = (page - 1) * per_page
    end = start + per_page
    
    return jsonify({
        'channels': filtered_channels[start:end],
        'total': len(filtered_channels),
        'page': page,
        'per_page': per_page,
        'categories': list(manager.categories.keys())
    })

@app.route('/api/channel/<int:channel_id>', methods=['PUT'])
def api_update_channel(channel_id):
    """API для обновления канала"""
    try:
        data = request.json
        
        if 0 <= channel_id < len(manager.channels):
            channel = manager.channels[channel_id]
            
            # Обновляем поля
            if 'name' in data:
                channel['name'] = data['name']
            if 'url' in data:
                channel['url'] = data['url']
            if 'group' in data:
                old_group = channel['group']
                channel['group'] = data['group']
                
                # Перемещаем между категориями
                if old_group in manager.categories:
                    if channel_id in manager.categories[old_group]:
                        manager.categories[old_group].remove(channel_id)
                
                if data['group'] not in manager.categories:
                    manager.categories[data['group']] = []
                manager.categories[data['group']].append(channel_id)
                
            if 'enabled' in data:
                channel['enabled'] = data['enabled']
            if 'tvg_logo' in data:
                channel['tvg_logo'] = data['tvg_logo']
            
            return jsonify({'success': True, 'channel': channel})
        else:
            return jsonify({'success': False, 'error': 'Channel not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/channel/<int:channel_id>/clone', methods=['POST'])
def api_clone_channel(channel_id):
    """API для клонирования канала"""
    try:
        if 0 <= channel_id < len(manager.channels):
            original = manager.channels[channel_id]
            
            # Создаем копию
            clone = original.copy()
            clone['id'] = len(manager.channels)
            clone['name'] = f"{original['name']} (копия)"
            
            manager.channels.append(clone)
            
            # Добавляем в категорию
            if clone['group'] not in manager.categories:
                manager.categories[clone['group']] = []
            manager.categories[clone['group']].append(clone['id'])
            
            return jsonify({'success': True, 'channel': clone})
        else:
            return jsonify({'success': False, 'error': 'Channel not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/channel/<int:channel_id>', methods=['DELETE'])
def api_delete_channel(channel_id):
    """API для удаления канала"""
    try:
        if 0 <= channel_id < len(manager.channels):
            channel = manager.channels[channel_id]
            
            # Удаляем из категории
            if channel['group'] in manager.categories:
                if channel_id in manager.categories[channel['group']]:
                    manager.categories[channel['group']].remove(channel_id)
            
            # Помечаем как удаленный (не удаляем физически для сохранения индексов)
            channel['enabled'] = False
            channel['name'] = f"[УДАЛЕН] {channel['name']}"
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Channel not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/save', methods=['POST'])
def api_save():
    """API для сохранения изменений"""
    try:
        success = manager.save_channels()
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bulk-action', methods=['POST'])
def api_bulk_action():
    """API для массовых операций"""
    try:
        data = request.json
        action = data.get('action')
        channel_ids = data.get('channel_ids', [])
        
        if action == 'enable':
            for channel_id in channel_ids:
                if 0 <= channel_id < len(manager.channels):
                    manager.channels[channel_id]['enabled'] = True
                    
        elif action == 'disable':
            for channel_id in channel_ids:
                if 0 <= channel_id < len(manager.channels):
                    manager.channels[channel_id]['enabled'] = False
                    
        elif action == 'change_group':
            new_group = data.get('new_group')
            if new_group:
                for channel_id in channel_ids:
                    if 0 <= channel_id < len(manager.channels):
                        channel = manager.channels[channel_id]
                        old_group = channel['group']
                        
                        # Удаляем из старой группы
                        if old_group in manager.categories:
                            if channel_id in manager.categories[old_group]:
                                manager.categories[old_group].remove(channel_id)
                        
                        # Добавляем в новую группу
                        channel['group'] = new_group
                        if new_group not in manager.categories:
                            manager.categories[new_group] = []
                        manager.categories[new_group].append(channel_id)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-stream/<int:channel_id>', methods=['POST'])
def api_check_single_stream(channel_id):
    """API для проверки одного потока"""
    if not STREAM_CHECKER_AVAILABLE:
        return jsonify({'success': False, 'error': 'Stream checker not available'}), 503
    
    try:
        if 0 <= channel_id < len(manager.channels):
            channel = manager.channels[channel_id]
            
            # Создаем временный объект для проверки
            checker = StreamChecker(timeout=10)
            
            # Запускаем проверку в отдельном потоке
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    checker.check_single_stream(channel_id, channel['url'], detailed=True)
                )
                
                # Обновляем информацию о канале
                channel['working'] = result['working']
                channel['last_check'] = result['checked_at']
                channel['check_details'] = result.get('details')
                
                return jsonify({
                    'success': True, 
                    'result': result,
                    'channel': channel
                })
                
            finally:
                loop.close()
        else:
            return jsonify({'success': False, 'error': 'Channel not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-all-streams', methods=['POST'])
def api_check_all_streams():
    """API для запуска проверки всех потоков"""
    if not STREAM_CHECKER_AVAILABLE:
        return jsonify({'success': False, 'error': 'Stream checker not available'}), 503
    
    try:
        data = request.json or {}
        detailed = data.get('detailed', False)
        enabled_only = data.get('enabled_only', True)
        
        # Фильтруем каналы
        channels_to_check = []
        for channel in manager.channels:
            if enabled_only and not channel.get('enabled', True):
                continue
            channels_to_check.append({
                'id': channel['id'],
                'name': channel['name'],
                'url': channel['url'],
                'group': channel['group']
            })
        
        if not channels_to_check:
            return jsonify({'success': False, 'error': 'No channels to check'}), 400
        
        # Запускаем проверку в фоне
        def run_check():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                checker = StreamChecker(timeout=10, max_concurrent=10)
                
                def progress_callback(completed, total, result):
                    # Обновляем информацию о канале в менеджере
                    for channel in manager.channels:
                        if channel['id'] == result['channel_id']:
                            channel['working'] = result['working']
                            channel['last_check'] = result['checked_at']
                            channel['check_details'] = result.get('details')
                            break
                
                results = loop.run_until_complete(
                    checker.check_multiple_streams(
                        channels_to_check, detailed, progress_callback
                    )
                )
                
                # Сохраняем отчет
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                report_file = f'../reports/stream_check_{timestamp}.json'
                os.makedirs('../reports', exist_ok=True)
                checker.save_results(report_file)
                
                print(f"✅ Проверка потоков завершена. Отчет: {report_file}")
                
            except Exception as e:
                print(f"❌ Ошибка при проверке потоков: {e}")
            finally:
                loop.close()
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=run_check)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True, 
            'message': f'Проверка {len(channels_to_check)} каналов запущена в фоне'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stream-stats')
def api_stream_stats():
    """API для получения статистики работоспособности потоков"""
    try:
        total_channels = len(manager.channels)
        enabled_channels = sum(1 for c in manager.channels if c.get('enabled', True))
        checked_channels = sum(1 for c in manager.channels if c.get('last_check'))
        working_channels = sum(1 for c in manager.channels if c.get('working') == True)
        broken_channels = sum(1 for c in manager.channels if c.get('working') == False)
        
        # Статистика по категориям
        category_stats = {}
        for channel in manager.channels:
            if not channel.get('enabled', True):
                continue
                
            category = channel.get('group', 'Unknown')
            if category not in category_stats:
                category_stats[category] = {
                    'total': 0,
                    'checked': 0,
                    'working': 0,
                    'broken': 0
                }
            
            category_stats[category]['total'] += 1
            if channel.get('last_check'):
                category_stats[category]['checked'] += 1
                if channel.get('working') == True:
                    category_stats[category]['working'] += 1
                elif channel.get('working') == False:
                    category_stats[category]['broken'] += 1
        
        return jsonify({
            'success': True,
            'stats': {
                'total_channels': total_channels,
                'enabled_channels': enabled_channels,
                'checked_channels': checked_channels,
                'working_channels': working_channels,
                'broken_channels': broken_channels,
                'success_rate': round((working_channels / max(1, checked_channels)) * 100, 2),
                'check_coverage': round((checked_channels / max(1, enabled_channels)) * 100, 2)
            },
            'category_stats': category_stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🌐 Запуск веб-админки IPTV...")
    print("📊 Адрес: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
