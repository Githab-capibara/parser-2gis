# Тестовый реестр parser-2gis

**Дата последней актуализации:** 2026-04-03
**Дата последней очистки:** 2026-04-03

## Сводная статистика

| Метрика | Значение |
|---------|----------|
| Тестовых файлов | 127 (после очистки: удалено 6 файлов) |
| Тестовых функций | ~1950 |
| Тестовых классов | ~530 |
| Конфигурация | pytest.ini, conftest.py (1072 строки, ~50 фикстур), tox.ini, .coveragerc |
| Coverage threshold | 85% |

## Удалённые файлы (очистка 2026-04-03)

| Файл | Причина удаления |
|------|-----------------|
| `tests/scripts/update_cities_list.py` | Не тест — утилита загрузки городов |
| `tests/scripts/update_rubrics_list.py` | Не тест — утилита загрузки рубрик |
| `tests/test_merge_logic.py` | 0 тестовых функций — utility-скрипт |
| `tests/test_run_sh_tui_flags.py` | Устарел — ссылки на удалённые `_tui_stub`/`_tui_omsk_stub` |
| `tests/test_rlock_usage.py` | Дублирует `tests/parallel/test_rlock_critical.py` |
| `tests/test_path_traversal_double_encoding.py` | Дублирует `tests/test_security_and_reliability_fixes.py` |

## Структура тестов

### tests/ (корень) — архитектурные и интеграционные тесты
- `test_architecture_*.py` — проверка архитектурных принципов (SOLID, DI, DDD, циклы, зависимости)
- `test_security_*.py` — тесты безопасности (SQL injection, XSS, path traversal)
- `test_refactoring_*.py` — тесты подтверждений рефакторинга
- `test_cache_*.py` — тесты кэша
- `test_chrome*.py` — тесты Chrome-модуля
- `test_cli*.py` — тесты CLI
- `test_config*.py` — тесты конфигурации
- `test_parallel_*.py` — тесты параллельного парсинга
- `test_parser*.py` — тесты парсера
- `test_tui*.py` — тесты TUI (textual)
- `test_logger*.py` — тесты логирования
- `test_path*.py` — тесты валидации путей
- `test_temp_file*.py` — тесты временных файлов
- `test_validation*.py` — тесты валидации
- `test_version*.py` — тесты версий/исключений
- `test_writer*.py` — тесты writer-модуля

### tests/cache/
- `test_manager_cleanup.py` — тесты очистки CacheManager
- `test_pool_critical_fixes.py` — критические исправления ConnectionPool
- `test_pool_exceptions.py` — обработка исключений в пуле

### tests/chrome/
- `test_browser_separation.py` — разделение ответственности браузера
- `test_remote_critical_fixes.py` — критические исправления ChromeRemote
- `test_subprocess_safety.py` — безопасность subprocess

### tests/parallel/
- `test_parallel_parser_delays.py` — задержки в параллельном парсере
- `test_rlock_critical.py` — критическое использование RLock

### tests/parser/
- `test_main_parser_memory.py` — оптимизация памяти MainPageParser
- `test_navigate_timeout.py` — обработка таймаутов навигации

### tests/utils/
- `test_path_validation.py` — валидация путей
- `test_temp_file_timer_finally.py` — очистка TempFileTimer

### tests/writer/
- `test_csv_writer_contact_processing.py` — обработка контактов CSV
- `test_csv_writer_errors.py` — обработка ошибок CSV

### parser_2gis/tests/
- `test_critical_fixes.py` — критические исправления ядра
- `test_refactoring.py` — рефакторинг ядра
- `test_refactoring_package_4.py` — пакет 4 рефакторинга

## Фикстуры (conftest.py)

~50 фикстур включая: `mock_oserror`, `temp_csv_files`, `mock_executor`, `mock_chrome_timeout`, `mock_db_connection`, `mock_tui_app_base`, `mock_chrome_options`, `mock_parser_options`, `mock_browser`, `mock_cities`, `mock_config`, `mock_cache_manager`, `mock_parallel_config` и др.

## Маркеры pytest

| Маркер | Описание |
|--------|----------|
| `slow` | Медленные тесты |
| `integration` | Интеграционные тесты |
| `gui` | Тесты GUI |
| `requires_chrome` | Требует Chrome |
| `requires_network` | Требует сеть |
| `requires_tui` | Требует textual TUI |
| `benchmark` | Бенчмарки |
| `critical` | Критические тесты |
| `unit` | Юнит-тесты |
