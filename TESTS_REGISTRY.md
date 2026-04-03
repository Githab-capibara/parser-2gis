# Реестр тестов Parser2GIS

**Дата последней актуализации:** 2026-04-02
**Дата последней очистки:** 2026-04-02

## 📊 Статистика

| Категория | Файлов | Тестов | Статус |
|-----------|--------|--------|--------|
| **Архитектура** | 15 | ~400 | ✅ Активны |
| **Рефакторинг** | 5 | ~200 | ✅ Активны |
| **Безопасность** | 3 | ~120 | ✅ Активны |
| **Производительность** | 2 | ~80 | ✅ Активны |
| **TUI** | 10 | ~200 | ⚠️ Требуют textual |
| **Парсер** | 5 | ~100 | ✅ Активны |
| **Кэш** | 5 | ~150 | ✅ Активны |
| **Browser** | 5 | ~150 | ✅ Активны |
| **Parallel** | 4 | ~100 | ✅ Активны |
| **Utils** | 2 | ~60 | ✅ Активны |
| **Writer** | 4 | ~80 | ✅ Активны |
| **Конфигурация** | 3 | ~100 | ✅ Активны |
| **Прочее** | 35 | ~700 | ✅ Активны |

**ВСЕГО:** 131 файл, ~1916 тестов (2 пропуска - textual not installed)

---

## 🗑️ УДАЛЕННЫЕ ТЕСТЫ (очистка 2026-04-02)

| Файл | Причина удаления |
|------|------------------|
| `test_error_handling_fixes.py` | Ссылается на удаленные функции (_get_memory_monitor, _temp_files_lock) |
| `test_protocols.py` | Дублирует test_architecture_protocols.py |
| `test_temp_file_registry_thread_safety.py` | Дублирует test_temp_file_race.py |

## ✅ ИСПРАВЛЕННЫЕ ТЕСТЫ (очистка 2026-04-02)

| Файл | Исправление |
|------|-------------|
| `test_file_handling.py` | register_temp_file → temp_file_manager.register() |
| `test_function_decomposition.py` | функции → методы CacheDataValidator |
| `test_performance_fixes.py` | _compute_* → compute_* из cache_utils |
| `test_security_fixes.py` | _sanitize_csv_value → SanitizeFormatter.format() |
| `test_sql_injection_cache.py` | функции → методы CacheDataValidator |
| `test_temp_file_race.py` | функции → методы temp_file_manager |
| `test_temp_file_timer_race.py` | функции → методы temp_file_manager |

---

## ✅ РАБОЧИЕ ТЕСТЫ

### Архитектура (test_architecture_*.py)
- `test_architecture_antipatterns.py` — тесты антипаттернов
- `test_architecture_boundaries.py` — тесты границ модулей
- `test_architecture_config_dataclasses.py` — тесты dataclass конфигурации
- `test_architecture_dependencies.py` — тесты зависимостей
- `test_architecture_di.py` — тесты dependency injection
- `test_architecture_facades.py` — тесты фасадов
- `test_architecture_improvements.py` — тесты улучшений архитектуры
- `test_architecture_infrastructure.py` — тесты infrastructure слоя
- `test_architecture_integration.py` — интеграционные тесты архитектуры
- `test_architecture_integrity.py` — тесты целостности
- `test_architecture_modularity.py` — тесты модульности
- `test_architecture_module_independence.py` — тесты независимости модулей
- `test_architecture_no_cycles.py` — тесты отсутствия циклов
- `test_architecture_no_duplicates.py` — тесты отсутствия дубликатов
- `test_architecture_principles.py` — тесты принципов
- `test_architecture_protocols.py` — тесты протоколов
- `test_architecture_resources.py` — тесты ресурсов
- `test_architecture_separation.py` — тесты разделения ответственности
- `test_architecture_solid.py` — тесты SOLID принципов
- `test_architecture_validation.py` — тесты валидации архитектуры

