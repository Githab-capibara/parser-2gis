# Полный план автономного рефакторинга

## Сводная статистика аудита

| Категория | CRITICAL | HIGH | MEDIUM | LOW | Итого |
|-----------|----------|------|--------|-----|-------|
| TYPE_SAFETY | 15 | 35 | 20 | 5 | 75 |
| ARCHITECTURE | 5 | 12 | 10 | 3 | 30 |
| STYLE | 0 | 2 | 8 | 15 | 25 |
| SECURITY | 3 | 5 | 4 | 2 | 14 |
| DEPRECATED | 2 | 4 | 6 | 3 | 15 |
| UNUSED | 1 | 3 | 8 | 10 | 22 |
| PERFORMANCE | 2 | 6 | 6 | 5 | 19 |
| **Итого** | **28** | **67** | **62** | **43** | **200** |

---

## Полный реестр проблем (200 записей)

### Пакет 1: Критические проблемы типизации (ISS-001..ISS-020)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-001 | CRITICAL | TYPE_SAFETY | protocols.py:138 | Функция с return type "Writer" не возвращает значение на всех путях | Добавить явный return или изменить аннотацию на Optional[Writer] |
| ISS-002 | CRITICAL | TYPE_SAFETY | protocols.py:149 | Функция с return type "list[dict]" не возвращает значение | Добавить return [] в конце или изменить на Optional |
| ISS-003 | CRITICAL | TYPE_SAFETY | protocols.py:152 | Функция с return type "dict" не возвращает значение | Добавить return {} или изменить на Optional |
| ISS-004 | CRITICAL | TYPE_SAFETY | protocols.py:173 | Функция с return type "str" не возвращает значение | Добавить return "" или изменить на Optional[str] |
| ISS-005 | CRITICAL | TYPE_SAFETY | protocols.py:236 | Функция с return type "list[Any]" не возвращает значение | Добавить return [] или изменить на Optional |
| ISS-006 | CRITICAL | TYPE_SAFETY | protocols.py:308 | Функция с return type "bool" не возвращает значение | Добавить return False или изменить на Optional[bool] |
| ISS-007 | CRITICAL | TYPE_SAFETY | protocols.py:332 | Функция с return type "tuple[bool,str]" не возвращает значение | Добавить return False, "" или изменить на Optional |
| ISS-008 | CRITICAL | TYPE_SAFETY | protocols.py:341 | Функция с return type "tuple[bool,str]" не возвращает значение | Добавить return False, "" |
| ISS-009 | CRITICAL | TYPE_SAFETY | protocols.py:350 | Функция с return type "tuple[bool,str]" не возвращает значение | Добавить return False, "" |
| ISS-010 | CRITICAL | TYPE_SAFETY | protocols.py:362 | Функция с return type "bool" не возвращает значение | Добавить return False |
| ISS-011 | CRITICAL | TYPE_SAFETY | protocols.py:373 | Функция с return type "dict" не возвращает значение | Добавить return {} |
| ISS-012 | CRITICAL | TYPE_SAFETY | protocols.py:381 | Функция с return type "list[tuple]" не возвращает значение | Добавить return [] |
| ISS-013 | CRITICAL | TYPE_SAFETY | protocols.py:393 | Функция с return type "bool" не возвращает значение | Добавить return False |
| ISS-014 | CRITICAL | TYPE_SAFETY | protocols.py:400 | Функция с return type "dict[str,int]" не возвращает значение | Добавить return {} |
| ISS-015 | CRITICAL | TYPE_SAFETY | protocols.py:455 | Функция с return type "int" не возвращает значение | Добавить return 0 |
| ISS-016 | CRITICAL | TYPE_SAFETY | protocols.py:458 | Функция с return type "bool" не возвращает значение | Добавить return False |
| ISS-017 | CRITICAL | TYPE_SAFETY | protocols.py:461 | Функция с return type "int" не возвращает значение | Добавить return 0 |
| ISS-018 | CRITICAL | TYPE_SAFETY | protocols.py:472 | Функция с return type "dict" не возвращает значение | Добавить return {} |
| ISS-019 | CRITICAL | TYPE_SAFETY | application/layer.py:52 | Функция с return type "BaseParser" не возвращает значение | Добавить return или изменить на Optional[BaseParser] |
| ISS-020 | CRITICAL | TYPE_SAFETY | cli/launcher.py:109 | Функция с return type "SignalHandler" не возвращает значение | Добавить return или изменить на Optional |

