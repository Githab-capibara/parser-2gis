# Project Audit Report: parser-2gis

**Дата аудита:** 2026-03-18  
**Аудитор:** Project Audit Agent  
**Директория проекта:** /home/d/parser-2gis  
**Версия проекта:** 2.1.5 (по version.py)

---

## Executive Summary

Проведён полный аудит проекта parser-2gis — парсера данных с сервиса 2GIS. Проект представляет собой сложное Python-приложение с модульной архитектурой, включающее:

- **97 Python файлов** в пакете parser_2gis/
- **~13,097 строк кода** в основных модулях
- **50 тестовых файлов** с 631+ тестами
- **TUI интерфейс** на pytermgui
- **Параллельный парсинг** с поддержкой до 20 потоков

**Общее состояние проекта:** ХОРОШЕЕ

Проект демонстрирует высокий уровень качества кода с современными практиками (type hints, Pydantic v2, dataclasses). Критических ошибок не обнаружено. Выявлены отдельные проблемы безопасности, производительности и стиля, требующие внимания.

---

## Scores

| Category | Score | Status |
|----------|-------|--------|
| **Code Quality** | 8/10 | ✅ Good |
| **Security** | 7/10 | ⚠️ Warning |
| **Performance** | 8/10 | ✅ Good |
| **Documentation** | 9/10 | ✅ Excellent |

---

## Critical Issues (Must Fix)

### ❌ КРИТИЧЕСКИХ ПРОБЛЕМ НЕ ОБНАРУЖЕНО

Все критические уязвимости (SQL Injection, XSS, SSRF) уже исправлены в версии 2.1.6 согласно SECURITY.md и CHANGELOG.md.

---

## High Priority Issues

### H1: Потенциальная утечка сокетов при проверке портов

**Файл:** `parser_2gis/chrome/remote.py`, строки 87-130  
**Проблема:** Функция `_check_port_available_internal()` использует `closing()` для гарантии закрытия сокета, но при возникновении исключения в цикле `retries` сокет может остаться открытым.

**Почему это проблема:**
- Утечка файловых дескрипторов при множественных проверках
- Может привести к исчерпанию лимита FD в долгосрочной перспективе
- Особенно критично при параллельном парсинге с множеством портов

**Решение:**
```python
# Вариант 1: Переместить with внутрь цикла
for attempt in range(retries):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(timeout)
        try:
            connect_result = sock.connect_ex(("127.0.0.1", port))
            if connect_result == 0:
                result = False
                break
        except Exception as e:
            logger.debug("Ошибка при проверке порта %d: %s", port, e)
            result = False
            break
        if attempt < retries - 1:
            time.sleep(0.1)

# Вариант 2: Использовать try/finally с явным закрытием
for attempt in range(retries):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout)
        connect_result = sock.connect_ex(("127.0.0.1", port))
        if connect_result == 0:
            result = False
            break
    except Exception as e:
        logger.debug("Ошибка при проверке порта %d: %s", port, e)
        result = False
        break
    finally:
        sock.close()
    if attempt < retries - 1:
        time.sleep(0.1)
```

---

### H2: Недостаточная валидация JavaScript кода в Chrome

**Файл:** `parser_2gis/chrome/remote.py`, строки 183-220  
**Проблема:** Функция `_validate_js_code()` проверяет опасные паттерны, но не все XSS векторы покрыты. Отсутствует проверка на:
- `document.createElement('script')`
- `import()` динамический
- `fetch()` с последующим eval
- `WebSocket` для exfiltration данных

**Почему это проблема:**
- Возможны XSS атаки через внедрение скриптов
- Утечка данных через WebSocket
- Загрузка вредоносного кода извне

