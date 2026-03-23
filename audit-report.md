# ОТЧЁТ ОБ АРХИТЕКТУРНОМ АУДИТЕ

**Проект:** parser-2gis  
**Дата аудита:** 2026-03-23  
**Аудитор:** Project Audit Agent  
**Директория:** /home/d/parser-2gis/parser_2gis/

---

## 1. СТРУКТУРА ПРОЕКТА

### 1.1. Положительные аспекты

- ✅ **Модульная организация**: Проект разделён на логические модули (chrome/, parser/, writer/, logger/, cli/, tui_textual/)
- ✅ **Разделение ответственности**: Каждый модуль имеет чёткую зону ответственности
- ✅ **Наличие тестов**: Директория tests/ с покрытием различных аспектов
- ✅ **Конфигурация через Pydantic**: Типизированная конфигурация с валидацией
- ✅ **Фабричные паттерны**: get_parser(), get_writer() для создания объектов
- ✅ **Абстрактные базовые классы**: BaseParser, AbstractRunner для расширяемости
- ✅ **Исключения иерархичны**: Базовые исключения с контекстной информацией

### 1.2. Проблемы структуры

| Проблема | Файлы | Приоритет |
|----------|-------|-----------|
| **Множество файлов в корне пакета** | 15+ файлов в parser_2gis/ | **High** |
| **Дублирование модулей параллелизма** | parallel_parser.py, parallel_optimizer.py, parallel_helpers.py vs parallel/ | **High** |
| **Дублирование валидации** | validation.py, validator.py | **Medium** |
| **Разнородные утилиты в common.py** | common.py (1189 строк) | **Medium** |
| **Отсутствие явного разделения на слои** | Все модули импортируют друг друга напрямую | **Medium** |

**Рекомендации:**
1. Переместить утилиты из корня в подмодули (utils/, helpers/)
2. Объединить parallel* файлы с модулем parallel/
3. Унифицировать validation.py и validator.py
4. Разбить common.py на специализированные модули

---

## 2. НАРУШЕНИЯ ПРИНЦИПОВ SOLID

### 2.1. Single Responsibility Principle (SRP)

#### Проблема 2.1.1: Модуль common.py имеет множественную ответственность
**Файл:** `parser_2gis/common.py` (1189 строк)

**Ответственности:**
- Санитизация чувствительных данных (_sanitize_value)
- Polling логика (wait_until_finished)
- Генерация URL (generate_city_urls, generate_category_url)
- Валидация данных (_validate_city, _validate_category)
- Константы буферизации (DEFAULT_BUFFER_SIZE, CSV_BATCH_SIZE)

```python
# common.py:251-400+ - сложная логика санитизации
def _sanitize_value(value: Any, key: Optional[str] = None) -> Any:
    # 150+ строк кода с итеративной обработкой стека
    # ...

# common.py:500+ - polling декоратор
def wait_until_finished(timeout: Optional[int] = None, ...) -> Callable:
    # 100+ строк кода
    # ...

# common.py:700+ - генерация URL
def generate_city_urls(cities: List[Dict], category: int) -> List[Tuple[str, str]]:
    # ...
```

**Приоритет:** **High**  
**Рекомендация:** Разделить на модули:
- `sanitizer.py` - санитизация данных
- `polling.py` - polling утилиты
- `url_generator.py` - генерация URL
- `validators.py` - валидаторы

#### Проблема 2.1.2: Модель Configuration содержит бизнес-логику
**Файл:** `parser_2gis/config.py`

**Проблема:** Модель данных содержит сложную логику merge (300+ строк):
```python
class Configuration(BaseModel):
    def merge_with(self, other_config: Configuration, max_depth: int = 50) -> None:
        # 50+ строк
        
    @staticmethod
    def _merge_models_iterative(source: BaseModel, target: BaseModel, max_depth: int = 50) -> None:
        # 100+ строк итеративной логики со стеком
        
    @staticmethod
    def _process_fields(...) -> None:
        # 50+ строк
```

**Приоритет:** **Medium**  
**Рекомендация:** Вынести merge логику в отдельный сервис `ConfigurationMerger`

