# Реестр тестовых файлов

## Сводка

| Параметр | Значение |
|----------|----------|
| **Всего .py файлов** | 101 |
| **Тестовых файлов (с тестами)** | 97 |
| **Функций `def test_`** | 1271 |
| **Тест-кейсов pytest** | 1347 passed, 23 skipped (параметризация даёт доп. кейсы) |
| **Упало** | 0 failed |
| **Дата актуализации** | 2026-04-13 |

---

## Architecture

| Файл | Назначение | Проверяемый модуль | Тестов | Статус |
|------|-----------|-------------------|--------|--------|
| `tests/test_architecture_config_dataclasses.py` | Проверка dataclass конфигураций | `parser_2gis.config`, `parser_2gis.dataclasses` | 24 | active |
| `tests/test_architecture_solid.py` | Проверка SOLID принципов в архитектуре | `parser_2gis.*` (архитектура) | 65 | active |
| `tests/test_base_parser_abc.py` | Абстрактный базовый класс BaseParser | `parser_2gis.parser.base` | 24 | active |
| `tests/test_config.py` | Модуль config.py | `parser_2gis.config` | 19 | active |
| `tests/test_config_srp.py` | ISSUE-001: Разделение Configuration на модули (SRP) | `parser_2gis.config` | 22 | active |
| `tests/test_configuration_fields.py` | Ошибки при работе с полями конфигурации | `parser_2gis.config` | 18 | active |
| `tests/test_parser_factory_patterns.py` | Компиляция паттернов в parser/factory.py | `parser_2gis.parser.factory` | 8 | active |
| `tests/test_parser_options.py` | Модуль parser_options.py | `parser_2gis.parser.options` | 16 | active |
| `tests/test_function_decomposition.py` | Разбиение сложных функций (decomposition) | `parser_2gis.*` (код-стиль) | 17 | active |
| `tests/test_imports.py` | Проверка отсутствия циклических импортов | `parser_2gis.*` (импорты) | 20 | active |
| `tests/test_dependencies.py` | Проверка зависимостей и импортов (объединён с test_optional_deps_tui) | `parser_2gis` (зависимости) | 15 | active |
| `tests/test_version_exceptions.py` | Модули version.py и exceptions.py | `parser_2gis.version`, `parser_2gis.exceptions` | 26 | active |

## Cache

| Файл | Назначение | Проверяемый модуль | Тестов | Статус |
|------|-----------|-------------------|--------|--------|
| `tests/cache/test_cache_utils.py` | Тесты для cache_utils | `parser_2gis.cache.cache_utils` | 18 | active |
| `tests/cache/test_manager_cleanup.py` | Finally-блок в cache/manager.py | `parser_2gis.cache.manager` | 13 | active |
| `tests/cache/test_manager_retry.py` | Метод `_handle_db_error()` в manager.py | `parser_2gis.cache.manager` | 11 | active |
| `tests/cache/test_pool_critical_fixes.py` | CRITICAL проблемы в cache/pool.py | `parser_2gis.cache.pool` | 10 | active |
| `tests/cache/test_pool_exceptions.py` | Обработка исключений в cache/pool.py | `parser_2gis.cache.pool` | 14 | active |
| `tests/cache/test_serializer.py` | JsonSerializer | `parser_2gis.cache.serializer` | 6 | active |
| `tests/cache/test_validator.py` | CacheDataValidator | `parser_2gis.cache.validator` | 4 | active |
| `tests/test_cache_exceptions.py` | Специфичные исключения в cache.py | `parser_2gis.cache` | 9 | active |
| `tests/test_cache_manager_typing.py` | Типизация параметров CacheManager | `parser_2gis.cache.manager` | 5 | active |
| `tests/test_cache_wal_mode.py` | WAL режим в SQLite кэше | `parser_2gis.cache` (SQLite) | 6 | active |
| `tests/test_connection_pool_leak.py` | Утечка ресурсов в `_ConnectionPool` | `parser_2gis.cache.pool` | 11 | active |
| `tests/test_sql_injection_cache.py` | SQL-инъекции в cache validator | `parser_2gis.cache.validator` | 16 | active |