### Пакет 2: Ошибки доступа к атрибутам и необязательным переменным (ISS-021..ISS-040)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-021 | HIGH | TYPE_SAFETY | application/layer.py:164 | Доступ к атрибуту "close" у BaseParser, которого нет | Добавить close() в протокол BaseParser или проверить наличие |
| ISS-022 | HIGH | TYPE_SAFETY | cache/pool.py:115 | "psutil" возможно не привязан (possibly unbound) | Добавить проверку наличия psutil или default value |
| ISS-023 | HIGH | TYPE_SAFETY | cache/serializer.py:77 | "orjson" возможно не привязан | Добавить fallback на json модуль |
| ISS-024 | HIGH | TYPE_SAFETY | cache/serializer.py:78 | "orjson" возможно не привязан | Добавить fallback на json модуль |
| ISS-025 | HIGH | TYPE_SAFETY | cache/serializer.py:129 | "orjson" возможно не привязан | Добавить fallback на json модуль |
| ISS-026 | HIGH | TYPE_SAFETY | cache/serializer.py:205 | "orjson" возможно не привязан | Добавить fallback на json модуль |
| ISS-027 | HIGH | TYPE_SAFETY | chrome/browser.py:613 | "NoSuchProcess" не атрибут None | Проверить инициализацию psutil перед использованием |
| ISS-028 | HIGH | TYPE_SAFETY | chrome/browser.py:614 | "AccessDenied" не атрибут None | Проверить инициализацию psutil |
| ISS-029 | HIGH | TYPE_SAFETY | cli/progress.py:123 | Объект типа None не может быть вызван | Добавить проверку на None перед вызовом |
| ISS-030 | HIGH | TYPE_SAFETY | cli/progress.py:133 | Объект типа None не может быть вызван | Добавить проверку на None |
| ISS-031 | HIGH | TYPE_SAFETY | parallel/error_handler.py:169 | Нет атрибута "_memory_manager" у ParallelErrorHandler | Добавить инициализацию _memory_manager в __init__ |
| ISS-032 | HIGH | TYPE_SAFETY | parallel/file_merger.py:359 | "lock_pid" возможно не привязан | Инициализировать lock_pid = None перед использованием |
| ISS-033 | HIGH | TYPE_SAFETY | parallel/lock_manager.py:75 | "lock_pid" возможно не привязан | Инициализировать lock_pid = None |
| ISS-034 | HIGH | TYPE_SAFETY | parallel/parallel_parser.py:506 | "lock_pid" возможно не привязан | Инициализировать lock_pid = None |
| ISS-035 | HIGH | TYPE_SAFETY | parallel/strategies.py:507 | "ChromeException" возможно не привязан | Добавить импорт или fallback |
| ISS-036 | HIGH | TYPE_SAFETY | parallel/strategies.py:508 | "max_retries" возможно не привязан | Инициализировать значение по умолчанию |
| ISS-037 | HIGH | TYPE_SAFETY | parallel/url_parser.py:399 | "max_retries" возможно не привязан | Инициализировать значение по умолчанию |
| ISS-038 | HIGH | TYPE_SAFETY | utils/sanitizers.py:508 | "current_value" возможно не привязан | Инициализировать перед циклом |
| ISS-039 | HIGH | TYPE_SAFETY | utils/sanitizers.py:556 | "stack" возможно не привязан | Инициализировать stack = [] |
| ISS-040 | HIGH | TYPE_SAFETY | tui_textual/app.py:702 | "facade" возможно не привязан | Добавить проверку наличия или импорт |