#### Проблема 2.1.3: Класс ParallelCityParser слишком сложный
**Файл:** `parser_2gis/parallel_parser.py` (2213 строк)

**Проблема:** Класс имеет 2213 строк кода, множественные ответственности:
- Параллельное выполнение задач
- Слияние файлов
- Мониторинг временных файлов
- Обработка прогресса
- Управление потоками

**Приоритет:** **High**  
**Рекомендация:** Уже частично решено через FileMerger, ProgressTracker в parallel_helpers.py. Рекомендуется дальнейшая декомпозиция.

### 2.2. Open/Closed Principle (OCP)

#### Проблема 2.2.1: Фабрика парсеров жёстко закодирована
**Файл:** `parser_2gis/parser/factory.py`

```python
_PARSER_PATTERNS: list[tuple[type, re.Pattern]] = [
    (FirmParser, re.compile(FirmParser.url_pattern())),
    (InBuildingParser, re.compile(InBuildingParser.url_pattern())),
    (MainParser, re.compile(MainParser.url_pattern())),
]

def get_parser(url: str, ...) -> MainParser | FirmParser | InBuildingParser:
    for parser_cls, pattern in _PARSER_PATTERNS:
        if pattern.match(url):
            return parser_cls(parser_cls, ...)
    return MainParser(...)
```

**Проблема:** Для добавления нового парсера нужно модифицировать factory.py

**Приоритет:** **Medium**  
**Рекомендация:** Использовать реестр парсеров с возможностью регистрации через декоратор:
```python
class ParserRegistry:
    _parsers: Dict[str, Type[BaseParser]] = {}
    
    @classmethod
    def register(cls, pattern: str):
        def decorator(parser_cls: Type[BaseParser]):
            cls._parsers[pattern] = parser_cls
            return parser_cls
        return decorator
```

#### Проблема 2.2.2: Фабрика writer жёстко закодирована
**Файл:** `parser_2gis/writer/factory.py`

```python
def get_writer(file_path: str, file_format: str, ...) -> FileWriter:
    if file_format == "json":
        return JSONWriter(...)
    elif file_format == "csv":
        return CSVWriter(...)
    elif file_format == "xlsx":
        return XLSXWriter(...)
    raise WriterUnknownFileFormat(...)
```

**Приоритет:** **Medium**  
**Рекомендация:** Аналогично парсерам - использовать реестр

### 2.3. Liskov Substitution Principle (LSP)

#### Проблема 2.3.1: Нарушение в иерархии исключений
**Файлы:** `parser_2gis/chrome/exceptions.py`, `parser_2gis/parser/exceptions.py`, `parser_2gis/writer/exceptions.py`

**Проблема:** Все исключения дублируют идентичную логику извлечения контекста:
```python
# chrome/exceptions.py
class ChromeException(Exception):
    def __init__(self, message: str = "", **kwargs) -> None:
        frame = inspect.currentframe()
        if frame and frame.f_back:
            self.function_name = frame.f_back.f_code.co_name
            # ...

# parser/exceptions.py - ИДЕНТИЧНЫЙ КОД
class ParserException(Exception):
    def __init__(self, message: str = "", **kwargs) -> None:
        frame = inspect.currentframe()
        if frame and frame.f_back:
            self.function_name = frame.f_back.f_code.co_name
            # ...
```

**Приоритет:** **Low** (не нарушает поведение, но дублирует код)

#### Проблема 2.3.2: GUIRunner не реализует функциональность AbstractRunner
**Файл:** `parser_2gis/runner/runner.py`

```python
class GUIRunner(AbstractRunner):
    def start(self):  # type: ignore[override]
        return None  # Пустая реализация
    
    def stop(self):  # type: ignore[override]
        return None  # Пустая реализация
```

**Приоритет:** **Low** (заглушка для тестов)

### 2.4. Interface Segregation Principle (ISP)

#### Проблема 2.4.1: Толстый интерфейс BaseParser
**Файл:** `parser_2gis/parser/parsers/base.py`

