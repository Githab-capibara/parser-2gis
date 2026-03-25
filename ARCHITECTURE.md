# Архитектура проекта parser-2gis

**Версия:** 2.1.0
**Дата обновления:** 2026-03-25

## Общая схема проекта

```
parser_2gis/
├── cache/               # Пакет кэширования на SQLite (НОВЫЙ в v2.1.0)
│   ├── __init__.py      # Экспорт API: CacheManager
│   ├── manager.py       # CacheManager класс (кэширование)
│   ├── pool.py          # ConnectionPool класс
│   ├── serializer.py    # JsonSerializer класс
│   └── validator.py     # CacheDataValidator класс
├── chrome/              # Модуль работы с браузером Chrome
│   ├── browser.py       # Управление браузером
│   ├── constants.py     # Константы Chrome
│   ├── dom.py           # DOM операции
│   ├── exceptions.py    # Исключения Chrome
│   ├── file_handler.py  # Обработка файлов
│   ├── health_monitor.py # Мониторинг здоровья
│   ├── http_cache.py    # HTTP кэширование (НОВЫЙ в v2.1.0)
│   ├── js_executor.py   # Валидация и выполнение JS (НОВЫЙ в v2.1.0)
│   ├── options.py       # Опции Chrome
│   ├── patches/         # Патчи pychrome
│   ├── rate_limiter.py  # Rate limiting (НОВЫЙ в v2.1.0)
│   ├── remote.py        # Chrome DevTools Protocol
│   └── utils.py         # Утилиты Chrome
├── cli/                 # CLI интерфейс (НОВЫЙ в v2.1.0)
│   ├── __init__.py      # Экспорт API
│   ├── arguments.py     # Парсинг аргументов
│   ├── formatter.py     # Форматировщик справки
│   ├── main.py          # Точка входа CLI
│   └── validator.py     # Валидация аргументов
├── data/                # Данные (города, категории, рубрики)
├── logger/              # Модуль логирования
├── parallel/            # Модуль параллельной обработки
│   ├── __init__.py      # Экспорт API
│   ├── file_merger.py   # Слияние CSV файлов
│   ├── options.py       # Опции параллелизма
│   ├── parallel_parser.py # Параллельный парсинг
│   ├── progress_tracker.py # Прогресс
│   └── temp_file_timer.py # Очистка temp файлов
├── parser/              # Модуль парсинга данных
│   ├── parsers/         # Конкретные парсеры
│   ├── adaptive_limits.py
│   ├── end_of_results.py
│   ├── exceptions.py
│   ├── factory.py       # Registry pattern для парсеров
│   ├── options.py
│   ├── smart_retry.py
│   └── utils.py
├── runner/              # Модуль запуска парсера
├── tui_textual/         # TUI интерфейс на Textual
├── utils/               # Общие утилиты
│   ├── __init__.py      # Экспорт API
│   ├── cache_monitor.py # Мониторинг кэшей (НОВЫЙ в v2.1.0)
│   ├── decorators.py    # Декораторы ожидания
│   ├── path_utils.py    # Валидация путей (НОВЫЙ в v2.1.0)
│   ├── sanitizers.py    # Санитаризация данных
│   ├── url_utils.py     # Генерация URL
│   └── validation_utils.py # Валидация городов/категорий
├── validation/          # Модуль валидации
│   ├── __init__.py      # Экспорт API
│   ├── data_validator.py # Валидация данных
│   ├── legacy.py        # Обратная совместимость
│   ├── path_validator.py # Валидация путей
│   └── url_validator.py # Валидация URL
├── writer/              # Модуль записи данных
│   ├── models/          # Модели данных
│   ├── writers/         # Конкретные writers
│   │   ├── csv_writer.py # Базовый CSV writer
│   │   ├── csv_buffer_manager.py # Буферизация
│   │   ├── csv_deduplicator.py # Дедупликация
│   │   ├── csv_post_processor.py # Постобработка
│   │   ├── file_writer.py # Базовый writer
│   │   ├── json_writer.py # JSON writer
│   │   └── xlsx_writer.py # XLSX writer (исправлена иерархия)
│   ├── exceptions.py
│   ├── factory.py       # Registry pattern для writers
│   └── options.py
├── common.py            # Базовые утилиты (обратная совместимость)
├── config.py            # Конфигурация через Pydantic
├── constants.py         # Централизованные константы
├── exceptions.py        # Иерархия исключений
├── main.py              # CLI точка входа (обратная совместимость)
├── parallel_helpers.py  # Helpers для параллелизма
├── parallel_optimizer.py # Оптимизатор параллелизма
├── paths.py             # Управление путями
├── protocols.py         # Protocol для callback и интерфейсов
│                        # BrowserService (НОВЫЙ в v2.1.0)
├── pydantic_compat.py   # Pydantic совместимость
├── signal_handler.py    # Обработчик сигналов
├── statistics.py        # Статистика работы
├── temp_file_manager.py # Менеджер временных файлов
└── version.py           # Версия пакета
```

