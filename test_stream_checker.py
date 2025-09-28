#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест улучшенной проверки потоков
"""

import asyncio
import sys
import os

# Добавляем путь к скриптам
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from stream_checker import StreamChecker

async def test_stream_checker():
    """Тестируем улучшенную проверку потоков"""
    print("🧪 Тестируем улучшенную проверку потоков...\n")
    
    # Тестовые URL (используем известные рабочие потоки)
    test_urls = [
        "http://109.71.162.112/live/sd.jasminchannel.stream/chunklist_w233748568.m3u8",
        "http://cdn.adultiptv.net/bigass.m3u8",
        "http://194.116.150.47:1935/vxtv/live_360p/chunklist_w543388767.m3u8",
        "https://httpbin.org/status/200",  # Тестовый URL
        "https://httpbin.org/status/404",  # Несуществующий URL
    ]
    
    checker = StreamChecker(timeout=15)
    
    for i, url in enumerate(test_urls, 1):
        print(f"📺 Тест {i}: {url[:60]}...")
        
        try:
            result = await checker.check_single_stream(i, url, detailed=False)
            
            status = "✅ РАБОТАЕТ" if result['working'] else "❌ НЕ РАБОТАЕТ"
            method = result.get('check_method', 'unknown')
            time_ms = result.get('response_time', 0)
            error = result.get('error', 'Нет ошибок')
            
            print(f"   Результат: {status}")
            print(f"   Метод: {method}")
            print(f"   Время: {time_ms}мс")
            if error and error != 'Нет ошибок':
                print(f"   Ошибка: {error}")
            print()
            
        except Exception as e:
            print(f"   ❌ ОШИБКА: {e}\n")

if __name__ == "__main__":
    asyncio.run(test_stream_checker())