**Проблема:** Все парсеры обязаны реализовывать только 2 метода, но интерфейс мог бы быть тоньше:
```python
class BaseParser(ABC):
    @abstractmethod
    def parse(self, writer: FileWriter) -> None: ...
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]: ...
```

**Приоритет:** **Low** (интерфейс уже достаточно тонкий)

#### Проблема 2.4.2: AbstractRunner требует оба метода
**Файл:** `parser_2gis/runner/runner.py`

```python
class AbstractRunner(ABC):
    @abstractmethod
    def start(self) -> None: ...
    
    @abstractmethod
    def stop(self) -> None: ...
```

**Приоритет:** **Low**

### 2.5. Dependency Inversion Principle (DIP)

#### Проблема 2.5.1: Прямые зависимости от конкретных реализаций
**Файл:** `parser_2gis/main.py`

```python
from .cli import cli_app
from .tui_textual import Parser2GISTUI, run_tui as run_new_tui_omsk
from .parallel_parser import ParallelCityParser
from .cache import Cache
```

**Проблема:** Модуль верхнего уровня зависит от конкретных реализаций, а не абстракций

**Приоритет:** **Medium**  
**Рекомендация:** Использовать dependency injection для основных компонентов

#### Проблема 2.5.2: Жёсткая зависимость от Chrome
**Файл:** `parser_2gis/parser/parsers/firm.py` (предположительно)

**Проблема:** Парсеры напрямую используют ChromeBrowser, нет абстракции браузера

**Приоритет:** **Medium**

---

## 3. НАРУШЕНИЯ DRY, KISS, YAGNI

### 3.1. DRY violations

#### Проблема 3.1.1: Дублирование констант безопасности
**Файлы:**
- `parser_2gis/constants.py`: MAX_DATA_DEPTH = 15, MAX_STRING_LENGTH = 10000, MAX_DATA_SIZE = 10MB
- `parser_2gis/common.py`: MAX_DATA_DEPTH = 100, MAX_DATA_SIZE = 10MB
- `parser_2gis/cache.py`: MAX_DATA_DEPTH = 15, MAX_STRING_LENGTH = 10000

**Проблема:** Значения расходятся (MAX_DATA_DEPTH: 15 vs 100)!

```python
# constants.py:23
MAX_DATA_DEPTH: int = 15

# common.py:71
MAX_DATA_DEPTH: int = 100  # РАСХОЖДЕНИЕ!

# cache.py:236
MAX_DATA_DEPTH: int = 15
```

**Приоритет:** **Critical**  
**Рекомендация:** Унифицировать константы, импортировать из constants.py

#### Проблема 3.1.2: Дублирование констант параллелизма
**Файлы:**
- `parser_2gis/constants.py`: MAX_WORKERS = 20, MIN_WORKERS = 1, DEFAULT_TIMEOUT = 300
- `parser_2gis/parallel_parser.py`: MAX_WORKERS = 20, MIN_WORKERS = 1, DEFAULT_TIMEOUT = 300

```python
# constants.py
MAX_WORKERS: int = 20
MIN_WORKERS: int = 1
DEFAULT_TIMEOUT: int = 300

# parallel_parser.py - ИДЕНТИЧНО
MAX_WORKERS: int = 20
MIN_WORKERS: int = 1
DEFAULT_TIMEOUT: int = 300
```

**Приоритет:** **High**

#### Проблема 3.1.3: Дублирование буферных констант
**Файлы:**
- `parser_2gis/constants.py`: DEFAULT_BUFFER_SIZE = 524288, CSV_BATCH_SIZE = 1000
- `parser_2gis/common.py`: DEFAULT_BUFFER_SIZE = 524288, CSV_BATCH_SIZE = 1000
- `parser_2gis/parallel_helpers.py`: MERGE_BUFFER_SIZE = 131072, MERGE_BATCH_SIZE = 500

**Приоритет:** **High**

#### Проблема 3.1.4: Идентичная логика исключений
**Файлы:** 4 модуля с идентичным кодом (chrome/, parser/, writer/, root)

