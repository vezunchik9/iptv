# 🎬 Автоматический Парсер IPTV Плейлистов

Система автоматического парсинга и интеграции потоков из донорских плейлистов в ваши категории.

## 🚀 Возможности

- ✅ **Автоматический парсинг** множественных донорских плейлистов
- ✅ **Умная категоризация** каналов по ключевым словам
- ✅ **Проверка дубликатов** - не добавляет уже существующие каналы
- ✅ **Валидация URL** - опциональная проверка работоспособности
- ✅ **Автоматический Git push** - обновления сразу в репозиторий
- ✅ **Гибкая конфигурация** - легко добавлять новых доноров
- ✅ **Детальная статистика** - полный отчет о процессе

## 📁 Структура файлов

```
├── scripts/
│   ├── playlist_parser.py           # Базовый парсер
│   └── advanced_playlist_parser.py  # Продвинутый парсер с конфигурацией
├── donors_config.json               # Конфигурация доноров и категорий
├── auto_update.sh                   # Скрипт автообновления с Git push
└── categories/                      # Обновленные категории
```

## ⚙️ Конфигурация доноров

Файл `donors_config.json` содержит:

### Доноры
```json
{
  "donors": {
    "IPTVSHARED": {
      "url": "https://raw.githubusercontent.com/IPTVSHARED/iptv/refs/heads/main/IPTV_SHARED.m3u",
      "enabled": true,
      "description": "Основной донор с большим количеством каналов",
      "priority": 1
    }
  }
}
```

### Категории
```json
{
  "category_mapping": {
    "спортивные": {
      "keywords": ["спорт", "sport", "футбол", "хоккей", "eurosport", "match"],
      "exclude": ["новости"]
    },
    "кино_и_сериалы": {
      "keywords": ["кино", "cinema", "movie", "tv1000", "paramount"],
      "exclude": ["новости", "детск"]
    }
  }
}
```

## 🎯 Использование

### 1. Базовый парсинг
```bash
# Простой парсинг всех доноров
python3 scripts/playlist_parser.py
```

### 2. Продвинутый парсинг
```bash
# С валидацией URL
python3 scripts/advanced_playlist_parser.py --validate

# С кастомной конфигурацией
python3 scripts/advanced_playlist_parser.py --config my_config.json
```

### 3. Добавление нового донора
```bash
# Добавить донора через командную строку
python3 scripts/advanced_playlist_parser.py --add-donor "NewDonor" "http://example.com/playlist.m3u"
```

### 4. Полное автообновление с Git
```bash
# Парсинг + обновление + коммит + push
./auto_update.sh
```

## 🔄 Автоматизация

### Настройка cron для автообновления
```bash
# Каждый день в 6:00 утра
0 6 * * * cd /path/to/iptv && ./auto_update.sh >> logs/auto_update.log 2>&1

# Каждые 6 часов
0 */6 * * * cd /path/to/iptv && ./auto_update.sh >> logs/auto_update.log 2>&1
```

### GitHub Actions (опционально)
Создайте `.github/workflows/update-playlists.yml`:
```yaml
name: Update Playlists
on:
  schedule:
    - cron: '0 6 * * *'  # Каждый день в 6:00 UTC
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Setup Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: pip install requests aiohttp
    - name: Update playlists
      run: ./auto_update.sh
```

## 📊 Статистика и мониторинг

После каждого запуска вы получите детальную статистику:

```
📊 СТАТИСТИКА ОБРАБОТКИ:
   Доноров обработано: 1
   Всего распарсено каналов: 1725
   Добавлено новых каналов: 342
   Пропущено каналов: 1383
   Обновлено категорий: 15

📁 Обновленные категории:
   - спортивные: 45 каналов
   - кино_и_сериалы: 128 каналов
   - эфирные: 32 каналов
   ...
```

## 🛠️ Настройки

В `donors_config.json` секция `settings`:

```json
{
  "settings": {
    "auto_update": true,           // Автообновление
    "backup_before_update": true,  // Бэкап перед обновлением
    "git_auto_push": true,         // Автопуш в Git
    "check_duplicates": true,      // Проверка дубликатов
    "validate_urls": false,        // Валидация URL (медленно)
    "max_channels_per_category": 1000  // Лимит каналов в категории
  }
}
```

## 🎭 Категоризация каналов

Система автоматически определяет категорию канала по:
- **Названию канала**
- **Группе в плейлисте**
- **Ключевым словам** из конфигурации
- **Исключениям** для точности

### Примеры категоризации:
- `"Eurosport 1 HD"` → `спортивные`
- `"TV1000 Action"` → `кинозалы_2`
- `"Первый канал"` → `эфирные`
- `"Discovery Channel"` → `познавательные`

## 🔍 Добавление новых доноров

### Через конфигурацию:
Отредактируйте `donors_config.json`:
```json
{
  "donors": {
    "MyDonor": {
      "url": "http://example.com/playlist.m3u",
      "enabled": true,
      "priority": 2,
      "description": "Мой новый донор"
    }
  }
}
```

### Через командную строку:
```bash
python3 scripts/advanced_playlist_parser.py --add-donor "MyDonor" "http://example.com/playlist.m3u"
```

## 📝 Логи и отладка

Логи сохраняются в:
- **Консоль** - основная информация
- **auto_update.log** - логи автообновления
- **Git commits** - история изменений

Уровни логирования:
- `INFO` - основная информация
- `DEBUG` - детальная отладка
- `ERROR` - ошибки

## 🚨 Устранение проблем

### Проблема: Не добавляются каналы
**Решение:** Проверьте категоризацию в `donors_config.json`

### Проблема: Дубликаты каналов
**Решение:** Включите `"check_duplicates": true`

### Проблема: Медленная работа
**Решение:** Отключите `"validate_urls": false`

### Проблема: Ошибки Git push
**Решение:** Настройте Git credentials:
```bash
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

## 🎉 Результат

После настройки у вас будет:
- ✅ **Автоматическое пополнение** плейлистов
- ✅ **Актуальные каналы** из множественных источников  
- ✅ **Организованные категории** без дубликатов
- ✅ **Автоматические обновления** в Git
- ✅ **Детальная статистика** процесса

**Ваши плейлисты всегда будут свежими и полными!** 🎬📺