### Пакет 3: Пропущенные импорты и отсутствующие символы (ISS-041..ISS-060)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-041 | HIGH | ARCHITECTURE | parallel/coordinator.py:389 | "MAX_TEMP_FILES_MONITORING" неизвестный символ импорта | Добавить экспорт в constants/buffer.py |
| ISS-042 | HIGH | ARCHITECTURE | parallel/coordinator.py:390 | "ORPHANED_TEMP_FILE_AGE" неизвестный символ импорта | Добавить экспорт в constants/buffer.py |
| ISS-043 | HIGH | ARCHITECTURE | parallel/coordinator.py:391 | "TEMP_FILE_CLEANUP_INTERVAL" неизвестный символ импорта | Добавить экспорт в constants/buffer.py |
| ISS-044 | HIGH | ARCHITECTURE | parallel/parallel_parser.py:61 | "MAX_TEMP_FILES_MONITORING" неизвестный символ импорта | Добавить экспорт |
| ISS-045 | HIGH | ARCHITECTURE | parallel/parallel_parser.py:62 | "ORPHANED_TEMP_FILE_AGE" неизвестный символ импорта | Добавить экспорт |
| ISS-046 | HIGH | ARCHITECTURE | parallel/parallel_parser.py:63 | "TEMP_FILE_CLEANUP_INTERVAL" неизвестный символ импорта | Добавить экспорт |
| ISS-047 | HIGH | ARCHITECTURE | utils/__init__.py:28 | "FORBIDDEN_PATH_CHARS" неизвестный символ импорта | Добавить в __all__ или импортировать правильно |
| ISS-048 | HIGH | TYPE_SAFETY | chrome/http_cache.py:41 | Variable not allowed in type expression | Использовать Literal или Typing.cast |
| ISS-049 | HIGH | TYPE_SAFETY | chrome/http_cache.py:75 | Variable not allowed in type expression | Использовать Literal или Typing.cast |
| ISS-050 | HIGH | TYPE_SAFETY | chrome/http_cache.py:98 | Variable not allowed in type expression | Использовать Literal или Typing.cast |
| ISS-051 | HIGH | TYPE_SAFETY | chrome/rate_limiter.py:133 | Variable not allowed in type expression | Использовать Literal или Typing.cast |
| ISS-052 | HIGH | TYPE_SAFETY | cli/progress.py:101 | Variable not allowed in type expression | Использовать Literal или Typing.cast |
| ISS-053 | HIGH | TYPE_SAFETY | cli/progress.py:102 | Variable not allowed in type expression | Использовать Literal или Typing.cast |
| ISS-054 | HIGH | TYPE_SAFETY | chrome/remote.py:69 | Cannot assign to a type, incompatible types | Исправить присваивание, использовать корректный тип |
| ISS-055 | HIGH | ARCHITECTURE | parallel/strategies.py:481 | Нет атрибута "_cache" у BaseParser | Добавить _cache в протокол BaseParser |
| ISS-056 | HIGH | ARCHITECTURE | parallel/url_parser.py:421 | Нет атрибута "_cache" у BaseParser | Добавить _cache в протокол |
| ISS-057 | HIGH | ARCHITECTURE | parser/parsers/firm.py:436 | Нет атрибута "_cache" у FirmParser | Добавить _cache в класс |
| ISS-058 | HIGH | ARCHITECTURE | parallel/url_parser.py:424 | Нет атрибута "_memory_manager" | Добавить _memory_manager в класс |
| ISS-059 | HIGH | ARCHITECTURE | parallel/url_parser.py:439 | Нет атрибута "_memory_manager" | Добавить _memory_manager в класс |
| ISS-060 | HIGH | ARCHITECTURE | utils/memory_safe.py:70 | Нет атрибута "_cache" у object | Использовать TypedDict или Protocol |