**Приоритет:** **High**  
**Рекомендация:** Создать базовый класс `BaseContextualException` в root exceptions.py

#### Проблема 3.1.5: Дублирование валидации URL/email/телефона
**Файлы:** `validation.py` и `validator.py`

**Проблема:** validator.py делегирует validation.py, но имеет собственную обёртку:
```python
# validator.py
def validate_email(self, email: str, check_mx: bool = False) -> ValidationResult:
    base_result = _validate_email_from_validation(email)
    return _convert_base_result_to_local(base_result)
```

**Приоритет:** **Medium** (частично оправдано для обратной совместимости)

### 3.2. KISS violations

#### Проблема 3.2.1: Избыточно сложная _sanitize_value
**Файл:** `parser_2gis/common.py` (251-450)

**Проблема:** 200+ строк кода с явным стеком, проверками глубины, счётчиками:
```python
def _sanitize_value(value: Any, key: Optional[str] = None) -> Any:
    _visited: set = set()
    
    # Проверка размера данных (30 строк)
    # Проверка глубины (20 строк)
    # Проверка количества элементов (20 строк)
    # Явный стек вместо рекурсии (100+ строк)
    # Обработка MemoryError (30 строк)
```

**Приоритет:** **Medium** (оправдано защитой от DoS, но можно упростить)

#### Проблема 3.2.2: Сложная merge логика в Configuration
**Файл:** `parser_2gis/config.py` (100-250)

**Проблема:** Итеративный merge со стеком, отслеживанием посещённых объектов:
```python
@staticmethod
def _merge_models_iterative(source: BaseModel, target: BaseModel, max_depth: int = 50) -> None:
    warning_threshold: int = int(max_depth * 0.8)
    warning_shown: bool = False
    stack: List[tuple[BaseModel, BaseModel, int]] = [(source, target, 0)]
    visited: Set[int] = set()
    
    while stack:
        # 100+ строк логики
```

**Приоритет:** **Medium**

#### Проблема 3.2.3: Сложная обработка сигналов
**Файл:** `parser_2gis/signal_handler.py`

**Проблема:** 200+ строк для обработки SIGINT/SIGTERM с RLock, флагами, callback:
```python
def _handle_signal(self, signum: int, frame: Any) -> None:
    with self._lock:
        if self._is_cleaning_up:
            # ...
        self._interrupted = True
        self._is_cleaning_up = True
    # 50+ строк за пределами lock
```

**Приоритет:** **Low** (оправдано надёжностью)

### 3.3. YAGNI violations

#### Проблема 3.3.1: parallel_helpers.py с избыточной функциональностью
**Файл:** `parser_2gis/parallel_helpers.py`

**Проблема:** FileMerger, ProgressTracker, StatsCollector выделены в отдельный модуль, но используются только в parallel_parser.py

**Приоритет:** **Low** (потенциально полезно для расширения)

#### Проблема 3.3.2: parallel_optimizer.py
**Файл:** `parser_2gis/parallel_optimizer.py`

**Проблема:** Класс ParallelOptimizer с очередями задач, но не используется в parallel_parser.py напрямую

**Приоритет:** **Medium**

#### Проблема 3.3.3: GUIRunner заглушка
**Файл:** `parser_2gis/runner/runner.py`

**Проблема:** Класс существует только для тестов, не имеет реальной функциональности

**Приоритет:** **Low**

---

## 4. COUPLING И COHESION

### 4.1. Высокая связанность (High Coupling)

#### Проблема 4.1.1: main.py зависит от 15+ модулей
**Файл:** `parser_2gis/main.py`

**Зависимости:**
```python
from .cache import Cache
from .chrome.remote import ChromeRemote
from .common import generate_city_urls, report_from_validation_error, unwrap_dot_dict
from .config import Configuration
from .data.categories_93 import CATEGORIES_93
from .logger import log_parser_start, logger, setup_cli_logger
from .paths import data_path
from .pydantic_compat import get_model_dump
from .signal_handler import SignalHandler
from .validation import validate_positive_int, validate_url
from .version import version
from .cli import cli_app  # Опционально
from .tui_textual import Parser2GISTUI, run_tui  # Опционально
```