## Chrome

| Файл | Назначение | Проверяемый модуль | Тестов | Статус |
|------|-----------|-------------------|--------|--------|
| `tests/chrome/test_browser_separation.py` | Разделение классов в chrome/browser.py | `parser_2gis.chrome.browser` | 31 | active |
| `tests/chrome/test_constants.py` | Chrome constants | `parser_2gis.chrome.constants` | 12 | active |
| `tests/chrome/test_dom.py` | DOM parser | `parser_2gis.chrome.dom` | 9 | active |
| `tests/chrome/test_rate_limiter.py` | Функция `_enforce_rate_limit()` | `parser_2gis.chrome.rate_limiter` | 10 | active |
| `tests/chrome/test_remote_cleanup.py` | Метод `_cleanup_interface()` в remote.py | `parser_2gis.chrome.remote` | 12 | active |
| `tests/chrome/test_remote_critical_fixes.py` | CRITICAL проблемы в chrome/remote.py | `parser_2gis.chrome.remote` | 14 | active |
| `tests/chrome/test_subprocess_safety.py` | Безопасность subprocess в browser.py | `parser_2gis.chrome.browser` | 13 | active |
| `tests/test_browser_cleanup.py` | Утечка ресурсов браузера | `parser_2gis.chrome.browser` | 7 | active |
| `tests/test_chrome_browser_finalizer.py` | `weakref.finalize()` в chrome/browser.py | `parser_2gis.chrome.browser` | 7 | active |
| `tests/test_chrome_integration.py` | Модуль chrome и интеграционные тесты | `parser_2gis.chrome.*` | 37 | active |
| `tests/test_chrome_port_check.py` | Логика проверки порта Chrome | `parser_2gis.chrome.browser` | 7 | active |
| `tests/test_connect_interface_timeout.py` | Таймаут `_connect_interface()` | `parser_2gis.chrome.remote` | 7 | active |
| `tests/test_port_selection_os.py` | Автоматический выбор порта ОС | `parser_2gis.chrome.browser` | 6 | active |
| `tests/test_setup_tab_none_check.py` | Проверка `_chrome_tab` на None в `_setup_tab()` | `parser_2gis.chrome.browser` | 8 | active |

## Parallel

| Файл | Назначение | Проверяемый модуль | Тестов | Статус |
|------|-----------|-------------------|--------|--------|
| `tests/parallel/test_parallel_parser_delays.py` | Опции задержек в parallel/parallel_parser.py | `parser_2gis.parallel.parallel_parser` | 2 | active |
| `tests/parallel/test_rlock_critical.py` | CRITICAL проблемы в parallel/parallel_parser.py | `parser_2gis.parallel.parallel_parser` | 10 | active |
| `tests/parallel/test_semaphore.py` | Семафор в parallel/parallel_parser.py | `parser_2gis.parallel.parallel_parser` | 8 | active |
| `tests/test_cleanup_parallel_exceptions.py` | Исключения в `cleanup_resources()` и parallel_parser | `parser_2gis.parallel`, `parser_2gis.common` | 4 | active |
| `tests/test_launcher_cleanup_on_error.py` | Очистка ресурсов launcher при ошибке | `parser_2gis.launcher` | 2 | active |
| `tests/test_parallel_memory_error_handling.py` | MemoryError в параллельном парсере | `parser_2gis.parallel.parallel_parser` | 5 | active |
| `tests/test_parallel_parser.py` | Параллельный парсер (базовые тесты) | `parser_2gis.parallel.parallel_parser` | 10 | active |
| `tests/test_parallel_parser_stats.py` | Статистика параллельного парсера | `parser_2gis.parallel.parallel_parser` | 5 | active |

## Parser

