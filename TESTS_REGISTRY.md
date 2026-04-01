# 📋 РЕЕСТР ТЕСТОВ parser-2gis

**Дата последней актуализации:** 2026-04-01  
**Дата последней очистки:** 2026-04-01

---

## 📊 ОБЩАЯ СТАТИСТИКА

| Метрика | Значение |
|---------|----------|
| **Количество тестовых файлов** | 119 |
| **Количество тестовых классов** | 114 |
| **Количество тестовых функций** | 1601 |
| **Процент покрытия (coverage)** | 87% |
| **Pass Rate** | 95%+ |
| **Среднее время прогона** | ~45 секунд |

---

## 📁 СТРУКТУРА ДИРЕКТОРИЙ ТЕСТОВ

```
tests/
├── cache/              # Тесты кэша (3 файла)
├── chrome/             # Тесты браузера (3 файла)
├── parallel/           # Тесты параллельного парсинга (2 файла)
├── parser/             # Тесты парсеров (2 файла)
├── utils/              # Тесты утилит (2 файла)
├── writer/             # Тесты writers (2 файла)
├── scripts/            # Утилиты обновления данных (2 файла)
└── [корневые тесты]    # Архитектура, интеграция, исправления (~103 файла)
```

### Описание директорий

| Директория | Файлов | Назначение |
|------------|--------|------------|
| `tests/cache/` | 3 | Тесты CacheManager, connection pool, сериализации, WAL режима |
| `tests/chrome/` | 3 | Тесты браузера, remote interface, subprocess безопасности |
| `tests/parallel/` | 2 | Тесты параллельного парсинга, RLock, delays |
| `tests/parser/` | 2 | Тесты основных парсеров, memory, navigate timeout |
| `tests/utils/` | 2 | Тесты path validation, temp file timer |
| `tests/writer/` | 2 | Тесты CSV/JSON writers, обработка ошибок |
| `tests/scripts/` | 2 | Скрипты обновления cities.json и rubrics.json |
| `tests/` (корень) | ~103 | Архитектурные тесты, интеграция, bugfixes, security |

---

## 📄 ТАБЛИЦА ВСЕХ ТЕСТОВЫХ ФАЙЛОВ

### Корневые тесты (архитектура, интеграция, исправления)