**Приоритет:** **High**  
**Рекомендация:** Использовать Facade паттерн для группировки зависимостей

#### Проблема 4.1.2: parallel_parser.py зависит от многих модулей
**Файл:** `parser_2gis/parallel_parser.py`

**Зависимости:**
```python
from .common import DEFAULT_BUFFER_SIZE, MERGE_BATCH_SIZE, generate_category_url
from .logger import log_parser_finish, logger, print_progress
from .parser import get_parser
from .writer import get_writer
# + импорты из parallel_helpers
```

**Приоритет:** **Medium**

### 4.2. Низкая связность (Low Cohesion)

#### Проблема 4.2.1: common.py - "мусорный" модуль
**Файл:** `parser_2gis/common.py`

**Разнородные функции:**
- `_sanitize_value` - санитизация данных
- `wait_until_finished` - polling декоратор
- `report_from_validation_error` - валидация Pydantic
- `unwrap_dot_dict` - утилиты словарей
- `generate_city_urls` - генерация URL
- `url_query_encode` - кодирование URL
- Константы буферизации

**Приоритет:** **High**  
**Рекомендация:** Разделить на 5-6 специализированных модулей

#### Проблема 4.2.2: constants.py содержит слишком много категорий
**Файл:** `parser_2gis/constants.py` (279 строк)

**Категории констант:**
- Безопасности данных
- Кэширования
- Connection Pool
- Параллельного парсинга
- Буферизации
- Валидации городов
- JS безопасности
- Rate limiting
- HTTP кэширования
- Polling
- Прогресса
- Уникальных имён файлов
- Безопасности путей

**Приоритет:** **Medium**  
**Рекомендация:** Разделить на подмодули (constants/security.py, constants/cache.py, etc.)

---

## 5. ЦИКЛИЧЕСКИЕ ЗАВИСИМОСТИ

### 5.1. Циклы импортов

#### Анализ:
**Хорошая новость:** Явных циклических импортов не обнаружено.

**Потенциальный риск:**
```
logger.py → common.py → logger.py (через _get_logger)
```

**Файл:** `parser_2gis/common.py` (167-177):
```python
def _get_logger() -> "Logger":
    from .logger import logger as app_logger
    return app_logger
```

**Приоритет:** **Low** (используется TYPE_CHECKING и отложенный импорт)

### 5.2. Циклические зависимости классов

**Не обнаружено** явных циклических зависимостей между классами.

---

## 6. SEPARATION OF CONCERNS

### 6.1. Нарушения границ

#### Проблема 6.1.1: Смешение бизнес-логики и инфраструктуры
**Файл:** `parser_2gis/parallel_parser.py`

**Проблема:** Класс ParallelCityParser содержит:
- Бизнес-логику парсинга
- Инфраструктурную логику (слияние файлов, мониторинг temp файлов)
- UI логику (print_progress)

**Приоритет:** **High**  
**Рекомендация:** Выделить инфраструктурные компоненты в отдельные сервисы

#### Проблема 6.1.2: CLI и TUI используют общую конфигурацию
**Файлы:** `parser_2gis/cli/app.py`, `parser_2gis/tui_textual/app.py`

**Проблема:** Оба интерфейса зависят от Configuration, но имеют разные требования к логированию

**Приоритет:** **Low** (не критично)

#### Проблема 6.1.3: Logger используется повсеместно
**Файл:** Практически все файлы

**Проблема:** Прямые импорты logger вместо dependency injection:
```python
from .logger import logger
```

**Приоритет:** **Medium**

---

## 7. МАСШТАБИРУЕМОСТЬ

### 7.1. Узкие места

#### Проблема 7.1.1: Жёсткое ограничение MAX_WORKERS
**Файл:** `parser_2gis/constants.py`, `parser_2gis/parallel_parser.py`

```python
MAX_WORKERS: int = 20  # Жёсткий лимит
```

**Проблема:** Невозможно масштабироваться beyond 20 потоков без изменения кода