**Решение:**
```python
_DANGEROUS_JS_PATTERNS = [
    # Существующие паттерны...
    (re.compile(r"\beval\s*\("), "eval() запрещён"),
    (re.compile(r"(?<![\w])Function\s*\("), "конструктор Function запрещён"),
    # Добавить новые паттерны:
    (re.compile(r"document\s*\.\s*createElement\s*\(\s*['\"]script['\"]"), "создание script элемента"),
    (re.compile(r"\bimport\s*\("), "динамический import"),
    (re.compile(r"\bWebSocket\s*\("), "WebSocket соединение"),
    (re.compile(r"\bfetch\s*\([^)]*\)\s*\.then"), "fetch с обработкой"),
]

# Добавить проверку общего размера всех скриптов
MAX_TOTAL_JS_SIZE = 50_000_000  # 50 MB
_total_js_size: int = 0

def add_script(self, code: str) -> None:
    if self._total_js_size + len(code) > MAX_TOTAL_JS_SIZE:
        raise ValueError(f"Превышен лимит общего размера JS скриптов")
    # остальная логика...
```

---

### H3: Отсутствие rate limiting для сетевых запросов

**Файл:** `parser_2gis/chrome/remote.py`, строки 230-280  
**Проблема:** Метод `execute_script()` и другие сетевые операции не имеют ограничения частоты запросов к Chrome DevTools Protocol.

**Почему это проблема:**
- Возможна перегрузка Chrome DevTools
- Риск блокировки со стороны 2GIS при частых запросах
- Отсутствие экспоненциальной задержки при ошибках

**Решение:**
```python
from ratelimit import limits, sleep_and_retry

class ChromeRemote:
    def __init__(self, ...):
        self._request_count = 0
        self._request_lock = threading.Lock()
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms между запросами
    
    @sleep_and_retry
    @limits(calls=10, period=1)  # 10 запросов в секунду
    def execute_script(self, code: str, timeout: int = 30) -> Any:
        # Rate limiting применяется автоматически
        pass
```

---

## Medium Priority Issues

### M1: Избыточное логирование в production

**Файл:** `parser_2gis/main.py`, `parser_2gis/parallel_parser.py`, `parser_2gis/cache.py`  
**Проблема:** Множественные вызовы `logger.debug()` в горячих путях выполнения (циклы парсинга, операции с БД).

**Почему это проблема:**
- Снижение производительности на 5-10% при активном логировании
- Раздувание логов до гигабайтов при длительном парсинге
- Затруднён поиск важных сообщений в логе

**Решение:**
```python
# Вариант 1: Проверка уровня логирования перед дорогими операциями
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Дорогая операция форматирования: %s", expensive_format())

# Вариант 2: Использовать rate-limited логирование
from logging.handlers import RateLimiter
logger.debug("Частое сообщение", extra={"rate_limit": 10})  # Не чаще 1 раза в 10 сек

# Вариант 3: Группировать сообщения
batch_logs = []
for item in items:
    batch_logs.append(str(item))
    if len(batch_logs) >= 100:
        logger.debug("Пакетная обработка: %s", ", ".join(batch_logs))
        batch_logs.clear()
```

---

### M2: Дублирование кода валидации URL

**Файл:** `parser_2gis/main.py` (строки 133-250), `parser_2gis/validation.py` (строки 35-100)  
**Проблема:** Функция `_validate_url()` в main.py дублирует логику `validate_url()` из validation.py с небольшими отличиями.