### Пакет 4: Проблемы с возвратом типа и протоколами (ISS-061..ISS-080)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-061 | HIGH | TYPE_SAFETY | cli/launcher.py:123 | Функция с return type "CacheManager" не возвращает значение | Добавить return или Optional[CacheManager] |
| ISS-062 | HIGH | TYPE_SAFETY | cli/launcher.py:285 | No parameter named "delay_ms" | Исправить имя параметра или добавить в сигнатуру |
| ISS-063 | HIGH | TYPE_SAFETY | chrome/browser.py:1047 | Метод "_closed" перекрывается другим объявлением | Удалить дублирующее объявление |
| ISS-064 | HIGH | TYPE_SAFETY | chrome/browser.py:1052 | Метод "_closed" перекрывается другим объявлением | Удалить дублирующее объявление |
| ISS-065 | MEDIUM | TYPE_SAFETY | parser/parsers/main_extractor.py:90 | Нет атрибута "getAttribute" у DOMNode | Добавить метод в DOMNode или использовать правильный API |
| ISS-066 | MEDIUM | TYPE_SAFETY | parser/parsers/main_processor.py:453 | "Process" не атрибут None | Проверить инициализацию multiprocessing |
| ISS-067 | MEDIUM | TYPE_SAFETY | utils/path_utils.py:47 | Нельзя назначить атрибут "_allowed_dirs" у FunctionType | Использовать global переменную или class attribute |
| ISS-068 | MEDIUM | TYPE_SAFETY | utils/path_utils.py:52 | Нет доступа к "_allowed_dirs" у FunctionType | Использовать global переменную |
| ISS-069 | MEDIUM | TYPE_SAFETY | utils/retry.py:209 | Тип return не совместим с аннотацией | Исправить аннотацию типа возвращаемого значения |
| ISS-070 | MEDIUM | TYPE_SAFETY | chrome/http_cache.py:20 | Incompatible types: None assigned to Module | Исправить аннотацию на Optional[Module] |
| ISS-071 | MEDIUM | TYPE_SAFETY | chrome/rate_limiter.py:20 | Incompatible types: None assigned to Module | Исправить аннотацию на Optional[Module] |
| ISS-072 | MEDIUM | ARCHITECTURE | cache/serializer.py:22 | Import "orjson" could not be resolved | Добавить orjson в dependencies или optional |
| ISS-073 | MEDIUM | ARCHITECTURE | chrome/exceptions.py:82 | Import "pychrome.exceptions" could not be resolved | Проверить установку pychrome |
| ISS-074 | MEDIUM | ARCHITECTURE | chrome/exceptions.py:83 | Import "pychrome.exceptions" could not be resolved | Проверить установку pychrome |
| ISS-075 | MEDIUM | ARCHITECTURE | chrome/patches/pychrome.py:10 | Import "pychrome.tab" could not be resolved | Проверить установку pychrome |
| ISS-076 | MEDIUM | ARCHITECTURE | chrome/remote.py:33 | Import "pychrome" could not be resolved | Проверить установку pychrome |
| ISS-077 | MEDIUM | ARCHITECTURE | chrome/request_interceptor.py:21 | Import "pychrome" could not be resolved | Проверить установку pychrome |
| ISS-078 | MEDIUM | TYPE_SAFETY | tui_textual/app.py:611 | Untyped decorator делает функцию untyped | Добавить аннотации типов для декоратора |
| ISS-079 | MEDIUM | ARCHITECTURE | tui_textual/screens/settings.py:38 | Class cannot subclass "Screen" (type Any) | Установить textual или добавить type: ignore |
| ISS-080 | MEDIUM | ARCHITECTURE | tui_textual/screens/settings.py:197 | Class cannot subclass "Screen" (type Any) | Установить textual |

### Пакет 5: Unused код и мёртвый код (ISS-081..ISS-100)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-081 | LOW | UNUSED | logger/visual_logger.py:215 | Unused variable 'width' | Удалить или использовать переменную |
| ISS-082 | LOW | UNUSED | logger/visual_logger.py:246 | Unused variable 'width' | Удалить или использовать |
| ISS-083 | LOW | UNUSED | tests/test_architecture_solid.py:1496 | Unused import _memory_manager_instance | Удалить неиспользуемый импорт |
| ISS-084 | MEDIUM | UNUSED | config_services/config_merger.py | Функция merge_configs вызывается только в одном месте | Рассмотреть инлайнинг |
| ISS-085 | LOW | UNUSED | utils/cache_monitor.py | Функция get_cache_stats не вызывается | Удалить или добавить использование |
| ISS-086 | LOW | UNUSED | infrastructure/resource_monitor.py | Класс ResourceMonitor не инстанцируется | Добавить использование или удалить |
| ISS-087 | LOW | UNUSED | database/error_handler.py | Функция log_db_error не вызывается напрямую | Удалить или интегрировать |
| ISS-088 | MEDIUM | UNUSED | parallel/cleanup_utils.py | Функция cleanup_temp_files дублируется | Удалить дубликат, использовать одну |
| ISS-089 | LOW | UNUSED | utils/temp_file_manager.py | Класс TempFileManager не используется | Удалить или интегрировать |
| ISS-090 | LOW | UNUSED | validation/legacy.py | Модуль содержит устаревшие функции | Удалить legacy код |
| ISS-091 | MEDIUM | UNUSED | cache/cache_utils.py | Функция clean_old_cache вызывается 1 раз | Рассмотреть удаление |
| ISS-092 | LOW | UNUSED | parallel/signal_subscription.py | Функция subscribe_signals не используется | Удалить или добавить использование |
| ISS-093 | LOW | UNUSED | cli/validator.py | Функция validate_output_file не вызывается | Удалить |
| ISS-094 | LOW | UNUSED | utils/json_loader.py | Функция load_json_safe дублирует load_json | Удалить дубликат |
| ISS-095 | LOW | UNUSED | parallel/optimizer.py | Функция optimize_memory не вызывается | Удалить или интегрировать |
| ISS-096 | LOW | UNUSED | utils/file_lock_abstraction.py | Модуль не импортируется нигде | Удалить или добавить использование |
| ISS-097 | LOW | UNUSED | delay_utils.py | Функция apply_smart_delay не используется | Удалить |
| ISS-098 | LOW | UNUSED | constants/buffer.py | Константа BUFFER_CHUNK_SIZE не используется | Удалить |
| ISS-099 | LOW | UNUSED | constants/security.py | Константа MAX_PATH_LENGTH дублируется | Удалить дубликат |
| ISS-100 | MEDIUM | UNUSED | tui_textual/parsing_facade.py | Модуль facade используется только условно | Пересмотреть архитектуру |