## Основные изменения в версии 2.1.0

### Рефакторинг cache.py в пакет
Разделение крупного модуля cache.py (1910 строк) на пакет:
- **manager.py** - CacheManager класс (880 строк)
- **pool.py** - ConnectionPool класс (563 строки)
- **serializer.py** - JsonSerializer класс (169 строк)
- **validator.py** - CacheDataValidator класс (295 строк)

### Рефакторинг chrome/remote.py
Разделение крупного модуля remote.py (1978 строк) на компоненты:
- **remote.py** - ChromeRemote класс (925 строк)
- **js_executor.py** - Валидация и выполнение JS (515 строк)
- **http_cache.py** - HTTP кэширование (163 строки)
- **rate_limiter.py** - Rate limiting (133 строки)

### Рефакторинг main.py в пакет cli/
Разделение крупного модуля main.py (1397 строк) на пакет:
- **main.py** - Точка входа CLI (558 строк)
- **arguments.py** - Парсинг аргументов (296 строк)
- **validator.py** - Валидация аргументов (281 строка)
- **formatter.py** - Форматировщик справки (114 строк)

### Registry pattern для writers и parsers
Внедрение паттерна Registry для расширяемости:
- **writer/factory.py** - WRITER_REGISTRY с декоратором @register_writer()
- **parser/factory.py** - PARSER_REGISTRY с декоратором @register_parser(priority=N)

### BrowserService Protocol
Добавлен Protocol для разрыва зависимости между chrome/ и parser/:
- **protocols.py** - BrowserService Protocol
- ChromeRemote реализует BrowserService
- Поддержка внедрения зависимостей через Protocol

### Улучшения utils/
Новые модули для централизации функциональности:
- **path_utils.py** - Валидация путей (validate_path_safety, validate_path_traversal)
- **cache_monitor.py** - Мониторинг кэшей (get_cache_stats, log_cache_stats)

### Исправление иерархии XLSXWriter
Исправлено наследование:
- **XLSXWriter** теперь наследуется от FileWriter, а не от CSVWriter
- Устранено нарушение LSP

### Оптимизация common.py
Удаление переэкспорта для устранения путаницы:
- Удалён переэкспорт функций из utils/
- Сохранены только базовые утилиты (report_from_validation_error, unwrap_dot_dict, floor_to_hundreds)
- Константы переэкспортируются из constants.py

## Основные изменения в версии 2.0.0

### Новый пакет utils/
Централизация общих утилит для устранения "utils hell" в common.py:
- **decorators.py** - Декораторы ожидания (`wait_until_finished`, `async_wait_until_finished`)
- **url_utils.py** - Генерация URL (`generate_category_url`, `generate_city_urls`, `url_query_encode`)
- **sanitizers.py** - Санитаризация данных (`_sanitize_value`, `_is_sensitive_key`)
- **validation_utils.py** - Валидация городов и категорий

