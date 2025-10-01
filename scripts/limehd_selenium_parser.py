#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🍋 LimeHD Parser с Selenium
Извлекает прямые потоки через автоматизацию браузера
"""

import time
import json
import re
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LimeHDSeleniumParser:
    def __init__(self):
        self.base_url = "https://limehd.tv"
        self.streams = []
        
    def check_selenium_installed(self):
        """Проверяет установлен ли Selenium"""
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            return True
        except ImportError:
            logger.error("❌ Selenium не установлен!")
            logger.info("Установите: pip3 install --break-system-packages selenium")
            logger.info("И WebDriver: brew install chromedriver")
            return False
    
    def setup_driver(self):
        """Настройка Chrome WebDriver"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Без GUI
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            
            # Включаем логирование сети
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            return driver
            
        except Exception as e:
            logger.error(f"Ошибка настройки драйвера: {e}")
            return None
    
    def extract_streams_from_network(self, driver):
        """Извлекает потоки из сетевых запросов"""
        streams = set()
        
        try:
            # Получаем логи браузера
            logs = driver.get_log('performance')
            
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    
                    if log['method'] == 'Network.responseReceived':
                        url = log['params']['response']['url']
                        
                        # Ищем m3u8 потоки
                        if '.m3u8' in url or '/stream/' in url or 'playlist' in url:
                            logger.info(f"  Найден поток: {url[:100]}...")
                            streams.add(url)
                            
                except:
                    continue
            
            return list(streams)
            
        except Exception as e:
            logger.error(f"Ошибка извлечения потоков: {e}")
            return []
    
    def get_channels_page(self, driver):
        """Получает список каналов со страницы"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            logger.info(f"Загружаем {self.base_url}...")
            driver.get(self.base_url)
            
            # Ждем загрузки
            time.sleep(5)
            
            # Ищем элементы каналов
            channel_selectors = [
                "//div[contains(@class, 'channel')]",
                "//a[contains(@href, '/channel/')]",
                "//div[contains(@class, 'card')]",
            ]
            
            channels = []
            for selector in channel_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        logger.info(f"Найдено элементов: {len(elements)}")
                        for elem in elements[:10]:  # Берем первые 10 для теста
                            try:
                                name = elem.text or elem.get_attribute('title') or "Unknown"
                                href = elem.get_attribute('href')
                                if href and name:
                                    channels.append({'name': name, 'url': href})
                            except:
                                continue
                        if channels:
                            break
                except:
                    continue
            
            return channels
            
        except Exception as e:
            logger.error(f"Ошибка получения каналов: {e}")
            return []
    
    def parse_channel(self, driver, channel_url):
        """Парсит отдельный канал"""
        try:
            logger.info(f"Парсим канал: {channel_url}")
            driver.get(channel_url)
            
            # Ждем загрузки видео
            time.sleep(3)
            
            # Ищем кнопку Play или автостарт
            try:
                play_button = driver.find_element(By.XPATH, "//button[contains(@class, 'play')]")
                play_button.click()
                time.sleep(2)
            except:
                pass
            
            # Извлекаем потоки
            streams = self.extract_streams_from_network(driver)
            
            return streams
            
        except Exception as e:
            logger.error(f"Ошибка парсинга канала: {e}")
            return []
    
    def parse_all(self):
        """Парсит все каналы"""
        if not self.check_selenium_installed():
            return []
        
        logger.info("🍋 Запуск LimeHD Selenium Parser...")
        
        driver = self.setup_driver()
        if not driver:
            return []
        
        try:
            # Получаем список каналов
            channels = self.get_channels_page(driver)
            logger.info(f"Найдено каналов: {len(channels)}")
            
            # Парсим каждый канал
            results = []
            for idx, channel in enumerate(channels[:5], 1):  # Тест на 5 каналах
                logger.info(f"[{idx}/{len(channels)}] {channel['name']}")
                
                streams = self.parse_channel(driver, channel['url'])
                
                if streams:
                    results.append({
                        'name': channel['name'],
                        'streams': streams,
                        'source': 'LimeHD'
                    })
                
                time.sleep(2)  # Пауза между запросами
            
            return results
            
        finally:
            driver.quit()
    
    def save_results(self, results):
        """Сохраняет результаты"""
        if not results:
            logger.warning("Нет результатов для сохранения")
            return
        
        # Сохраняем JSON
        report_path = Path(__file__).parent.parent / "reports" / f"limehd_streams_{int(datetime.now().timestamp())}.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Результаты сохранены: {report_path}")
        
        # Статистика
        total_streams = sum(len(r['streams']) for r in results)
        print(f"\n{'='*60}")
        print(f"📊 СТАТИСТИКА")
        print(f"{'='*60}")
        print(f"Каналов обработано: {len(results)}")
        print(f"Потоков найдено: {total_streams}")
        print(f"{'='*60}\n")

def main():
    parser = LimeHDSeleniumParser()
    results = parser.parse_all()
    parser.save_results(results)

if __name__ == "__main__":
    main()

