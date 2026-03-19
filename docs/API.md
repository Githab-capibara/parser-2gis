# 📚 API Документация Parser2GIS

**Версия:** 2.1.13  
**Дата обновления:** 2026-03-19

---

## 📋 Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Базовое использование](#базовое-использование)
3. [Конфигурация](#конфигурация)
4. [Режимы парсинга](#режимы-парсинга)
5. [Обработка результатов](#обработка-результатов)
6. [Продвинутое использование](#продвинутое-использование)
7. [Обработка ошибок](#обработка-ошибок)

---

## 🚀 Быстрый старт

### Минимальный пример

```python
from parser_2gis import Parser

# Создание парсера
parser = Parser(url="https://2gis.ru/moscow/search/Аптеки")

# Запуск парсинга
data = parser.parse()

# Вывод результатов
print(f"Найдено организаций: {len(data)}")
for org in data[:5]:
    print(f"- {org.name}")
```

### С настройками

```python
from parser_2gis import Parser
from parser_2gis.config import Configuration

# Конфигурация
config = Configuration(
    parser_max_orgs=100,
    parser_max_retries=3,
    chrome_headless=True
)

# Создание и запуск
parser = Parser(
    url="https://2gis.ru/moscow/search/Аптеки",
    config=config
)
data = parser.parse()
```

---

## 📖 Базовое использование

### Инициализация парсера

```python
from parser_2gis import Parser

# Базовая инициализация
parser = Parser(
    url="https://2gis.ru/moscow/search/Рестораны",
    headless=True,        # Скрытый режим
    max_orgs=50,          # Максимум организаций
    output_format="csv"   # Формат вывода
)
```

### Параметры конструктора

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `url` | str | - | URL для парсинга |
| `headless` | bool | False | Скрытый режим браузера |
| `max_orgs` | int | None | Максимум организаций |
| `output_format` | str | "csv" | Формат вывода (csv/xlsx/json) |
| `config` | Configuration | None | Объект конфигурации |

### Метод parse()

```python
# Базовый вызов
data = parser.parse()

# С записью в файл
from parser_2gis.writer.writers.csv_writer import CSVWriter

writer = CSVWriter(output_path="results.csv")
parser.parse(writer=writer)
```

---

## ⚙️ Конфигурация

### Создание конфигурации

```python
from parser_2gis.config import Configuration

config = Configuration(
    # Парсер
    parser_max_orgs=100,
    parser_max_retries=3,
    parser_timeout=30.0,
    
    # Браузер
    chrome_headless=True,
    chrome_startup_delay=2.0,
    
    # Writer
    writer_format="csv",
    writer_buffer_size=262144,
    
    # Логирование
    log_level="INFO",
    log_file="parser.log"
)
```

### Полная конфигурация

```python
from parser_2gis.config import Configuration

config = Configuration(
    # === Парсер ===
    parser_max_orgs=1000,           # Максимум организаций
    parser_max_retries=5,           # Попыток при ошибке
    parser_timeout=30.0,            # Таймаут запроса (сек)
    parser_delay_between_requests=1.0,  # Задержка между запросами
    
    # === Браузер ===
    chrome_headless=True,           # Скрытый режим
    chrome_startup_delay=2.0,       # Задержка запуска (сек)
    chrome_remote_debugging_port=9222,
    
    # === Writer ===
    writer_format="csv",            # csv/xlsx/json
    writer_buffer_size=262144,      # Размер буфера (байт)
    writer_encoding="utf-8-sig",    # Кодировка
    
    # === Кэш ===
    cache_enabled=True,             # Включить кэш
    cache_ttl=3600,                 # Время жизни кэша (сек)
    
    # === Логирование ===
    log_level="INFO",               # DEBUG/INFO/WARNING/ERROR
    log_file="parser.log",          # Файл лога
    log_format="%(asctime)s - %(levelname)s - %(message)s"
)
```

---

## 🔄 Режимы парсинга

### Парсинг по URL

```python
from parser_2gis import Parser

parser = Parser(url="https://2gis.ru/moscow/search/Аптеки")
data = parser.parse()
```

### Парсинг по городу и категории

```python
from parser_2gis import Parser
from parser_2gis.config import Configuration

config = Configuration(
    parser_city="Москва",
    parser_category="Аптеки"
)

parser = Parser(config=config)
data = parser.parse()
```

### Параллельный парсинг

```python
from parser_2gis.parallel_parser import ParallelCityParser
from parser_2gis.config import Configuration

config = Configuration(
    parser_max_workers=10,          # Количество потоков
    parser_max_orgs_per_worker=100
)

cities = [
    {"code": "msk", "name": "Москва"},
    {"code": "spb", "name": "Санкт-Петербург"}
]

categories = [
    {"id": 1, "name": "Аптеки"},
    {"id": 2, "name": "Рестораны"}
]

parser = ParallelCityParser(
    cities=cities,
    categories=categories,
    output_dir="output",
    config=config
)

parser.run()
```

---

## 📊 Обработка результатов

### Структура данных

```python
from parser_2gis import Parser

parser = Parser(url="https://2gis.ru/moscow/search/Аптеки")
data = parser.parse()

# data - это список объектов Org
for org in data:
    print(f"Название: {org.name}")
    print(f"Адрес: {org.address}")
    print(f"Телефон: {org.phone}")
    print(f"Рейтинг: {org.rating}")
    print(f"Отзывы: {org.reviews_count}")
    print(f"Категории: {org.categories}")
    print(f"Часы работы: {org.schedule}")
    print("---")
```

### Поля организации

```python
from parser_2gis.writer.models.org import Org

org: Org
org.name              # Название организации
org.address           # Адрес
org.phone             # Телефон
org.email             # Email
org.website           # Сайт
org.rating            # Рейтинг (0-5)
org.reviews_count     # Количество отзывов
org.categories        # Список категорий
org.rubrics           # Список рубрик
org.schedule          # График работы
org.coordinates       # Координаты (lat, lon)
org.adm_div           # Административное деление
org.contact_groups    # Группы контактов
org.points            # Точки на карте
```

### Экспорт в различные форматы

```python
from parser_2gis.writer.factory import WriterFactory

# CSV
csv_writer = WriterFactory.create_writer("csv", "output.csv")
csv_writer.write_all(data)
csv_writer.close()

# XLSX
xlsx_writer = WriterFactory.create_writer("xlsx", "output.xlsx")
xlsx_writer.write_all(data)
xlsx_writer.close()

# JSON
json_writer = WriterFactory.create_writer("json", "output.json")
json_writer.write_all(data)
json_writer.close()
```

---

## 🔧 Продвинутое использование

### Кэширование

```python
from parser_2gis import Parser
from parser_2gis.cache import CacheManager

# Получение менеджера кэша
cache = CacheManager.get_instance()

# Проверка кэша
if cache.has_cached_result(url):
    data = cache.get_cached_result(url)
    print("Данные получены из кэша")
else:
    parser = Parser(url=url)
    data = parser.parse()
    cache.save_result(url, data)
```

### Обработка ошибок

```python
from parser_2gis import Parser
from parser_2gis.parser.exceptions import (
    ParserTimeoutError,
    ParserNavigationError,
    ParserParseError
)

parser = Parser(url="https://2gis.ru/moscow/search/Аптеки")

try:
    data = parser.parse()
except ParserTimeoutError as e:
    print(f"Таймаут: {e}")
except ParserNavigationError as e:
    print(f"Ошибка навигации: {e}")
except ParserParseError as e:
    print(f"Ошибка парсинга: {e}")
except Exception as e:
    print(f"Неизвестная ошибка: {e}")
```

### Мониторинг прогресса

```python
from parser_2gis import Parser
from parser_2gis.statistics import Statistics

parser = Parser(url="https://2gis.ru/moscow/search/Аптеки")

# Получение статистики
stats = Statistics.get_instance()

# В процессе парсинга
print(f"Собрано организаций: {stats.org_count}")
print(f"Текущая страница: {stats.current_page}")
print(f"Скорость: {stats.org_per_minute} орг/мин")
```

### Пользовательские писатели

```python
from parser_2gis.writer.writers.file_writer import FileWriter
from parser_2gis.writer.models.org import Org

class CustomWriter(FileWriter):
    def _write_data(self, data: list[Org]) -> bool:
        # Кастомная логика записи
        for org in data:
            # Ваша логика
            pass
        return True
    
    def _finalize(self) -> None:
        # Финализация
        pass

# Использование
writer = CustomWriter(output_path="custom_output.txt")
parser.parse(writer=writer)
```

---

## ❗ Обработка ошибок

### Типы исключений

```python
from parser_2gis.parser.exceptions import (
    ParserError,              # Базовое исключение
    ParserTimeoutError,       # Таймаут
    ParserNavigationError,    # Ошибка навигации
    ParserParseError,         # Ошибка парсинга
    ParserWriteError,         # Ошибка записи
    ParserConfigError         # Ошибка конфигурации
)
```

### Стратегии повторных попыток

```python
from parser_2gis import Parser
from parser_2gis.config import Configuration

config = Configuration(
    parser_max_retries=5,         # Максимум попыток
    parser_retry_delay=1.0,       # Базовая задержка
    parser_retry_backoff=2.0      # Экспоненциальный рост
)

parser = Parser(url=url, config=config)

# При ошибке будет выполнено до 5 попыток
# с задержками: 1s, 2s, 4s, 8s, 16s
data = parser.parse()
```

### Логирование ошибок

```python
import logging
from parser_2gis import Parser
from parser_2gis.logger import setup_cli_logger

# Настройка логирования
setup_cli_logger(level="DEBUG", fmt="%(asctime)s - %(levelname)s - %(message)s")

parser = Parser(url="https://2gis.ru/moscow/search/Аптеки")

# Все ошибки будут залогированы
data = parser.parse()
```

---

## 📝 Примеры

### Пример 1: Базовый парсинг

```python
from parser_2gis import Parser

parser = Parser(
    url="https://2gis.ru/moscow/search/Аптеки",
    headless=True,
    max_orgs=50
)

data = parser.parse()
print(f"Найдено: {len(data)} аптек")
```

### Пример 2: Парсинг с конфигурацией

```python
from parser_2gis import Parser
from parser_2gis.config import Configuration

config = Configuration(
    parser_max_orgs=100,
    parser_max_retries=3,
    chrome_headless=True,
    writer_format="xlsx",
    log_level="DEBUG"
)

parser = Parser(
    url="https://2gis.ru/spb/search/Рестораны",
    config=config
)

data = parser.parse()
```

### Пример 3: Параллельный парсинг

```python
from parser_2gis.parallel_parser import ParallelCityParser
from parser_2gis.config import Configuration

config = Configuration(
    parser_max_workers=10,
    parser_max_orgs_per_worker=50
)

cities = [
    {"code": "msk", "name": "Москва"},
    {"code": "spb", "name": "Санкт-Петербург"},
    {"code": "ekb", "name": "Екатеринбург"}
]

categories = [
    {"id": 1, "name": "Аптеки"},
    {"id": 2, "name": "Продукты"}
]

parser = ParallelCityParser(
    cities=cities,
    categories=categories,
    output_dir="output",
    config=config
)

parser.run()
```

### Пример 4: Обработка ошибок

```python
from parser_2gis import Parser
from parser_2gis.parser.exceptions import ParserTimeoutError

parser = Parser(
    url="https://2gis.ru/moscow/search/Кафе",
    max_orgs=100
)

try:
    data = parser.parse()
    print(f"Успешно: {len(data)} организаций")
except ParserTimeoutError:
    print("Превышено время ожидания")
except Exception as e:
    print(f"Ошибка: {e}")
finally:
    print("Парсинг завершён")
```

---

## 📞 Поддержка

- **Документация:** [GitHub Wiki](https://github.com/Githab-capibara/parser-2gis/wiki)
- **Issues:** [GitHub Issues](https://github.com/Githab-capibara/parser-2gis/issues)
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)

---

*Документация обновлена: 2026-03-19*