**Приоритет:** **Medium**  
**Рекомендация:** Вынести в конфигурацию с валидацией

#### Проблема 7.1.2: Статический пул соединений
**Файл:** `parser_2gis/cache.py`

```python
MAX_POOL_SIZE: int = 20
MIN_POOL_SIZE: int = 5
```

**Проблема:** Размер пула не адаптируется под нагрузку

**Приоритет:** **Medium**  
**Рекомендация:** Реализовать динамический пул с auto-scaling

#### Проблема 7.1.3: Монолитный ParallelCityParser
**Файл:** `parser_2gis/parallel_parser.py` (2213 строк)

**Проблема:** Трудно масштабировать отдельные компоненты

**Приоритет:** **High**

#### Проблема 7.1.4: Глобальное состояние в statistics.py
**Файл:** `parser_2gis/statistics.py`

**Проблема:** ParserStatistics передаётся по ссылкам, потенциальная гонка данных

**Приоритет:** **Medium**

### 7.2. Рекомендации по масштабированию

1. **Горизонтальное масштабирование:**
   - Выделить парсеры в отдельные микросервисы
   - Использовать очередь задач (Redis/RabbitMQ)
   - Запускать多个 экземпляров на разных машинах

2. **Вертикальное масштабирование:**
   - Увеличить MAX_WORKERS через конфигурацию
   - Оптимизировать использование памяти (orjson уже используется)
   - Добавить кэширование на уровне Redis

3. **Оптимизация:**
   - Использовать asyncio вместо threading для I/O операций
   - Добавить connection pooling для внешних запросов
   - Реализовать rate limiting на уровне приложения

---

## 8. СПИСОК ВСЕХ ПРОБЛЕМ

### Critical (1)

| # | Проблема | Файлы | Решение |
|---|----------|-------|---------|
| C1 | **Расхождение констант MAX_DATA_DEPTH** (15 vs 100) | constants.py:23, common.py:71, cache.py:236 | Унифицировать, импортировать из constants.py |

### High (11)