| Файл | Описание | Что тестирует | Категория |
|------|----------|---------------|-----------|
| `test_architecture_antipatterns.py` | Тесты антипаттернов | Архитектурные антипаттерны | Architecture |
| `test_architecture_boundaries.py` | Тесты границ модулей | Границы слоёв архитектуры | Architecture |
| `test_architecture_config_dataclasses.py` | Тесты dataclass конфигурации | Configuration dataclasses | Architecture |
| `test_architecture_dependencies.py` | Тесты зависимостей | Циклические зависимости | Architecture |
| `test_architecture_di.py` | Тесты Dependency Injection | Внедрение зависимостей | Architecture |
| `test_architecture_facades.py` | Тесты фасадов | Application Layer фасады | Architecture |
| `test_architecture_improvements.py` | Тесты улучшений | Архитектурные улучшения | Architecture |
| `test_architecture_infrastructure.py` | Тесты инфраструктуры | Infrastructure слой | Architecture |
| `test_architecture_integration.py` | Тесты интеграции | Интеграция компонентов | Architecture |
| `test_architecture_integrity.py` | Тесты целостности | Архитектурная целостность | Architecture |
| `test_architecture_modularity.py` | Тесты модульности | Модульность архитектуры | Architecture |
| `test_architecture_module_independence.py` | Тесты независимости модулей | Independence модулей | Architecture |
| `test_architecture_no_cycles.py` | Тесты отсутствия циклов | Циклические импорты | Architecture |
| `test_architecture_no_duplicates.py` | Тесты отсутствия дублирования | Дублирование кода | Architecture |
| `test_architecture_principles.py` | Тесты принципов | DRY, YAGNI, OCP, DIP | Architecture |
| `test_architecture_protocols.py` | Тесты протоколов | Protocol абстракции | Architecture |
| `test_architecture_resources.py` | Тесты ресурсов | Структура resources/ | Architecture |
| `test_architecture_separation.py` | Тесты разделения | Разделение ответственности | Architecture |
| `test_architecture_solid.py` | Тесты SOLID | Принципы SOLID | Architecture |
| `test_architecture_validation.py` | Тесты валидации | Централизованная валидация | Architecture |
| `test_audit_fixes.py` | Тесты исправлений аудита | Исправления по аудиту | Audit |
| `test_base_parser_abc.py` | Тесты BaseParser ABC | Абстрактный базовый класс | Parser |
| `test_browser_cleanup.py` | Тесты очистки браузера | Browser cleanup | Chrome |
| `test_cache_exceptions.py` | Тесты исключений кэша | Cache exceptions | Cache |
| `test_cache_manager_typing.py` | Тесты типизации кэша | CacheManager typing | Cache |
| `test_cache_wal_mode.py` | Тесты WAL режима кэша | SQLite WAL mode | Cache |
| `test_category_selector.py` | Тесты выбора категорий | CategorySelectorScreen | TUI |
| `test_chrome.py` | Тесты Chrome модуля | Chrome browser | Chrome |
| `test_chrome_browser_finalizer.py` | Тесты финализатора браузера | Browser finalizer | Chrome |
| `test_chrome_port_check.py` | Тесты проверки портов | Chrome DevTools port | Chrome |
| `test_city_selector.py` | Тесты выбора городов | CitySelectorScreen | TUI |
| `test_cleanup_parallel_exceptions.py` | Тесты очистки параллельно | Parallel cleanup | Parallel |
| `test_cli_arguments.py` | Тесты CLI аргументов | Argument parsing | CLI |
| `test_code_improvements.py` | Тесты улучшений кода | Code improvements | Quality |
| `test_code_quality.py` | Тесты качества кода | Code quality metrics | Quality |
| `test_common.py` | Общие интеграционные тесты | Integration common | Integration |
| `test_config.py` | Тесты конфигурации | Config module | Config |
| `test_configuration_fields.py` | Тесты полей конфигурации | Configuration fields | Config |
| `test_connect_interface_timeout.py` | Тесты таймаута подключения | Chrome connect timeout | Chrome |
| `test_connection_pool_leak.py` | Тесты утечек pool | Connection pool leak | Cache |
| `test_dependencies.py` | Тесты зависимостей | Project dependencies | Dependencies |
| `test_docstrings.py` | Тесты docstrings | Наличие docstrings | Quality |
| `test_duplicate_rubric_code.py` | Тесты дубликатов rubric | Rubric code duplicates | Parser |
| `test_exception_handling.py` | Тесты обработки исключений | Exception handling | Error Handling |
| `test_file_handling.py` | Тесты обработки файлов | File operations | Utils |
| `test_file_logger.py` | Тесты файлового логгера | File logger | Logger |
| `test_firm_parser_validation.py` | Тесты валидации фирм | FirmParser validation | Parser |
| `test_fixes_23_30.py` | Тесты исправлений 23-30 | Fixes 23-30 | Bugfixes |
| `test_function_decomposition.py` | Тесты декомпозиции функций | Function decomposition | Quality |
| `test_imports.py` | Тесты импортов | Import statements | Quality |
| `test_integration.py` | Интеграционные тесты | Component integration | Integration |
| `test_js_validation.py` | Тесты валидации JS | JavaScript validation | Validation |
| `test_json_writer_structure.py` | Тесты структуры JSON writer | JSON writer | Writer |
| `test_launcher_cleanup_on_error.py` | Тесты очистки лаунчера | Launcher cleanup | Error Handling |
| `test_line_length.py` | Тесты длины строк | Line length compliance | Quality |
| `test_logger.py` | Тесты логгера | Logger module | Logger |
| `test_logging_improvements.py` | Тесты улучшений логирования | Logging improvements | Logger |
| `test_main_categories_mode.py` | Тесты режима категорий | Main categories mode | Parser |
| `test_max_workers_validation.py` | Тесты валидации workers | Max workers validation | Validation |
| `test_merge_logic.py` | Тесты логики слияния | Merge logic | Parallel |
| `test_new_improvements.py` | Тесты новых улучшений | New improvements | Improvements |
| `test_optional_deps_tui.py` | Тесты опциональных зависимостей | Optional TUI deps | Dependencies |
| `test_parallel_memory_error_handling.py` | Тесты MemoryError | Memory error handling | Parallel |
| `test_parallel_parser.py` | Тесты параллельного парсера | Parallel parser | Parallel |
| `test_parallel_parser_stats.py` | Тесты статистики парсера | Parallel stats | Parallel |
| `test_parser.py` | Тесты парсера | Main parser | Parser |
| `test_parser_factory_patterns.py` | Тесты фабрик парсеров | Parser factory patterns | Parser |
| `test_parser_options.py` | Тесты опций парсера | Parser options | Parser |
| `test_path_traversal.py` | Тесты path traversal | Path traversal protection | Security |
| `test_path_traversal_double_encoding.py` | Тесты double encoding | Double encoding attack | Security |
| `test_path_validator_module.py` | Тесты валидации путей | Path validator | Security |
| `test_paths_functions.py` | Тесты функций путей | Paths functions | Utils |
| `test_pep8_compliance.py` | Тесты PEP8 | PEP8 compliance | Quality |
| `test_phone_validation.py` | Тесты валидации телефонов | Phone validation | Validation |
| `test_port_selection_os.py` | Тесты выбора портов ОС | OS port selection | Chrome |
| `test_process_manager_simplified.py` | Тесты ProcessManager | Process manager | Parallel |
| `test_protocols.py` | Тесты протоколов | Protocol definitions | Architecture |
| `test_pydantic_compatibility.py` | Тесты Pydantic | Pydantic compatibility | Dependencies |
| `test_pysocks_dependency.py` | Тесты PySocks | PySocks dependency | Dependencies |
| `test_rlock_usage.py` | Тесты RLock | RLock usage | Parallel |
| `test_run_sh_tui_flags.py` | Тесты флагов TUI | run.sh TUI flags | TUI |
| `test_sanitize_thread_safety.py` | Тесты потокобезопасности sanitize | Sanitize thread safety | Utils |
| `test_security_and_reliability_fixes.py` | Тесты безопасности | Security fixes | Security |
| `test_setup_tab_none_check.py` | Тесты проверки None | Setup tab None check | Chrome |
| `test_specific_exceptions.py` | Тесты специфичных исключений | Specific exceptions | Error Handling |
| `test_sql_injection_cache.py` | Тесты SQL инъекций | SQL injection protection | Security |
| `test_sqlite_thread_safety.py` | Тесты потокобезопасности SQLite | SQLite thread safety | Cache |
| `test_temp_file_race.py` | Тесты race condition файлов | Temp file race | Security |
| `test_temp_file_registry_thread_safety.py` | Тесты реестра файлов | Temp file registry | Security |
| `test_temp_file_timer_cleanup.py` | Тесты таймера очистки | Temp file timer | Security |