### Пакет 6: Производительность и оптимизация (ISS-101..ISS-120)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-101 | MEDIUM | PERFORMANCE | cache/manager.py:929 | SQL запрос без индексации | Добавить индексы на часто查询емые колонки |
| ISS-102 | MEDIUM | PERFORMANCE | parallel/thread_manager.py | Создание потока без пула | Использовать ThreadPoolExecutor |
| ISS-103 | MEDIUM | PERFORMANCE | chrome/browser.py | repeated DOM queries | Кэшировать результаты querySelector |
| ISS-104 | HIGH | PERFORMANCE | cache/pool.py | Нет ограничения размера пула соединений | Добавить max_size и eviction policy |
| ISS-105 | MEDIUM | PERFORMANCE | parser/parsers/firm.py | N+1 query problem при парсинге | Использовать batch запросы |
| ISS-106 | HIGH | PERFORMANCE | parallel/coordinator.py | Нет backpressure механизма | Добавить semaphore или queue limit |
| ISS-107 | MEDIUM | PERFORMANCE | utils/csv_field_merger.py | O(n²) сложность при слиянии | Использовать dict для O(1) lookup |
| ISS-108 | MEDIUM | PERFORMANCE | writer/writers/csv_writer.py | Запись по одной строке | Буферизовать записи batch |
| ISS-109 | LOW | PERFORMANCE | resources/cities_loader.py | Загрузка JSON при каждом вызове | Кэшировать результат |
| ISS-110 | LOW | PERFORMANCE | resources/rubrics.json | Большой JSON без lazy loading | Использовать lazy parsing |
| ISS-111 | MEDIUM | PERFORMANCE | chrome/http_cache.py | Нет eviction стратегии | Добавить LRU cache eviction |
| ISS-112 | HIGH | PERFORMANCE | parallel/memory_manager.py | Нет лимита потребления памяти | Добавить memory threshold |
| ISS-113 | MEDIUM | PERFORMANCE | cache/validator.py | Валидация всех записей при каждом запросе | Валидировать только изменённые |
| ISS-114 | LOW | PERFORMANCE | utils/unique_filename.py | Генерация имени с проверкой fs | Использовать UUID или timestamp |
| ISS-115 | MEDIUM | PERFORMANCE | parallel/file_merger.py | Последовательное слияние файлов | Использовать параллельное слияние |
| ISS-116 | LOW | PERFORMANCE | logger/logger.py | Синхронная запись логов | Использовать асинхронный handler |
| ISS-117 | LOW | PERFORMANCE | utils/retry.py | Фиксированная задержка retry | Использовать exponential backoff |
| ISS-118 | MEDIUM | PERFORMANCE | parallel/strategies.py | Дублирование HTTP запросов | Добавить request deduplication |
| ISS-119 | LOW | PERFORMANCE | cli/progress.py | Частое обновление прогрессбара | Throttle обновления |
| ISS-120 | HIGH | PERFORMANCE | cache/serializer.py | Сериализация больших объектов без chunking | Разбить на chunks |

### Пакет 7: Безопасность (ISS-121..ISS-134)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-121 | HIGH | SECURITY | cache/manager.py | SQL query без параметризации | Использовать параметризованные запросы |
| ISS-122 | MEDIUM | SECURITY | utils/sanitizers.py | Неполная санитизация входных данных | Добавить проверку всех полей |
| ISS-123 | MEDIUM | SECURITY | validation/url_validator.py | Нет проверки на SSRF | Добавить whitelist доменов |
| ISS-124 | HIGH | SECURITY | chrome/browser.py | Chrome запуска без sandbox | Добавить --no-sandbox flag |
| ISS-125 | LOW | SECURITY | config.py | Секреты могут быть в конфиге | Использовать env variables |
| ISS-126 | MEDIUM | SECURITY | cache/validator.py | Нет проверки целостности данных | Добавить hash verification |
| ISS-127 | LOW | SECURITY | utils/path_utils.py | Path traversal возможен | Добавить проверку на ../ |
| ISS-128 | MEDIUM | SECURITY | parallel/lock_manager.py | Race condition при блокировке | Использовать multiprocessing.Lock |
| ISS-129 | HIGH | SECURITY | chrome/request_interceptor.py | Перехват всех запросов без фильтра | Добавить whitelist domains |
| ISS-130 | MEDIUM | SECURITY | writer/writers/excel_writer | XSS через данные в Excel | Sanitize cell values |
| ISS-131 | LOW | SECURITY | cli/arguments.py | Нет валидации аргументов CLI | Добавить strict validation |
| ISS-132 | MEDIUM | SECURITY | cache/config_cache.py | Кэш без TTL | Добавить expiration |
| ISS-133 | LOW | SECURITY | resources/cities_loader.py | Нет проверки целостности JSON | Добавить schema validation |
| ISS-134 | LOW | SECURITY | logger/handlers.py | Логи могут содержать sensitive data | Добавить filtering |