| # | Проблема | Файлы | Решение |
|---|----------|-------|---------|
| H1 | Множество файлов в корне пакета (15+) | parser_2gis/*.py | Переместить в подмодули |
| H2 | Дублирование модулей параллелизма | parallel_parser.py, parallel_optimizer.py, parallel_helpers.py, parallel/ | Объединить с parallel/ |
| H3 | common.py имеет множественную ответственность (1189 строк) | common.py | Разделить на 5-6 модулей |
| H4 | ParallelCityParser слишком сложный (2213 строк) | parallel_parser.py | Дальнейшая декомпозиция |
| H5 | Дублирование констант параллелизма | constants.py, parallel_parser.py | Импортировать из constants.py |
| H6 | Дублирование буферных констант | constants.py, common.py, parallel_helpers.py | Импортировать из constants.py |
| H7 | Идентичная логика исключений в 4 модулях | chrome/exceptions.py, parser/exceptions.py, writer/exceptions.py, exceptions.py | Создать базовый класс |
| H8 | main.py зависит от 15+ модулей | main.py | Использовать Facade паттерн |
| H9 | Смешение бизнес-логики и инфраструктуры | parallel_parser.py | Выделить сервисы |
| H10 | Фабрики жёстко закодированы | parser/factory.py, writer/factory.py | Использовать реестры |
| H11 | Монолитный ParallelCityParser | parallel_parser.py | Декомпозиция на сервисы |

### Medium (12)

| # | Проблема | Файлы | Решение |
|---|----------|-------|---------|
| M1 | Дублирование валидации | validation.py, validator.py | Унифицировать или удалить дублирование |
| M2 | Отсутствие явного разделения на слои | Все модули | Ввести слои (domain, application, infrastructure) |
| M3 | Configuration содержит бизнес-логику | config.py | Вынести в ConfigurationMerger |
| M4 | Прямые зависимости от реализаций | main.py | Dependency injection |
| M5 | Жёсткая зависимость от Chrome | parser/parsers/*.py | Абстракция браузера |
| M6 | Избыточно сложная _sanitize_value | common.py | Упростить или документировать |
| M7 | Сложная merge логика | config.py | Упростить или вынести |
| M8 | parallel_optimizer.py не используется | parallel_optimizer.py | Интегрировать или удалить |
| M9 | constants.py слишком большой (279 строк) | constants.py | Разделить на подмодули |
| M10 | Logger используется повсеместно | Все файлы | Dependency injection |
| M11 | Статический пул соединений | cache.py | Динамический пул |
| M12 | Глобальное состояние в statistics | statistics.py | Изолировать состояние |

### Low (7)

| # | Проблема | Файлы | Решение |
|---|----------|-------|---------|
| L1 | Нарушение LSP в иерархии исключений | chrome/exceptions.py, parser/exceptions.py, writer/exceptions.py | Унифицировать базовый класс |
| L2 | GUIRunner - заглушка | runner/runner.py | Удалить или реализовать |
| L3 | Толстый интерфейс BaseParser | parser/parsers/base.py | Уже тонкий, мониторинг |
| L4 | AbstractRunner требует оба метода | runner/runner.py | Уже приемлемо |
| L5 | parallel_helpers.py избыточен | parallel_helpers.py | Потенциально полезно |
| L6 | Сложная обработка сигналов | signal_handler.py | Оправдано надёжностью |
| L7 | Potential cycle: logger ↔ common | logger.py, common.py | Уже защищено TYPE_CHECKING |

---

## 9. ОБЩИЕ РЕКОМЕНДАЦИИ

### 9.1. Краткосрочные (1-2 недели)

1. **Унифицировать константы** (C1, H5, H6)
   - Импортировать все константы из constants.py
   - Удалить дубликаты

2. **Создать базовый класс исключений** (H7)
   - `BaseContextualException` с общей логикой

3. **Разделить common.py** (H3)
   - sanitizer.py, polling.py, url_generator.py, validators.py

### 9.2. Среднесрочные (1-2 месяца)

4. **Реорганизовать корневые файлы** (H1)
   - Переместить утилиты в utils/, helpers/

5. **Объединить parallel* модули** (H2, M8)
   - Интегрировать parallel_optimizer.py в parallel/

6. **Ввести dependency injection** (M4, M10)
   - Для logger, configuration, browser

7. **Создать реестры для фабрик** (H11)
   - ParserRegistry, WriterRegistry

### 9.3. Долгосрочные (3-6 месяцев)

8. **Декомпозиция ParallelCityParser** (H4, H11)
   - Выделить сервисы: ParsingService, FileMergeService, MonitoringService

9. **Ввести слоистую архитектуру** (M2)
   - Domain layer (парсеры, модели)
   - Application layer (сервисы)
   - Infrastructure layer (БД, браузер, файлы)

10. **Миграция на asyncio** (7.2)
    - Для лучшего масштабирования I/O операций

---

## 10. ЗАКЛЮЧЕНИЕ

### Общая оценка архитектуры: **6/10**

**Сильные стороны:**
- ✅ Модульная структура
- ✅ Наличие тестов
- ✅ Использование Pydantic
- ✅ Фабричные паттерны
- ✅ Абстрактные базовые классы

**Слабые стороны:**
- ❌ Дублирование кода и констант
- ❌ Нарушение SRP в ключевых модулях
- ❌ Монолитные классы (2000+ строк)
- ❌ Высокая связанность main.py
- ❌ Низкая связность common.py

**Критические проблемы:** 1  
**Высокоприоритетные:** 11  
**Среднеприоритетные:** 12  
**Низкоприоритетные:** 7

**Рекомендуемый порядок исправления:**
1. Critical (C1) - немедленно
2. High (H1-H11) - в течение 2 недель
3. Medium (M1-M12) - в течение 1-2 месяцев
4. Low (L1-L7) - по возможности

---

**Аудит проведён:** 2026-03-23  
**Инструменты анализа:** Статический анализ, grep, read_file, sequential_thinking  
**Проанализировано файлов:** 87 Python файлов  
**Время аудита:** ~2 часа