### tests/cache/

| Файл | Описание | Что тестирует | Категория |
|------|----------|---------------|-----------|
| `test_manager_cleanup.py` | Тесты очистки менеджера | CacheManager cleanup | Cache |
| `test_pool_critical_fixes.py` | Тесты исправлений pool | Connection pool fixes | Cache |
| `test_pool_exceptions.py` | Тесты исключений pool | Pool exceptions | Cache |

### tests/chrome/

| Файл | Описание | Что тестирует | Категория |
|------|----------|---------------|-----------|
| `test_browser_separation.py` | Тесты разделения браузера | Browser separation | Chrome |
| `test_remote_critical_fixes.py` | Тесты исправлений remote | ChromeRemote fixes | Chrome |
| `test_subprocess_safety.py` | Тесты безопасности subprocess | Subprocess safety | Chrome |

### tests/parallel/

| Файл | Описание | Что тестирует | Категория |
|------|----------|---------------|-----------|
| `test_parallel_parser_delays.py` | Тесты задержек парсера | Parallel parser delays | Parallel |
| `test_rlock_critical.py` | Тесты критических RLock | RLock critical sections | Parallel |

### tests/parser/

| Файл | Описание | Что тестирует | Категория |
|------|----------|---------------|-----------|
| `test_main_parser_memory.py` | Тесты памяти парсера | Main parser memory | Parser |
| `test_navigate_timeout.py` | Тесты таймаута навигации | Navigate timeout | Parser |