### Кэш (test_cache_*.py, tests/cache/)
- `test_cache_exceptions.py` — тесты исключений кэша
- `test_cache_manager_typing.py` — тесты типизации менеджера кэша
- `test_cache_wal_mode.py` — тесты WAL режима
- `test_sql_injection_cache.py` — тесты защиты от SQL injection
- `cache/test_manager_cleanup.py` — тесты очистки менеджера
- `cache/test_pool_critical_fixes.py` — тесты критических исправлений пула
- `cache/test_pool_exceptions.py` — тесты исключений пула

### Browser (test_chrome_*.py, tests/chrome/)
- `test_browser_cleanup.py` — тесты очистки браузера
- `test_chrome_browser_finalizer.py` — тесты финализатора
- `test_chrome_port_check.py` — тесты проверки портов
- `test_port_selection_os.py` — тесты выбора портов ОС
- `chrome/test_browser_separation.py` — тесты разделения логики
- `chrome/test_remote_critical_fixes.py` — тесты критических исправлений
- `chrome/test_subprocess_safety.py` — тесты безопасности subprocess

### Parallel (test_parallel_*.py, tests/parallel/)
- `test_parallel_memory_error_handling.py` — тесты обработки MemoryError
- `test_parallel_parser.py` — тесты параллельного парсера
- `test_parallel_parser_stats.py` — тесты статистики
- `parallel/test_parallel_parser_delays.py` — тесты задержек
- `parallel/test_rlock_critical.py` — тесты критичности RLock

### Парсер (tests/parser/)
- `test_base_parser_abc.py` — тесты ABC парсера
- `test_firm_parser_validation.py` — тесты валидации firm парсера
- `test_parser_factory_patterns.py` — тесты factory паттерна
- `test_parser_options.py` — тесты опций парсера
- `parser/test_main_parser_memory.py` — тесты памяти main парсера
- `parser/test_navigate_timeout.py` — тесты таймаута навигации

### Utils (tests/utils/)
- `test_path_traversal.py` — тесты path traversal
- `test_path_traversal_double_encoding.py` — тесты двойного кодирования
- `test_path_validator_module.py` — тесты модуля валидации путей
- `test_paths_functions.py` — тесты функций путей
- `utils/test_path_validation.py` — тесты валидации путей
- `utils/test_temp_file_timer_finally.py` — тесты TempFileTimer

### Writer (tests/writer/)
- `test_csv_writer_contact_processing.py` — тесты обработки контактов
- `test_csv_writer_errors.py` — тесты ошибок CSV writer
- `test_csv_writer_strategies.py` — тесты стратегий CSV writer
- `test_json_writer_structure.py` — тесты структуры JSON writer

### TUI (test_tui_*.py)
- `test_category_selector.py` — тесты селектора категорий (требует textual)
- `test_city_selector.py` — тесты селектора городов (требует textual)
- `test_duplicate_rubric_code.py` — тесты дублирования рубрик (требует textual)
- `test_tui_config_fields.py` — тесты полей конфигурации TUI
- `test_tui_imports.py` — тесты импортов TUI
- `test_tui_layout.py` — тесты layout TUI (требует textual)
- `test_tui_state_management_regression.py` — тесты регрессии управления состоянием
- `test_tui_stop_parsing_fix.py` — тесты исправления остановки парсинга
- `test_tui_textual.py` — тесты textual (требует textual)
- `test_tui_textual_logger.py` — тесты логгера textual (требует textual)
- `test_widget_unique_ids.py` — тесты уникальности ID виджетов (требует textual)

### Конфигурация (test_config*.py)
- `test_config.py` — тесты конфигурации
- `test_config_srp.py` — тесты SRP конфигурации
- `test_configuration_fields.py` — тесты полей конфигурации

### Безопасность (test_security*.py)
- `test_security_fixes.py` — тесты исправлений безопасности
- `test_security_and_reliability_fixes.py` — тесты безопасности и надежности
- `test_js_validation.py` — тесты валидации JavaScript

### Производительность (test_performance*.py)
- `test_performance_fixes.py` — тесты исправлений производительности

### Рефакторинг (test_refactoring*.py)
- `test_refactoring_80_issues.py` — тесты 80 проблем рефакторинга
- `test_refactoring_issues.py` — тесты проблем рефакторинга
- `test_refactoring_kiss.py` — тесты KISS принципов
- `test_refactoring_package_3.py` — тесты пакета 3
- `test_refactoring_package_4.py` — тесты пакета 4 (parser_2gis/tests/)
- `test_refactoring_packages_9_10.py` — тесты пакетов 9-10