### Новый пакет validation/
Объединение модулей валидации для устранения путаницы:
- **url_validator.py** - Валидация URL
- **data_validator.py** - Валидация данных (int, float, строки, списки, email, phone)
- **path_validator.py** - Валидация путей (PathValidator)
- **legacy.py** - Обратная совместимость

### Рефакторинг parallel/
Разделение parallel_parser.py на подмодули:
- **parallel_parser.py** - Параллельный парсинг (1138 строк, было 2130)
- **file_merger.py** - Слияние CSV файлов (444 строки)
- **temp_file_timer.py** - Очистка временных файлов (394 строки)
- **progress_tracker.py** - Отслеживание прогресса (18 строк)

### Рефакторинг writer/writers/
Разделение CSVWriter на компоненты:
- **csv_writer.py** - Базовая запись CSV (364 строки, было 1203)
- **csv_buffer_manager.py** - Управление буферами и mmap (460 строк)
- **csv_deduplicator.py** - Дедупликация через хеширование (223 строки)
- **csv_post_processor.py** - Постобработка (удаление колонок, рубрики) (315 строк)

### Улучшения protocols.py
- Объединение с interfaces.py
- Добавлен LoggerProtocol
- Все Protocol в одном модуле

### Оптимизация common.py
- Сокращён с 1207 до 265 строк (−78%)
- Переэкспорт функций из utils/ для обратной совместимости
- Сохранены только базовые утилиты

## Зависимости между компонентами

```
┌─────────────┐     ┌─────────────┐
│   main.py   │────▶│   config.py │
└─────────────┘     └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  runner/    │────▶│  parser/    │
└─────────────┘     └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  chrome/    │◀────│   writer/   │
└─────────────┘     └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  logger/    │     │   cache/    │
└─────────────┘     └─────────────┘
       ▲
       │
┌─────────────┐
│   utils/    │
└─────────────┘
```

## Паттерны проектирования

### Фабричный метод (Factory Method)
- `get_parser()` в `parser/factory.py`
- `get_writer()` в `writer/factory.py`

### Одиночка (Singleton)
- `CacheManager` - единый экземпляр для кэширования
- `SignalHandler` - глобальный обработчик сигналов
- `PathValidator` - валидатор путей (через `get_path_validator()`)

### Стратегия (Strategy)
- Различные парсеры (`FirmParser`, `InBuildingParser`, `MainParser`)
- Различные writers (`CSVWriter`, `XLSXWriter`, `JSONWriter`)

### Контекстный менеджер (Context Manager)
- `FileMerger` - гарантия очистки временных файлов
- `ChromeBrowser` - гарантия закрытия браузера

### Пул объектов (Object Pool)
- `_ConnectionPool` в `cache.py` - пул SQLite соединений (5-20 соединений)

### Protocol (Structural Subtyping)
- `Writer`, `Parser` в `protocols.py`
- `ProgressCallback`, `LogCallback`, `CleanupCallback` в `protocols.py`
- `LoggerProtocol` в `protocols.py`

## Иерархия исключений

```
Exception
└── BaseContextualException (parser_2gis/exceptions.py)
    ├── ChromeException (parser_2gis/chrome/exceptions.py)
    │   ├── ChromeRuntimeException
    │   ├── ChromeUserAbortException
    │   └── ChromePathNotFound
    ├── ParserException (parser_2gis/parser/exceptions.py)
    └── WriterUnknownFileFormat (parser_2gis/writer/exceptions.py)
```

**Особенности BaseContextualException:**
- Автоматическое извлечение имени функции
- Номер строки где произошла ошибка
- Имя файла
- Полная трассировка стека

## Принципы проектирования

### SOLID
- **Single Responsibility**: Достигнуто через разделение на подмодули (parallel/, utils/, validation/, writer/writers/)
- **Open/Closed**: Factory pattern для парсеров и writers
- **Liskov Substitution**: Все исключения наследуются от BaseContextualException
- **Interface Segregation**: Protocol классы в protocols.py
- **Dependency Inversion**: Использование Protocol для разрыва зависимостей