### tests/utils/

| Файл | Описание | Что тестирует | Категория |
|------|----------|---------------|-----------|
| `test_path_validation.py` | Тесты валидации путей | Path validation | Utils |
| `test_temp_file_timer_finally.py` | Тесты таймера в finally | Temp file timer finally | Utils |

### tests/writer/

| Файл | Описание | Что тестирует | Категория |
|------|----------|---------------|-----------|
| `test_csv_writer_contact_processing.py` | Тесты обработки контактов | CSV writer contacts | Writer |
| `test_csv_writer_errors.py` | Тесты ошибок writer | CSV writer errors | Writer |

### tests/scripts/

| Файл | Описание | Что тестирует | Категория |
|------|----------|---------------|-----------|
| `update_cities_list.py` | Скрипт обновления городов | Cities list update | Scripts |
| `update_rubrics_list.py` | Скрипт обновления рубрик | Rubrics list update | Scripts |

---

## 🏷️ МАРКЕРЫ PYTEST

| Маркер | Описание | Пример использования |
|--------|----------|---------------------|
| `requires_chrome` | Тесты, требующие установленный Chrome | `@pytest.mark.requires_chrome` |
| `requires_network` | Тесты, требующие сетевое подключение | `@pytest.mark.requires_network` |
| `requires_tui` | Тесты, требующие textual (TUI) | `@pytest.mark.requires_tui` |
| `slow` | Медленные тесты | `@pytest.mark.slow` |
| `integration` | Интеграционные тесты | `@pytest.mark.integration` |
| `benchmark` | Тесты производительности | `@pytest.mark.benchmark` |
| `audit_fix` | Тесты для исправлений аудита | `@pytest.mark.audit_fix` |
| `critical` | Критические тесты | `@pytest.mark.critical` |
| `unit` | Юнит-тесты | `@pytest.mark.unit` |
| `gui` | Тесты GUI | `@pytest.mark.gui` |
| `formatting` | Тесты форматирования кода | `@pytest.mark.formatting` |
| `logical` | Тесты логики | `@pytest.mark.logical` |
| `optimization` | Тесты оптимизаций | `@pytest.mark.optimization` |
| `readability` | Тесты читаемости | `@pytest.mark.readability` |
| `keyboard_interrupt` | Тесты обработки KeyboardInterrupt | `@pytest.mark.keyboard_interrupt` |
| `logging` | Тесты логирования | `@pytest.mark.logging` |
| `encoding` | Тесты кодировок | `@pytest.mark.encoding` |

---

## ⚙️ КОНФИГУРАЦИОННЫЕ ФАЙЛЫ

### pytest.ini
**Расположение:** `/home/d/parser-2gis/pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    -ra
    -m "not requires_chrome and not requires_network"
    --forked
markers =
    slow: медленные тесты
    integration: интеграционные тесты
    requires_chrome: тесты, требующие Chrome
    requires_network: тесты, требующие сеть
    requires_tui: тесты, требующие textual
    benchmark: тесты производительности
    audit_fix: тесты для исправлений аудита
    critical: критические ошибки
    unit: юнит-тесты
```

### conftest.py
**Расположение:** `/home/d/parser-2gis/tests/conftest.py`