### Прочее
- `test_cli_arguments.py` — тесты аргументов CLI
- `test_code_improvements.py` — тесты улучшений кода
- `test_code_quality.py` — тесты качества кода
- `test_common.py` — общие тесты
- `test_dependencies.py` — тесты зависимостей
- `test_docstrings.py` — тесты документирования
- `test_exception_handling.py` — тесты обработки исключений
- `test_file_handling.py` — тесты работы с файлами
- `test_file_logger.py` — тесты файлового логгера
- `test_fixes_23_30.py` — тесты исправлений 23-30
- `test_function_decomposition.py` — тесты декомпозиции функций
- `test_imports.py` — тесты импортов
- `test_integration.py` — интеграционные тесты
- `test_launcher_cleanup_on_error.py` — тесты очистки launcher при ошибке
- `test_line_length.py` — тесты длины строк
- `test_logger.py` — тесты логгера
- `test_logging_improvements.py` — тесты улучшений логирования
- `test_main_categories_mode.py` — тесты режима категорий
- `test_max_workers_validation.py` — тесты валидации max_workers
- `test_new_improvements.py` — тесты новых улучшений
- `test_optional_deps_tui.py` — тесты опциональных зависимостей TUI
- `test_pep8_compliance.py` — тесты соответствия PEP8
- `test_phone_validation.py` — тесты валидации телефонов
- `test_process_manager_simplified.py` — тесты упрощенного ProcessManager
- `test_pydantic_compatibility.py` — тесты совместимости Pydantic
- `test_pysocks_dependency.py` — тесты зависимости PySocks
- `test_rlock_usage.py` — тесты использования RLock
- `test_run_sh_tui_flags.py` — тесты флагов TUI в run.sh
- `test_sanitize_thread_safety.py` — тесты потокобезопасности санитизации
- `test_setup_tab_none_check.py` — тесты проверки setup_tab None
- `test_specific_exceptions.py` — тесты специфичных исключений
- `test_sqlite_thread_safety.py` — тесты потокобезопасности SQLite
- `test_temp_file_race.py` — тесты гонок временных файлов
- `test_temp_file_timer_cleanup.py` — тесты очистки таймера временных файлов
- `test_temp_file_timer_race.py` — тесты гонок таймера временных файлов
- `test_thread_safety.py` — тесты потокобезопасности
- `test_typed_dict_categories.py` — тесты TypedDict категорий
- `test_typing_pylint_fixes.py` — тесты типизации и pylint
- `test_validation_caching.py` — тесты кэширования валидации
- `test_version_exceptions.py` — тесты исключений версии
- `test_visited_links_cleanup.py` — тесты очистки посещенных ссылок
- `test_weakref_finalize.py` — тесты weakref финализации
- `test_connect_interface_timeout.py` — тесты таймаута подключения
- `test_connection_pool_leak.py` — тесты утечек пула соединений
- `test_cleanup_parallel_exceptions.py` — тесты исключений параллельной очистки
- `test_audit_fixes.py` — тесты исправлений аудита

---

## 🔧 КОНФИГУРАЦИЯ ТЕСТОВ

### pytest.ini
- Минимальная версия: 6.0
- Маркеры: slow, integration, gui, requires_chrome, requires_network, requires_tui, benchmark
- Coverage порог: 85%
- Фильтры предупреждений: PendingDeprecationWarning, ResourceWarning

### conftest.py
- Общие фикстуры для всех тестов
- Моки для браузера, кэша, парсера
- Утилиты для создания тестовых данных

### .coveragerc
- Исключения: tui_textual, tests, venv
- Ветвление: включено
- Параллельное выполнение: включено

---

## 📝 ПРИМЕЧАНИЯ

- Тесты требуют textual для TUI функциональности (6 тестов пропускаются)
- Некоторые тесты требуют Chrome (mark: requires_chrome)
- Некоторые тесты требуют сеть (mark: requires_network)
- Coverage порог 85% для всего проекта
- Критические модули требуют 100% coverage (cache.py, chrome/browser.py, validation.py)