| Файл | Назначение | Проверяемый модуль | Тестов | Статус |
|------|-----------|-------------------|--------|--------|
| `tests/parser/test_main_parser_memory.py` | Утечка памяти и TimeoutError в main.py | `parser_2gis.parser.parsers.main` | 7 | active |
| `tests/parser/test_navigate_timeout.py` | Обработка TimeoutError в main.py | `parser_2gis.parser.parsers.main` | 10 | active |
| `tests/test_firm_parser_validation.py` | Валидация initialState в firm.py | `parser_2gis.parser.parsers.firm` | 21 | active |
| `tests/test_parser.py` | Основной парсер 2GIS | `parser_2gis.parser` | 1 | active |

## Validation

| Файл | Назначение | Проверяемый модуль | Тестов | Статус |
|------|-----------|-------------------|--------|--------|
| `tests/validation/test_path_validator.py` | PathValidator | `parser_2gis.validation.path_validator` | 10 | active |
| `tests/validation/test_url_validator.py` | URLValidator | `parser_2gis.validation.url_validator` | 4 | active |
| `tests/test_phone_validation.py` | Валидация телефона в validation.py | `parser_2gis.validation` | 12 | active |
| `tests/test_validation_caching.py` | Кэширование валидации URL | `parser_2gis.validation` | 19 | active |
| `tests/test_js_validation.py` | Валидация JavaScript кода | `parser_2gis.validation.js` | 34 | active |

## Writer

| Файл | Назначение | Проверяемый модуль | Тестов | Статус |
|------|-----------|-------------------|--------|--------|
| `tests/writer/test_csv_writer_contact_processing.py` | Обработка контактов в csv_writer.py | `parser_2gis.writer.writers.csv_writer` | 2 | active |
| `tests/writer/test_csv_writer_errors.py` | Обработка ошибок в csv_writer.py | `parser_2gis.writer.writers.csv_writer` | 13 | active |
| `tests/test_csv_writer_strategies.py` | ISSUE-005: CSVWriter стратегии форматирования | `parser_2gis.writer.writers.csv_writer` | 36 | active |
| `tests/test_json_writer_structure.py` | Структура JSON в json_writer.py | `parser_2gis.writer.writers.json_writer` | 8 | active |
| `tests/test_path_traversal.py` | Защита от path traversal в writer/factory.py | `parser_2gis.writer.factory` | 7 | active |

## TUI

| Файл | Назначение | Проверяемый модуль | Тестов | Статус |
|------|-----------|-------------------|--------|--------|
| `tests/test_category_selector.py` | CategorySelectorScreen | `parser_2gis.tui.screens.category_selector` | 18 | active |
| `tests/test_city_selector.py` | CitySelectorScreen | `parser_2gis.tui.screens.city_selector` | 11 | active |
| `tests/test_duplicate_rubric_code.py` | Дублирующиеся ID виджетов в CategorySelectorScreen | `parser_2gis.tui.screens.category_selector` | 6 | active |
| `tests/test_tui_config_fields.py` | Соответствие полей TUI и моделей конфигурации | `parser_2gis.tui`, `parser_2gis.config` | 18 | active |
| `tests/test_tui_imports.py` | Ошибки импорта в TUI модулях | `parser_2gis.tui.*` (импорты) | 12 | active |
| `tests/test_tui_layout.py` | TUI layout | `parser_2gis.tui.app` | 3 | active |
| `tests/test_tui_state_management_regression.py` | Регрессионные ошибки управления состоянием TUI | `parser_2gis.tui` | 21 | active |
| `tests/test_tui_textual.py` | TUI Parser2GIS на Textual | `parser_2gis.tui` | 15 | active |
| `tests/test_tui_textual_logger.py` | Ошибки в TUI Textual | `parser_2gis.tui` | 3 | active |
| `tests/test_widget_unique_ids.py` | Уникальность ID виджетов в TUI | `parser_2gis.tui` | 5 | active |

## Utils / Common