### DRY
- Централизованные константы в constants.py
- Общая функция `validate_env_int()` в constants.py
- Переэкспорт функций через utils/ и validation/

### KISS
- Упрощённая структура модулей
- Прямые импорты вместо сложных абстракций
- Минимальное количество уровней наследования

### YAGNI
- Удаление неиспользуемого кода
- Ленивые импорты для опциональных зависимостей

## Модульность и связность

### Низкая связность (Low Coupling)
- utils/ не зависит от бизнес-логики
- validation/ независим от parser/writer
- constants.py не импортирует другие модули

### Высокая автономность (High Cohesion)
- Каждый модуль имеет одну ответственность
- Чёткие границы между слоями
- Минимальное количество импортов

## Масштабируемость

### Горизонтальное масштабирование
- Параллельный парсинг до 20 потоков
- Изолированные экземпляры браузера
- Разделение файлов результатов

### Вертикальное масштабирование
- Оптимизированная буферизация (256KB стандартная, 1MB для больших файлов)
- mmap для файлов >10MB
- Connection pool для SQLite (5-20 соединений)

## Тестирование

### Architecture Tests
- `test_architecture_refactoring.py` - Тесты рефакторинга (18 тестов)
- `test_module_boundaries.py` - Границы модулей (17 тестов)
- `test_architecture_integrity.py` - Целостность архитектуры (7 тестов)
- `test_architecture_layers.py` - Слои архитектуры (19 тестов)
- `test_cyclic_dependencies.py` - Циклические зависимости
- `test_architecture_constraints.py` - Архитектурные ограничения (11 тестов)

### Покрытие
- 1418 автоматических тестов
- 85%+ покрытие кода
- Unit, integration, architecture tests

## Безопасность

### Валидация данных
- Проверка глубины вложенности структур (MAX_DATA_DEPTH=100)
- Ограничение размера данных (MAX_DATA_SIZE=10MB)
- Проверка на SQL injection в кэше
- Валидация JavaScript кода

### Защита от DoS
- Лимиты на размер коллекций
- Ограничение длины строк (MAX_STRING_LENGTH=10000)
- Контроль глубины рекурсии

## Производительность

### Оптимизации
- lru_cache для часто вызываемых функций (2048 записей)
- Компилированные regex паттерны
- Пакетная запись данных (до 1000 записей)
- mmap для больших файлов (>10MB)
- Connection pooling для SQLite

### Буферизация
- DEFAULT_BUFFER_SIZE = 256KB
- MERGE_BUFFER_SIZE = 256KB
- CSV_BATCH_SIZE = 1000 строк
- HASH_BATCH_SIZE = 1000 строк

## Расширяемость

### Добавление нового парсера
1. Создать класс наследуясь от базового парсера
2. Реализовать методы парсинга
3. Зарегистрировать в фабрике парсеров

### Добавление нового формата вывода
1. Создать класс наследуясь от FileWriter
2. Реализовать метод write()
3. Зарегистрировать в фабрике writers

### Добавление новой утилиты
1. Создать модуль в utils/
2. Добавить экспорт в utils/__init__.py
3. Импортировать в нужных модулях

## Миграции

### Версия 2.0.0 (текущая)
- Создан пакет `utils/` с утилитами из common.py
- Создан пакет `validation/` из validation.py, validators.py, validator.py
- Разделён `parallel_parser.py` на подмодули
- Разделён `csv_writer.py` на компоненты
- Объединены `protocols.py` и `interfaces.py`
- Удалён `interfaces.py`
- Сокращён `common.py` с 1207 до 265 строк
- Добавлены тесты на архитектурную целостность (35 тестов)

### Версия 1.4.0
- Добавлен модуль `interfaces.py` с `LoggerProtocol`
- Добавлен модуль `validators.py` с `PathValidator`
- Улучшена архитектура: устранены циклические зависимости

## Ссылки

- [README.md](README.md) - Основная документация
- [SECURITY.md](SECURITY.md) - Политика безопасности
- [LICENSE](LICENSE) - Лицензия LGPLv3+