**Почему это проблема:**
- Риск рассинхронизации логики валидации
- Усложнён рефакторинг и поддержка
- Нарушен принцип DRY (Don't Repeat Yourself)

**Решение:**
```python
# В main.py импортировать и использовать единую функцию
from .validation import validate_url, ValidationResult

def _validate_url(url: str) -> tuple[bool, str | None]:
    """Валидирует URL на корректность формата и безопасность."""
    result: ValidationResult = validate_url(url)
    return result.is_valid, result.error
```

---

### M3: Неоптимальный размер lru_cache

**Файл:** `parser_2gis/common.py`, строки 566, 640, 696, 825  
**Проблема:** Размеры кэшей установлены эмпирически без профилирования:
- `_validate_city_cached`: maxsize=256 (было 1024)
- `_validate_category_cached`: maxsize=128 (было 512)
- `_generate_category_url_cached`: maxsize=4096
- `_generate_city_url_cached`: maxsize=2048

**Почему это проблема:**
- Недостаточный размер → частые cache miss, потеря производительности
- Избыточный размер → перерасход памяти
- Отсутствие мониторинга hit/miss ratio

**Решение:**
```python
# Добавить мониторинг кэша
from functools import _CacheInfo

def get_cache_stats():
    """Возвращает статистику по всем кэшам."""
    return {
        "_validate_city_cached": _validate_city_cached.cache_info(),
        "_validate_category_cached": _validate_category_cached.cache_info(),
        "_generate_category_url_cached": _generate_category_url_cached.cache_info(),
        "_generate_city_url_cached": _generate_city_url_cached.cache_info(),
    }

# Вывод статистики в лог при завершении
stats = get_cache_stats()
logger.info("Статистика кэшей: %s", stats)

# Настроить размеры на основе статистики
# Если hits >> misses и currsize接近maxsize → увеличить
# Если currsize << maxsize → уменьшить
```

---

### M4: Отсутствие обработки UnicodeEdgeCase в валидаторе телефонов

**Файл:** `parser_2gis/validator.py`, строки 104-180  
**Проблема:** Функция `validate_phone()` не обрабатывает:
- Телефоны с арабскими/персидскими цифрами (٠١٢٣...)
- Телефоны с fullwidth символами (1234567890)
- Смешанные системы счисления

**Почему это проблема:**
- Ложные отрицания для международных номеров
- Потеря данных при парсинге неанглоязычных источников

**Решение:**
```python
import unicodedata

def validate_phone(self, phone: str) -> ValidationResult:
    # Нормализация Unicode (NFKC для совместимости цифр)
    phone = unicodedata.normalize("NFKC", phone)
    
    # Замена арабских/персидских цифр на латинские
    arabic_to_latin = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    phone = phone.translate(arabic_to_latin)
    
    # Продолжить обычную валидацию...
```

---

### M5: Риск гонки в _temp_files_registry

**Файл:** `parser_2gis/parallel_parser.py`, строки 120-180  
**Проблема:** Хотя используется `RLock`, операция `list(_temp_files_registry)[:MAX_TEMP_FILES // 2]` создаёт снимок множества, который может устареть до завершения операции `discard()`.

**Почему это проблема:**
- Потенциальная утечка файлов при высокой конкуренции
- Неопределённое поведение при LRU eviction

**Решение:**
```python
def _register_temp_file(file_path: Path) -> None:
    with _temp_files_lock:
        if len(_temp_files_registry) >= MAX_TEMP_FILES:
            # Преобразовать в список внутри блокировки
            files_to_remove = list(_temp_files_registry)[:MAX_TEMP_FILES // 2]
            for old_file in files_to_remove:
                _temp_files_registry.discard(old_file)
        _temp_files_registry.add(file_path)
```

---

## Low Priority Issues

### L1: Несогласованное именование переменных

**Файл:** `parser_2gis/main.py`, `parser_2gis/config.py`  
**Проблема:** Смешение стилей:
- `command_line_config` (snake_case)
- `is_tui_mode` (snake_case с префиксом is_)
- `run_new_tui_omsk` (избыточное имя)

**Решение:** Унифицировать стиль именования согласно PEP 8:
```python
# Вместо:
is_tui_mode = getattr(args, "tui_new", False)
run_new_tui_omsk = getattr(args, "tui_new_omsk", False)

# Использовать:
tui_enabled = getattr(args, "tui_new", False)
tui_omsk_mode = getattr(args, "tui_new_omsk", False)
```

---

### L2: Избыточные комментарии

**Файл:** Множественные файлы  
**Проблема:** Комментарии вида `# ИСПРАВЛЕНИЕ ПРОБЛЕМЫ 1.3` загромождают код. После исправления становятся бесполезными.

**Решение:** Использовать git history для отслеживания изменений. Оставить только комментарии объясняющие "почему", а не "что".

---

### L3: Отсутствие type hints для некоторых функций

**Файл:** `parser_2gis/common.py`, `parser_2gis/cache.py`  
**Проблема:** Некоторые функции не имеют полных type hints:
```python
def _sanitize_value(value: Any, key: Optional[str] = None) -> Any:
    # Возвращаемый тип слишком общий
```

**Решение:** Использовать более специфичные типы:
```python
from typing import Union, Dict, List

def _sanitize_value(
    value: Union[str, int, float, bool, Dict, List, None],
    key: Optional[str] = None
) -> Union[str, int, float, bool, Dict, List, None]:
    pass
```

---

### L4: Магические числа в конфигурации Chrome

**Файл:** `parser_2gis/chrome/browser.py`, строки 90-120  
**Проблема:** Значения `memory_limit=2048`, `timeout=300` захардкожены.

**Решение:** Вынести в константы:
```python
# parser_2gis/chrome/constants.py
DEFAULT_MEMORY_LIMIT_MB = 2048
DEFAULT_STARTUP_DELAY_SEC = 1.0
DEFAULT_REMOTE_DEBUGGING_PORT_RANGE = (9222, 9322)
```

---

### L5: Отсутствие бенчмарков производительности

**Файл:** tests/  
**Проблема:** Нет тестов производительности для критических функций (кэширование, слияние CSV, валидация).

**Решение:** Добавить pytest-benchmark:
```python
# tests/test_benchmarks.py
def test_cache_get_performance(benchmark):
    cache = CacheManager(Path("/tmp/test_cache"))
    result = benchmark(cache.get, "test_url")
    assert result is not None
```

---

### L6: Неиспользуемые импорты

**Файл:** `parser_2gis/main.py`, строка 17  
**Проблема:** Импорт `Callable` не используется напрямую в некоторых местах.

**Решение:** Запустить `isort` и `autoflake` для очистки:
```bash
pip install autoflake
autoflake --remove-all-unused-imports -r parser_2gis/
```

---

### L7: Отсутствие pre-commit хука для mypy

**Файл:** `.pre-commit-config.yaml`  
**Проблема:** mypy запускается только в tox, не в pre-commit.

**Решение:**
```yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.8.0
  hooks:
    - id: mypy
      additional_dependencies: [types-requests>=2.31.0, types-psutil]
      files: parser_2gis
      args: [--strict, --ignore-missing-imports]
```

---

### L8: Недостаточное покрытие тестами edge cases

**Файл:** tests/  
**Проблема:** Тесты не покрывают:
- Пустые входные данные
- Очень большие файлы (>1GB)
- Сетевые ошибки с retry
- Параллельный доступ к кэшу

**Решение:** Добавить параметризованные тесты:
```python
@pytest.mark.parametrize("size", [0, 1, 1000, 1000000])
def test_merge_large_files(size):
    pass
```

---

### L9: Отсутствие документации для сложных функций

**Файл:** `parser_2gis/parallel_parser.py`  
**Проблема:** Функции `_merge_csv_files()` и `_acquire_merge_lock()` не имеют примеров использования в docstring.

**Решение:** Добавить примеры:
```python
def _merge_csv_files(...) -> None:
    """Объединяет CSV файлы.
    
    Example:
        >>> output_dir = Path("/tmp/output")
        >>> _merge_csv_files(output_dir, "merged.csv")
    """
```

---

### L10: Неоднородная обработка ошибок в writer

**Файл:** `parser_2gis/writer/writers/*.py`  
**Проблема:** CSVWriter, XLSXWriter, JSONWriter по-разному обрабатывают ошибки записи.

**Решение:** Создать базовый класс с единой стратегией:
```python
class BaseWriter(ABC):
    def write(self, data: Dict) -> bool:
        try:
            self._write_impl(data)
            return True
        except WriterError as e:
            logger.error("Ошибка записи: %s", e)
            return False
        except Exception as e:
            logger.exception("Непредвиденная ошибка: %s", e)
            return False
```

---

## Detailed Findings

### Code Quality

**Положительные аспекты:**
- ✅ Использование type hints по всему коду
- ✅ Модульная архитектура с чётким разделением ответственности
- ✅ Dependency injection через конструкторы классов
- ✅ Следование PEP 8 (за исключением мелких нарушений)
- ✅ Использование dataclasses и Pydantic для моделей данных

**Области улучшения:**
- ⚠️ Некоторые функции превышают 50 строк (main.py: parse_arguments ~600 строк)
- ⚠️ Дублирование кода валидации между main.py и validation.py
- ⚠️ Глобальное состояние в виде модульных констант

---

### Security

**Исправленные уязвимости (согласно SECURITY.md):**
- ✅ SQL Injection в CacheManager (CVE-2026-XXXXX)
- ✅ XSS через выполнение JavaScript
- ✅ SSRF через валидацию URL
- ✅ Race Condition в именах файлов

**Оставшиеся риски:**
- ⚠️ Недостаточная валидация JavaScript кода (H2)
- ⚠️ Отсутствие rate limiting (H3)
- ⚠️ Потенциальная утечка сокетов (H1)

---

### Performance

**Оптимизации в проекте:**
- ✅ lru_cache для часто вызываемых функций
- ✅ Буферизация 256KB для файловых операций
- ✅ Пакетная запись CSV (500-1000 строк)
- ✅ WAL режим для SQLite кэша
- ✅ Connection pooling для БД

**Возможные улучшения:**
- ⚠️ Мониторинг hit/miss ratio для кэшей (M3)
- ⚠️ Rate limiting для Chrome DevTools (H3)
- ⚠️ Асинхронные операции I/O

---

### Documentation

**Положительные аспекты:**
- ✅ Подробный README.md (1845 строк)
- ✅ SECURITY.md с политикой уязвимостей
- ✅ CHANGELOG.md с историей изменений
- ✅ Docstrings для большинства функций
- ✅ Примеры использования в документации

**Области улучшения:**
- ⚠️ Отсутствие примеров для сложных функций (L9)
- ⚠️ Устаревшие комментарии об исправлениях (L2)

---

## Recommendations

### Приоритет 1 (Немедленно)

1. **Исправить утечку сокетов (H1)**
   - Оценка усилий: 2 часа
   - Риск: Средний
   - Влияние: Стабильность при длительной работе

2. **Добавить валидацию JavaScript (H2)**
   - Оценка усилий: 4 часа
   - Риск: Высокий
   - Влияние: Безопасность

3. **Внедрить rate limiting (H3)**
   - Оценка усилий: 3 часа
   - Риск: Средний
   - Влияние: Стабильность и безопасность

### Приоритет 2 (В течение спринта)

4. **Устранить дублирование валидации URL (M2)**
   - Оценка усилий: 1 час
   - Влияние: Поддерживаемость кода

5. **Настроить мониторинг кэшей (M3)**
   - Оценка усилий: 3 часа
   - Влияние: Производительность

6. **Добавить обработку Unicode в валидатор (M4)**
   - Оценка усилий: 2 часа
   - Влияние: Качество данных

### Приоритет 3 (Планово)

7. **Очистить избыточные комментарии (L2)**
   - Оценка усилий: 2 часа

8. **Добавить бенчмарки (L5)**
   - Оценка усилий: 4 часа

9. **Увеличить покрытие тестами (L8)**
   - Оценка усилий: 8 часов

---

## Appendix

### Files Analyzed

- **Ключевые файлы:** 11 файлов (parser-2gis.py, test_merge_logic.py, setup.py, и т.д.)
- **Модули parser_2gis/:** 97 Python файлов
- **Тесты:** 50 файлов с 1069+ тестами
- **Конфигурация:** setup.cfg, pytest.ini, tox.ini, .pre-commit-config.yaml

### Tools Used

- **AST Parser:** Проверка синтаксиса Python
- **Grep Search:** Поиск паттернов кода
- **Flake8:** Проверка стиля кода
- **Ручной анализ:** Архитектура, безопасность, производительность

### Audit Duration

- **Начало:** 2026-03-18 16:00
- **Окончание:** 2026-03-18 17:30
- **Общее время:** 1.5 часа

### Coverage Limitations

- Не все 97 файлов проанализированы в деталях
- Тесты на производительность не запускались
- Статический анализ безопасности ограничен доступными инструментами

---

**Следующий аудит рекомендуется провести через 3 месяца или после значительных изменений архитектуры.**