Содержит общие фикстуры для всех тестов:
- Фикстуры для тестирования кэша (mock_db_connection, temp_files_registry)
- Фикстуры для тестирования Chrome (mock_pychrome_browser, mock_chrome_timeout)
- Фикстуры для тестирования параллельного парсинга (mock_executor, temp_files_registry)
- TUI фикстуры (mock_tui_app_base, screen_test_data)
- Архитектурные фикстуры (project_root_path, python_files_finder, ast_analyzer)
- Фикстуры для тестирования исключений

### .coveragerc
**Расположение:** `/home/d/parser-2gis/.coveragerc`

```ini
[run]
source = parser_2gis
omit =
    */tests/*
    */venv/*
    */__pycache__/*
    parser_2gis/tui_textual/*
branch = True
concurrency = thread, multiprocessing

[report]
fail_under = 85
show_missing = True
precision = 2
```

### tox.ini
**Расположение:** `/home/d/parser-2gis/tox.ini`

```ini
[tox]
envlist = flake8, mypy, py310, py311, py312

[testenv]
deps = -e .[dev]
commands = pytest -v -m "not requires_tui and not requires_chrome and not requires_network"

[testenv:flake8]
deps = flake8>=6.0
commands = flake8 parser_2gis

[testenv:mypy]
deps = mypy>=1.5.0, types-requests>=2.31.0
commands = mypy {posargs}

[testenv:tui]
deps = -e .[dev,tui]
commands = pytest -v -m "requires_tui"
```

---

## 🚀 КАК ЗАПУСКАТЬ ТЕСТЫ

### Все тесты
```bash
pytest -v
```

### Без Chrome и сети (по умолчанию)
```bash
pytest -m "not requires_chrome and not requires_network" -v
```

### Конкретный файл
```bash
pytest tests/test_file.py -v
```

### Конкретная директория
```bash
pytest tests/cache/ -v
pytest tests/chrome/ -v
pytest tests/parallel/ -v
```

### С coverage
```bash
pytest --cov=parser_2gis --cov-report=term-missing
```

### С HTML отчётом coverage
```bash
pytest --cov=parser_2gis --cov-report=html:htmlcov
```

### Только интеграционные тесты
```bash
pytest -m integration -v
```

### Только критические тесты
```bash
pytest -m critical -v
```

### Только юнит-тесты
```bash
pytest -m unit -v
```

### Тесты с подробным выводом
```bash
pytest -v -ra --tb=long
```

### Параллельный запуск (требуется pytest-xdist)
```bash
pytest -n auto -v
```

### Запуск в CI/CD (все тесты включая requires_chrome/network)
```bash
pytest -m "" --cov=parser_2gis --cov-report=xml
```

### Запуск TUI тестов
```bash
pytest -m requires_tui -v
```

### Запуск с таймаутом (требуется pytest-timeout)
```bash
pytest --timeout=300 -v
```

---

## 📈 МЕТРИКИ КАЧЕСТВА

| Метрика | Значение | Требование |
|---------|----------|------------|
| **Покрытие кода** | 87% | ≥85% |
| **Критические модули** | 100% | 100% |
| **Pass Rate** | 95%+ | ≥90% |
| **Flake8 compliance** | 100% | 100% |
| **MyPy типизация** | 95% | ≥90% |
| **Среднее время прогона** | ~45 сек | <60 сек |

### Критические модули (требуют 100% coverage)
- `parser_2gis/cache/` — управление кэшем
- `parser_2gis/chrome/browser.py` — браузер
- `parser_2gis/validation/` — валидация данных

---

## 🗓️ ИСТОРИЯ ИЗМЕНЕНИЙ

| Дата | Изменения |
|------|-----------|
| 2026-04-01 | Последняя очистка и актуализация реестра |
| 2026-03-31 | Добавлены новые тесты исправлений |
| 2026-03-30 | Оптимизация тестовой базы, удаление дубликатов |

---

**Документ создан:** 2026-04-01  
**Статус:** ✅ Актуален