| Файл | Назначение | Проверяемый модуль | Тестов | Статус |
|------|-----------|-------------------|--------|--------|
| `tests/utils/test_sanitizers.py` | Модуль utils/sanitizers | `parser_2gis.utils.sanitizers` | 10 | active |
| `tests/test_common.py` | Модуль common.py и качество кода | `parser_2gis.common` | 30 | active |
| `tests/test_paths_functions.py` | Наличие критических функций в модуле paths | `parser_2gis.paths` | 10 | active |
| `tests/test_sanitize_thread_safety.py` | Потокобезопасность `_sanitize_value` | `parser_2gis.writer` (sanitizer) | 6 | active |

## Integration / Quality / Security

| Файл | Назначение | Проверяемый модуль | Тестов | Статус |
|------|-----------|-------------------|--------|--------|
| `tests/test_cli_arguments.py` | Регистрация аргументов командной строки | `parser_2gis.cli` | 13 | active |
| `tests/test_code_quality.py` | Качество кода | `parser_2gis.*` (линтеры) | 7 | active |
| `tests/test_docstrings.py` | Наличие docstrings | `parser_2gis.*` (документация) | 24 | active |
| `tests/test_exception_handling.py` | Обработка исключений | `parser_2gis.*` | 13 | active |
| `tests/test_file_handling.py` | Работа с файлами | `parser_2gis.common` | 9 | active |
| `tests/test_file_logger.py` | Модуль файлового логирования (FileLogger) | `parser_2gis.logger` | 20 | active |
| `tests/test_line_length.py` | Проверка длины строк | `parser_2gis.*` (стиль) | 16 | active |
| `tests/test_logger.py` | Модуль logger.py | `parser_2gis.logger` | 19 | active |
| `tests/test_logging_improvements.py` | Улучшения логирования | `parser_2gis.logger` | 11 | active |
| `tests/test_main_categories_mode.py` | Режим основных категорий | `parser_2gis.parser` | 7 | active |
| `tests/test_max_workers_validation.py` | Валидация max_workers | `parser_2gis.parallel` | 14 | active |
| `tests/test_typing_pylint_fixes.py` | Исправления типизации (P1) и pylint fixes | `parser_2gis.*` (typing) | 23 | active |
| `tests/test_path_traversal.py` | Защита от path traversal атак | `parser_2gis.writer.factory` | 7 | active |
| `tests/test_pep8_compliance.py` | Соответствие PEP8 | `parser_2gis.*` (стиль) | 9 | active |
| `tests/test_performance_fixes.py` | Исправления производительности (P1) | `parser_2gis.*` | 13 | active |
| `tests/test_pydantic_compatibility.py` | Работа с Pydantic v2 | `parser_2gis` (pydantic) | 9 | active |
| `tests/test_pysocks_dependency.py` | Зависимость PySocks для SOCKS в urllib3 | `parser_2gis` (зависимости) | 3 | active |
| `tests/test_security_fixes.py` | Исправления безопасности (P0) | `parser_2gis.*` | 32 | active |
| `tests/test_specific_exceptions.py` | Специфическая обработка исключений | `parser_2gis.exceptions` | 17 | active |
| `tests/test_temp_file_race.py` | Race condition в `register_temp_file` | `parser_2gis.common` | 3 | active |
| `tests/test_temp_file_timer_cleanup.py` | Очистка временных файлов по таймеру | `parser_2gis.common` | 14 | active |
| `tests/test_visited_links_cleanup.py` | Периодическая очистка visited_links | `parser_2gis.parser` | 5 | active |
| `tests/test_weakref_finalize.py` | Использование `weakref.finalize` | `parser_2gis.*` | 14 | active |

---

## Служебные файлы (не содержат тестов)

| Файл | Назначение |
|------|-----------|
| `tests/__init__.py` | Инициализация пакета тестов |
| `tests/common/__init__.py` | Инициализация подпакета common |
| `tests/common/file_helpers.py` | Хелперы для создания временных файлов |
| `tests/common/log_assertions.py` | Хелперы для проверки логов |
| `tests/conftest.py` | Общие фикстуры и конфигурация для pytest |
