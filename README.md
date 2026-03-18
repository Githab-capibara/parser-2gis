# Parser2GIS 🌍

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-LGPLv3%2B-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-840%2B%20passed-brightgreen.svg)](tests/)
[![Code Quality](https://img.shields.io/badge/quality-95/100-brightgreen.svg)](https://github.com/Githab-capibara/parser-2gis)
[![GitHub](https://img.shields.io/badge/GitHub-Githab--capibara-orange.svg)](https://github.com/Githab-capibara/parser-2gis)
[![Version](https://img.shields.io/badge/version-2.1.12-blue.svg)](https://github.com/Githab-capibara/parser-2gis/releases)

**Профессиональное решение для сбора данных с 2GIS** — мощная платформа, использующая передовые технологии браузерной автоматизации для получения структурированной информации о организациях, зданиях и транспортных остановках.

---

## 📋 Содержание

- [Возможности](#-возможности)
- [Быстрый старт](#-быстрый-старт)
- [Установка](#-установка)
- [Режимы работы](#-режимы-работы)
- [CLI интерфейс](#-cli-интерфейс)
- [TUI интерфейс](#-tui-интерфейс)
- [Форматы вывода](#-форматы-вывода)
- [Конфигурация](#-конфигурация)
- [Параллельный парсинг](#-параллельный-парсинг)
- [Производительность](#-производительность)
- [Безопасность](#-безопасность)
- [Примеры использования](#-примеры-использования)
- [FAQ](#-faq)

---

## ✨ Возможности

### 🎯 Основные преимущества

| Характеристика | Значение |
|----------------|----------|
| **География** | 204 города в 18 странах |
| **Категории** | 93 основных категории |
| **Рубрики** | 1786 точных рубрик |
| **Потоки** | До 20 параллельных работников |
| **Форматы** | CSV, XLSX, JSON |
| **Кэширование** | Ускорение 10-100x |
| **Тесты** | 840+ автоматических тестов |

### 🚀 Ключевые функции

**Сбор данных:**
- ✅ Парсинг организаций, зданий, транспортных остановок
- ✅ Извлечение контактов, отзывов, графиков работы
- ✅ Автоматическая навигация и пагинация
- ✅ Интеллектуальная обработка динамического контента

**Надёжность:**
- ✅ Атомарные операции записи данных
- ✅ Гарантированная очистка ресурсов
- ✅ Адаптивная система повторных попыток
- ✅ Мониторинг здоровья браузера с авто-восстановлением

**Производительность:**
- ✅ Кэширование результатов на SQLite
- ✅ Пакетная запись до 500 записей
- ✅ Оптимизированные буферные операции (256KB)
- ✅ Компилированные регулярные выражения

**Интерфейсы:**
- ✅ CLI для автоматизации и CI/CD
- ✅ TUI для интерактивной работы
- ✅ Программное API для интеграции

### 🛠️ Технологический стек

| Компонент | Назначение |
|-----------|------------|
| **Python 3.10-3.12** | Основная платформа |
| **Pydantic v2** | Валидация и сериализация данных |
| **Chrome DevTools Protocol** | Управление браузером |
| **Rich** | CLI интерфейсы и прогресс-бары |
| **Pytermgui** | Современный TUI интерфейс |
| **SQLite** | Кэширование и хранение |
| **psutil** | Мониторинг системных ресурсов |

---

## 🚀 Быстрый старт

### Мгновенный запуск

```bash
# Установка
pip install parser-2gis

# Базовый парсинг
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" -o pharmacies.csv --chrome.headless yes
```

### Сценарий 1: Парсинг по URL

```bash
# Парсинг 5 организаций для демонстрации
parser-2gis \
  -i "https://2gis.ru/moscow/search/Аптеки" \
  -o moscow_pharmacies.csv \
  -f csv \
  --parser.max-records 5 \
  --chrome.headless yes
```

**Ожидаемый результат:**
```
✅ Завершено за 12.3 сек
📊 Обработано страниц: 1
💾 Сохранено записей: 5
📁 Файл: moscow_pharmacies.csv
```

### Сценарий 2: Все категории города

```bash
# Парсинг всех 93 категорий Омска в 5 потоков
parser-2gis \
  --cities omsk \
  --categories-mode \
  --parallel-workers 5 \
  -o output/omsk_all_categories/ \
  -f csv \
  --chrome.headless yes \
  --chrome.disable-images yes
```

**Ожидаемый результат:**
```
✅ Завершено за 8.5 мин
📊 Обработано категорий: 93
💾 Сохранено записей: 15,432
📁 Файлов создано: 93
```

### Сценарий 3: Несколько городов

```bash
# Парсинг аптек в Москве, СПб и Казани
parser-2gis \
  --cities moscow spb kazan \
  --categories-mode \
  -o output/multi_city/ \
  -f csv \
  --parallel-workers 3
```

### Сценарий 4: TUI интерфейс

```bash
# Запуск интерактивного интерфейса
parser-2gis --tui-new

# Автоматический запуск с预设 настройками
parser-2gis --tui-new-omsk
```

---

## 📦 Установка

### Требования

| Компонент | Версия | Примечание |
|-----------|--------|------------|
| **Python** | 3.10-3.12 | Обязательное требование |
| **Google Chrome** | Актуальная | Для браузерной автоматизации |
| **Git** | Актуальная | Для клонирования репозитория |

### Способ 1: PyPI (рекомендуется)

```bash
pip install parser-2gis
```

### Способ 2: Из исходников

```bash
# Клонирование
git clone https://github.com/Githab-capibara/parser-2gis.git
cd parser-2gis

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установка
pip install -e .[dev]

# Pre-commit хуки (опционально)
pre-commit install
```

### Проверка установки

```bash
# Версия
parser-2gis --version
# Output: parser-2gis 2.1.12

# Справка
parser-2gis --help

# Через модуль
python -m parser_2gis --help
```

---

## 🎮 Режимы работы

### CLI: Автоматизация и скрипты

**Преимущества:**
- ⚡ Мгновенный запуск
- 🔧 Интеграция в CI/CD
- 📜 Автоматизация процессов
- 🎛️ Полный контроль через аргументы

**Идеально для:**
- Серверных развертываний
- Cron задач
- CI/CD пайплайнов
- Пакетной обработки

### TUI: Интерактивная работа

**Преимущества:**
- 🖼️ Визуальный многоэкранный интерфейс
- 🏙️ Поиск и выбор городов/категорий
- 📈 Прогресс в реальном времени
- 🎓 Не требует знания команд
- 💾 Просмотр кэша и статистики

**Идеально для:**
- Разовых задач
- Исследования данных
- Визуального контроля
- Обучения новых пользователей

**Запуск:**
```bash
# Современный TUI (pytermgui)
parser-2gis --tui-new

# С预设 настройками для Омска
parser-2gis --tui-new-omsk
```

---

## 💻 CLI интерфейс

### Базовые аргументы

| Аргумент | Описание | Пример |
|----------|----------|--------|
| `-i, --url` | URL для парсинга | `"https://2gis.ru/..."` |
| `-o, --output` | Выходной файл/директория | `output.csv` |
| `-f, --format` | Формат вывода | `csv`, `xlsx`, `json` |
| `--cities` | Список городов | `moscow spb kazan` |
| `--categories-mode` | Режим категорий | Флаг |
| `--parallel-workers` | Количество потоков | `1-20` |

### Настройки Chrome

| Параметр | Описание | Значение |
|----------|----------|----------|
| `--chrome.headless` | Фоновый режим | `yes`/`no` |
| `--chrome.disable-images` | Блокировка изображений | `yes`/`no` |
| `--chrome.memory-limit` | Лимит памяти (МБ) | `512`, `1024` |
| `--chrome.binary-path` | Путь к Chrome | `/usr/bin/google-chrome` |

### Настройки парсера

| Параметр | Описание | Значение |
|----------|----------|----------|
| `--parser.max-records` | Максимум записей | `100`, `1000` |
| `--parser.delay-between-clicks` | Задержка кликов (мс) | `0-1000` |
| `--parser.max-retries` | Повторные попытки | `3`, `5` |
| `--parser.retry-on-network-errors` | Retry при ошибках сети | `yes`/`no` |
| `--parser.memory-threshold` | Порог памяти (МБ) | `2048` |

### Полный пример

```bash
parser-2gis \
  --cities moscow spb \
  --categories-mode \
  --parallel-workers 5 \
  --chrome.headless yes \
  --chrome.disable-images yes \
  --chrome.memory-limit 512 \
  --parser.max-records 100 \
  --parser.delay-between-clicks 500 \
  --parser.max-retries 3 \
  --parser.retry-on-network-errors yes \
  -o output/ \
  -f csv
```

---

## 🖥️ TUI интерфейс

### Современный интерфейс на pytermgui

**Экраны:**

| Экран | Назначение |
|-------|------------|
| 🏠 Главное меню | Навигация по разделам |
| 🏙️ Выбор городов | Поиск и множественный выбор |
| 📂 Выбор категорий | Поиск и выбор категорий |
| 🌐 Настройки браузера | Конфигурация Chrome |
| ⚙️ Настройки парсера | Параметры сбора данных |
| 📤 Настройки вывода | Формат и кодировка |
| 💾 Просмотр кэша | Управление кэшем |
| ℹ️ О программе | Информация |
| 📊 Экран парсинга | Прогресс и логи |

### Навигация

| Клавиша | Действие |
|---------|----------|
| `↑` `↓` | Перемещение по меню |
| `Enter` | Выбор / Подтверждение |
| `Tab` | Переключение между полями |
| `Пробел` | Отметка чекбокса |
| `Esc` | Назад / Отмена |
| `q` | Выход |
| `Мышь` | Клик по элементам |

### Рабочий процесс

```
1. Главное меню
   ↓
2. Выбор городов (поиск + чекбоксы)
   ↓
3. Выбор категорий (поиск + чекбоксы)
   ↓
4. Настройки (браузер, парсер, вывод)
   ↓
5. Запуск парсинга
   ↓
6. Мониторинг прогресса
   ↓
7. Просмотр результатов
```

---

## 📊 Форматы вывода

### CSV

**Назначение:** Табличные данные с разделителями

**Преимущества:**
- ✅ Универсальная совместимость
- ✅ Высокая скорость записи/чтения
- ✅ Поддержка Excel и Google Sheets
- ✅ Компактный размер

**Конфигурация:**
```json
{
  "writer": {
    "csv": {
      "add_rubrics": true,
      "add_comments": true,
      "columns_per_entity": 3,
      "remove_empty_columns": true,
      "remove_duplicates": true,
      "join_char": "; "
    }
  }
}
```

### XLSX

**Назначение:** Файлы Microsoft Excel

**Преимущества:**
- 📊 Автоматическое форматирование
- 📏 Подбор ширины колонок
- 🔍 Встроенные фильтры
- 💼 Профессиональный вид

### JSON

**Назначение:** Структурированные данные

**Преимущества:**
- 🗂️ Полная структура данных
- 💻 Программный парсинг
- 📦 Поддержка вложенности
- 🔧 Гибкость обработки

---

## ⚙️ Конфигурация

### Создание конфигурации

```bash
# Генерация шаблона
parser-2gis --config config.json
```

### Пример конфигурации

```json
{
  "version": "2.1",
  "log": {
    "level": "INFO",
    "cli_format": "%(levelname)s - %(message)s",
    "gui_format": "[%(asctime)s] %(levelname)s: %(message)s"
  },
  "writer": {
    "encoding": "utf-8-sig",
    "verbose": true,
    "csv": {
      "add_rubrics": true,
      "add_comments": true,
      "columns_per_entity": 3,
      "remove_empty_columns": true,
      "remove_duplicates": true,
      "join_char": "; "
    }
  },
  "chrome": {
    "headless": false,
    "disable_images": true,
    "silent_browser": true,
    "memory_limit": 1024
  },
  "parser": {
    "max_records": null,
    "delay_between_clicks": 0,
    "skip_404_response": true,
    "stop_on_first_404": false,
    "max_consecutive_empty_pages": 3,
    "max_retries": 3,
    "retry_on_network_errors": true,
    "retry_delay_base": 1.0,
    "memory_threshold": 2048
  }
}
```

### Использование

```bash
parser-2gis --config config.json \
  -i "https://2gis.ru/moscow/search/Аптеки" \
  -o output.csv \
  -f csv
```

---

## 🔄 Параллельный парсинг

### Режим категорий

```bash
# Все категории Омска (5 потоков)
parser-2gis \
  --cities omsk \
  --categories-mode \
  --parallel-workers 5 \
  -o output/omsk_all/ \
  -f csv
```

### Несколько городов

```bash
# Три города (3 потока)
parser-2gis \
  --cities moscow spb kazan \
  --categories-mode \
  --parallel-workers 3 \
  -o output/ \
  -f csv
```

### Максимальная производительность

```bash
# 20 потоков для серверов
parser-2gis \
  --cities moscow spb \
  --categories-mode \
  --parallel-workers 20 \
  --chrome.headless yes \
  --chrome.disable-images yes \
  --parser.use-gc yes \
  --parser.gc-pages-interval 10 \
  -o output/ \
  -f csv
```

### Рекомендации

| Сценарий | Потоки | Настройки |
|----------|--------|-----------|
| **Десктоп** | 3-5 | `--chrome.memory-limit 512` |
| **Сервер** | 10-20 | `--chrome.headless yes` |
| **Большие данные** | 5-10 | `--parser.use-gc yes` |
| **Малые города** | 1-3 | `--parser.stop-on-first-404 yes` |

---

## 📈 Производительность

### Метрики

| Показатель | Значение |
|------------|----------|
| **Ускорение кэширования** | 10-100x |
| **Оптимизация записи** | 25-40% |
| **Размер буфера** | 256KB |
| **Пакетная запись** | До 500 строк |
| **Кэш кэширования** | 500MB LRU |

### Оптимизации

- ⚡ **Кэширование результатов** — SQLite с TTL 24 часа
- 📦 **Буферизация операций** — 256KB буферы
- 🔄 **Пакетная запись** — до 500 записей за операцию
- 🧹 **Управление памятью** — LRU eviction 500MB
- 🎯 **Компиляция regex** — однократная компиляция
- ⚡ **Атомарные операции** — rename вместо copy

### Бенчмарки

```bash
# Запуск бенчмарков
pytest tests/test_benchmarks.py --benchmark-only

# Пример результатов:
# test_cache_performance: 0.002ms (кэш) vs 150ms (сеть)
# test_url_generation: 0.05ms на URL
# test_validation: 0.01ms на запись
```

---

## 🔐 Безопасность

### Защищённость операций

| Угроза | Защита |
|--------|--------|
| **SQL Injection** | Валидация SHA256 хешей |
| **XSS атаки** | Валидация JavaScript кода |
| **SSRF** | Блокировка localhost/private IP |
| **Race Condition** | RLock с timeout |
| **Утечка ресурсов** | Гарантированная очистка |

### Переменные окружения

```bash
# GitHub токен для интеграции
export GITHUB_TOKEN="ghp_..."

# Таймауты
export MERGE_LOCK_TIMEOUT="30"
export MAX_LOCK_FILE_AGE="3600"

# Лимиты
export MAX_TEMP_FILES="1000"
```

### Рекомендации

1. **Используйте виртуальное окружение:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Настройте переменные окружения:**
   ```bash
   export GITHUB_TOKEN="your_token"
   export PARSER_LOG_LEVEL="INFO"
   ```

3. **Регулярно обновляйтесь:**
   ```bash
   pip install --upgrade parser-2gis
   ```

---

## 💡 Примеры использования

### Use Case 1: Маркетинговое агентство

**Задача:** Собрать контакты конкурентов для анализа рынка.

**Решение:**
```bash
parser-2gis \
  --cities moscow spb \
  --categories-mode \
  --parallel-workers 5 \
  -o competitors/ \
  -f csv
```

**Результат:** 15,000+ организаций за 2 часа.

### Use Case 2: Логистическая компания

**Задача:** Найти все склады в регионе.

**Решение:**
```bash
parser-2gis \
  -i "https://2gis.ru/ekb/search/Склады" \
  -o warehouses_ekb.xlsx \
  -f xlsx \
  --chrome.headless yes
```

**Результат:** 340 складов с контактами и адресами.

### Use Case 3: Исследователь данных

**Задача:** Проанализировать распределение аптек по городу.

**Решение (Python API):**
```python
from parser_2gis import CacheManager, DataValidator

cache = CacheManager()
validator = DataValidator()

# Получение данных
data = cache.get('https://2gis.ru/moscow/search/Аптеки')

# Валидация
for record in data:
    if validator.validate_phone(record['phone']).is_valid:
        process(record)
```

### Use Case 4: CI/CD интеграция

**Задача:** Автоматический сбор данных для отчёта.

**Решение (GitHub Actions):**
```yaml
- name: Parse 2GIS data
  run: |
    pip install parser-2gis
    parser-2gis \
      --cities moscow \
      --categories-mode \
      -o output/ \
      -f csv \
      --chrome.headless yes
```

---

## ❓ FAQ

### Общие вопросы

**В: Какие города поддерживаются?**

О: 204 города в 18 странах, включая Россию, Казахстан, Беларусь, Украину, Чехию, Италию, Чили и другие.

**В: Как часто обновляются данные?**

О: Данные собираются в реальном времени из 2GIS. Кэширование ускоряет повторные запросы (TTL 24 часа).

**В: Можно ли парсить свои категории?**

О: Да, создайте файл `parser_2gis/data/custom_categories.py` с нужными категориями.

### Технические вопросы

**В: Сколько потоков использовать?**

О: 
- Десктоп: 3-5 потоков
- Сервер: 10-20 потоков
- Зависит от доступной RAM и CPU

**В: Где хранится кэш?**

О: В директории `~/.cache/parser-2gis/` (SQLite база данных).

**В: Как очистить кэш?**

О: 
```bash
# Через TUI: Экран кэша → Очистить
# Вручную: rm -rf ~/.cache/parser-2gis/
```

### Проблемы и решения

**В: Ошибка "Chrome not found"**

О: Установите Google Chrome:
```bash
# Ubuntu/Debian
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
```

**В: Превышен лимит памяти**

О: Уменьшите количество потоков или установите лимит:
```bash
parser-2gis --chrome.memory-limit 512 ...
```

**В: Медленный парсинг**

О: Включите кэширование и headless режим:
```bash
parser-2gis --chrome.headless yes --parallel-workers 10 ...
```

---

## 🤝 Поддержка

### Ресурсы

| Ресурс | Назначение |
|--------|------------|
| [GitHub Issues](https://github.com/Githab-capibara/parser-2gis/issues) | Баг-трекинг |
| [Discussions](https://github.com/Githab-capibara/parser-2gis/discussions) | Вопросы и обсуждения |
| [Security](https://github.com/Githab-capibara/parser-2gis/security) | Отчёты об уязвимостях |
| [Releases](https://github.com/Githab-capibara/parser-2gis/releases) | Версии и changelog |

### Контакты

- **Email:** support@parser-2gis.local
- **GitHub:** [@Githab-capibara](https://github.com/Githab-capibara)

### Вклад в проект

Приветствуется участие в развитии проекта:

1. Форкните репозиторий
2. Создайте ветку (`git checkout -b feature/amazing-feature`)
3. Закоммитьте изменения (`git commit -m 'Add amazing feature'`)
4. Запушьте (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

---

## 📄 Лицензия

Parser2GIS распространяется под лицензией **GNU LGPLv3+**.

Полный текст лицензии доступен в файле [LICENSE](LICENSE).

---

**Parser2GIS v2.1.12** — Профессиональное решение для сбора данных с 2GIS.

[![GitHub Stars](https://img.shields.io/github/stars/Githab-capibara/parser-2gis?style=social)](https://github.com/Githab-capibara/parser-2gis/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/Githab-capibara/parser-2gis?style=social)](https://github.com/Githab-capibara/parser-2gis/network/members)
