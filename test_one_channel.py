#!/usr/bin/env python3
# Простой тест одного канала

import subprocess
import time

def test_channel(url, name="Test Channel"):
    print(f"🎬 Тестируем: {name}")
    print(f"🔗 URL: {url}")
    print("=" * 50)
    
    # Тест 1: Базовая доступность
    print("📡 Тест 1: Проверка доступности...")
    try:
        cmd = ['curl', '-s', '-I', '--max-time', '5', '--connect-timeout', '3', url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        
        if result.returncode == 0:
            headers = result.stdout
            if '200 OK' in headers:
                print("✅ Канал доступен (200 OK)")
            elif any(code in headers for code in ['301', '302', '307', '308']):
                print("⚠️ Канал доступен с редиректом")
            else:
                print(f"❌ Неожиданный ответ: {headers.split()[0] if headers else 'Нет ответа'}")
        else:
            print("❌ Канал недоступен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тест 2: Скорость загрузки
    print("\n📊 Тест 2: Проверка скорости загрузки...")
    try:
        cmd = ['curl', '-s', '--max-time', '8', '--write-out', 'SPEED:%{speed_download}|SIZE:%{size_download}', '--output', '/dev/null', url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout:
            info = {}
            for part in result.stdout.strip().split('|'):
                if ':' in part:
                    key, value = part.split(':', 1)
                    try:
                        info[key] = float(value)
                    except:
                        info[key] = value
            
            speed = info.get('SPEED', 0)
            size = info.get('SIZE', 0)
            speed_kb = speed / 1024 if speed > 0 else 0
            size_mb = size / (1024 * 1024) if size > 0 else 0
            
            print(f"📈 Скорость: {speed_kb:.1f} KB/s")
            print(f"📦 Загружено: {size_mb:.2f} MB")
            
            if speed > 10000:
                print("✅ Поток работает хорошо!")
            elif speed > 1000:
                print("⚠️ Поток медленный")
            else:
                print("❌ Поток не работает или очень медленный")
        else:
            print("❌ Не удалось получить данные")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

# Тестируем канал из кинозалы 3
print("🎭 ТЕСТ КАНАЛА ИЗ КАТЕГОРИИ 'КИНОЗАЛЫ 3'")
print("=" * 60)

test_channel(
    "http://178.217.72.66:8080/BCUActionHD/index.m3u8", 
    "BCU Action HD"
)

print("\n" + "=" * 60)
print("🏁 ТЕСТ ЗАВЕРШЕН")