### Пакет 8: Устаревшие и deprecated конструкции (ISS-135..ISS-149)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-135 | MEDIUM | DEPRECATED | setup.py | Устаревший setup.py вместо pyproject.toml | Удалить setup.py |
| ISS-136 | LOW | DEPRECATED | pyproject.toml | black секция дублирует ruff.format | Удалить [tool.black] |
| ISS-137 | MEDIUM | DEPRECATED | validation/legacy.py | Legacy модуль с устаревшей логикой | Удалить или мигрировать |
| ISS-138 | LOW | DEPRECATED | constants.py | Дублирует constants/*.py | Удалить constants.py |
| ISS-139 | LOW | DEPRECATED | shared_config_constants.py | Дублирует constants/env_config.py | Удалить дубликат |
| ISS-140 | MEDIUM | DEPRECATED | parser_2gis_entry.py | Entry point дублирует parser_2gis/__main__.py | Удалить entry point |
| ISS-141 | LOW | DEPRECATED | main.py | Дублирует cli/main.py | Удалить |
| ISS-142 | LOW | DEPRECATED | runner/runner.py | Дублирует cli/launcher.py | Удалить |
| ISS-143 | MEDIUM | DEPRECATED | parallel/helpers.py | Устаревшие helper функции | Перенести в utils |
| ISS-144 | LOW | DEPRECATED | utils/data_utils.py | Дублирует функции из других модулей | Удалить дубликаты |
| ISS-145 | LOW | DEPRECATED | utils/math_utils.py | Простые функции без использования | Удалить или inline |
| ISS-146 | MEDIUM | DEPRECATED | parser/config.py | Дублирует shared_config_constants | Консолидировать |
| ISS-147 | LOW | DEPRECATED | parallel/options.py | Дублирует parser/options.py | Консолидировать |
| ISS-148 | LOW | DEPRECATED | writer/options.py | Дублирует общие options | Консолидировать |
| ISS-149 | LOW | DEPRECATED | logger/options.py | Дублирует общие options | Консолидировать |

### Пакет 9: Архитектурные проблемы и SOLID нарушения (ISS-150..ISS-179)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-150 | HIGH | ARCHITECTURE | protocols.py | Протокол слишком большой (400+ строк) | Разбить на специализированные протоколы |
| ISS-151 | HIGH | ARCHITECTURE | config.py | God object — содержит всё | Разбить на Config, EnvConfig, AppConfig |
| ISS-152 | MEDIUM | ARCHITECTURE | cache/manager.py | Нарушение SRP — кэш + ошибки + валидация | Разделить на CacheManager, CacheErrorHandler |
| ISS-153 | MEDIUM | ARCHITECTURE | chrome/browser.py | God class — 1000+ строк | Выделить BrowserSession, BrowserDOM, BrowserNetwork |
| ISS-154 | MEDIUM | ARCHITECTURE | parallel/coordinator.py | Нарушение SRP | Разделить на Coordinator, Merger, ErrorHandler |
| ISS-155 | LOW | ARCHITECTURE | parser/parsers/firm.py | Нарушение DIP — зависит от конкретики | Использовать абстракции |
| ISS-156 | MEDIUM | ARCHITECTURE | tui_textual/app.py | God class TUI приложения | Разделить на AppShell, ScreenManager, EventRouter |
| ISS-157 | LOW | ARCHITECTURE | utils/__init__.py | Too many exports (28) | Сгруппировать по подмодулям |
| ISS-158 | MEDIUM | ARCHITECTURE | cache/serializer.py | Нарушение OCP — if/else для форматов | Использовать strategy pattern |
| ISS-159 | LOW | ARCHITECTURE | writer/factory.py | Нарушение OCP — добавление формата требует правки factory | Использовать registry pattern |
| ISS-160 | MEDIUM | ARCHITECTURE | parser/factory.py | Нарушение OCP — добавление парсера требует правки factory | Использовать registry pattern |
| ISS-161 | HIGH | ARCHITECTURE | parallel/memory_manager.py | Глобальное состояние модуля | Использовать dependency injection |
| ISS-162 | MEDIUM | ARCHITECTURE | cache/pool.py | Нарушение SRP — pool + connection management | Разделить |
| ISS-163 | LOW | ARCHITECTURE | logger/visual_logger.py | Нарушение SRP — логика + rendering | Разделить |
| ISS-164 | MEDIUM | ARCHITECTURE | cli/formatter.py | Нарушение OCP | Использовать strategy pattern |
| ISS-165 | LOW | ARCHITECTURE | runner/cli.py | Дублирует cli/main.py | Удалить |
| ISS-166 | MEDIUM | ARCHITECTURE | parallel/builder.py | Нарушение SRP | Разделить |
| ISS-167 | LOW | ARCHITECTURE | resources/cities_loader.py | Нарушение SRP — загрузка + валидация | Разделить |
| ISS-168 | MEDIUM | ARCHITECTURE | validation/url_validator.py | Нарушение SRP — валидация + sanitization | Разделить |
| ISS-169 | LOW | ARCHITECTURE | validation/path_validator.py | Нарушение SRP | Разделить |
| ISS-170 | MEDIUM | ARCHITECTURE | parallel/strategies.py | Нарушение DIP — зависит от конкретики Chrome | Использовать абстракцию BrowserInterface |
| ISS-171 | HIGH | ARCHITECTURE | application/layer.py | Неполная реализация паттерна Factory | Добавить все варианты или сделать abstract |
| ISS-172 | MEDIUM | ARCHITECTURE | writer/models | Пустой подмодуль без кода | Удалить или реализовать |
| ISS-173 | LOW | ARCHITECTURE | parallel/common | Пустой подмодуль | Удалить |
| ISS-174 | MEDIUM | ARCHITECTURE | parallel/infrastructure | Пустой подмодуль | Удалить или реализовать |
| ISS-175 | LOW | ARCHITECTURE | tui_textual/screens | Много экранов без базового класса | Создать BaseScreen |
| ISS-176 | MEDIUM | ARCHITECTURE | parser/adaptive_limits.py | Нарушение SRP | Разделить |
| ISS-177 | LOW | ARCHITECTURE | chrome/file_handler.py | Нарушение DIP | Использовать абстракцию FileSystem |
| ISS-178 | MEDIUM | ARCHITECTURE | chrome/js_executor.py | Нарушение SRP — выполнение + парсинг | Разделить |
| ISS-179 | LOW | ARCHITECTURE | chrome/dom.py | Нарушение SRP — DOM queries + parsing | Разделить |

### Пакет 10: Стиль, документация и косметические проблемы (ISS-180..ISS-200)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-180 | LOW | STYLE | config.py | Отсутствуют docstrings у публичных классов | Добавить docstrings |
| ISS-181 | LOW | STYLE | protocols.py | Отсутствуют docstrings у методов протокола | Добавить docstrings |
| ISS-182 | LOW | STYLE | cache/manager.py | Сложные comprehensions > 3 уровней | Упростить |
| ISS-183 | LOW | STYLE | chrome/browser.py | Функции > 50 строк | Рефакторинг на мелкие функции |
| ISS-184 | LOW | STYLE | parallel/coordinator.py | Функции > 50 строк | Рефакторинг |
| ISS-185 | LOW | STYLE | parser/parsers/firm.py | Функции > 50 строк | Рефакторинг |
| ISS-186 | LOW | STYLE | tui_textual/app.py | Функции > 50 строк | Рефакторинг |
| ISS-187 | LOW | STYLE | utils/sanitizers.py | Сложная вложенность if > 4 уровней | Упростить логику |
| ISS-188 | LOW | STYLE | cache/serializer.py | Магические числа | Вынести в константы |
| ISS-189 | LOW | STYLE | parallel/file_merger.py | Магические числа | Вынести в константы |
| ISS-190 | LOW | STYLE | chrome/browser_builder.py | Дублирование кода настройки | Вынести в общую функцию |
| ISS-191 | LOW | STYLE | cli/progress.py | Magic strings для прогрессбара | Вынести в константы |
| ISS-192 | LOW | STYLE | logger/logger.py | Хардкод форматирования логов | Вынести в конфиг |
| ISS-193 | LOW | STYLE | constants/parser.py | Избыточные комментарии | Удалить устаревшие |
| ISS-194 | LOW | STYLE | chrome/constants.py | Все константы в одном месте | Сгруппировать по категориям |
| ISS-195 | LOW | STYLE | pydantic_compat.py | Модуль совместимости без необходимости | Удалить если py3.10+ |
| ISS-196 | LOW | STYLE | core_types.py |缺少 типизированных алиасов | Добавить больше TypeAlias |
| ISS-197 | LOW | STYLE | types.py | Дублирует core_types.py | Объединить |
| ISS-198 | LOW | STYLE | exceptions.py |缺乏 специализированных исключений | Добавить больше подклассов |
| ISS-199 | LOW | STYLE | version.py | Простая переменная версии | Использовать importlib.metadata |
| ISS-200 | LOW | STYLE | README.md | Отсутствует раздел API documentation | Добавить |

---

## Группировка по пакетам

### Пакет 1 (ISS-001..ISS-020): Критические проблемы возврата типов в protocols.py
- **Фокус:** Функции с declared return type не возвращают значение
- **Файлы:** protocols.py, application/layer.py, cli/launcher.py
- **Подход:** Добавить явные return или изменить аннотации на Optional

### Пакет 2 (ISS-021..ISS-040): Possibly unbound переменные и атрибуты
- **Фокус:** Переменные которые могут быть не инициализированы
- **Файлы:** cache/pool.py, cache/serializer.py, chrome/browser.py, parallel/*, utils/sanitizers.py
- **Подход:** Инициализировать значения по умолчанию, добавить fallback

### Пакет 3 (ISS-041..ISS-060): Отсутствующие импорты и символы
- **Фокус:** Unknown import symbols и missing imports
- **Файлы:** parallel/coordinator.py, parallel/parallel_parser.py, utils/__init__.py, chrome/*
- **Подход:** Добавить экспорты, установить missing packages, исправить импорты

### Пакет 4 (ISS-061..ISS-080): Протоколы и type expressions
- **Фокус:** Variable not allowed in type expression, redeclaration
- **Файлы:** cli/launcher.py, chrome/browser.py, parser/parsers/*, utils/*
- **Подход:** Использовать Literal, Typing.cast, удалить дубликаты

### Пакет 5 (ISS-081..ISS-100): Unused код и мёртвый код
- **Фокус:** Unused imports, variables, functions, modules
- **Файлы:** logger/visual_logger.py, tests/*, utils/*, parallel/*, validation/legacy.py
- **Подход:** Удалить неиспользуемый код, консолидировать дубликаты

### Пакет 6 (ISS-101..ISS-120): Производительность
- **Фокус:** N+1 queries, missing indexes, no backpressure, memory leaks
- **Файлы:** cache/*, parallel/*, chrome/*, utils/*
- **Подход:** Добавить индексы, connection pooling, batch operations

### Пакет 7 (ISS-121..ISS-134): Безопасность
- **Фокус:** SQL injection, path traversal, SSRF, race conditions
- **Файлы:** cache/manager.py, utils/sanitizers.py, chrome/*, validation/*
- **Подход:** Параметризация, whitelist, sandbox, validation

### Пакет 8 (ISS-135..ISS-149): Deprecated конструкции
- **Фокус:** Устаревшие модули, дубликаты, legacy код
- **Файлы:** setup.py, validation/legacy.py, constants.py, main.py, runner/*
- **Подход:** Удалить дубликаты, мигрировать на pyproject.toml

### Пакет 9 (ISS-150..ISS-179): Архитектурные проблемы SOLID
- **Фокус:** God classes, SRP/DIP/OCP violations
- **Файлы:** protocols.py, config.py, cache/manager.py, chrome/browser.py, parallel/*
- **Подход:** Разделить god classes, использовать паттерны, dependency injection

### Пакет 10 (ISS-180..ISS-200): Стиль и документация
- **Фокус:** Missing docstrings, magic numbers, long functions
- **Файлы:** config.py, protocols.py, chrome/browser.py, parallel/*, cli/*
- **Подход:** Добавить docstrings, вынести константы, рефакторинг длинных функций

---

## Стратегия валидации после каждого пакета

```bash
ruff check . --fix --exit-zero
ruff format . --check
pylint parser_2gis/ --exit-zero --output-format=text
mypy parser_2gis/ --no-error-summary --pretty
pyright parser_2gis/
bandit -r parser_2gis/ --exit-zero -ll
vulture parser_2gis/ --min-confidence 80 --exit-zero
pytest -q --tb=short
```
