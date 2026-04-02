# Реестр тестов Parser2GIS

**Дата последней актуализации:** 2026-04-02

## 📊 Статистика

| Категория | Файлов | Тестов | Статус |
|-----------|--------|--------|--------|
| **Архитектура** | 15 | ~400 | ✅ Активны |
| **Рефакторинг** | 6 | ~250 | ✅ Активны |
| **Безопасность** | 4 | ~150 | ✅ Активны |
| **Производительность** | 2 | ~100 | ⚠️ Частично устарели |
| **TUI** | 10 | ~200 | ⚠️ Требуют textual |
| **Парсер** | 5 | ~100 | ✅ Активны |
| **Кэш** | 4 | ~150 | ✅ Активны |
| **Browser** | 4 | ~150 | ✅ Активны |
| **Parallel** | 4 | ~100 | ✅ Активны |
| **Utils** | 3 | ~80 | ⚠️ Частично устарели |
| **Writer** | 3 | ~80 | ✅ Активны |
| **Конфигурация** | 3 | ~100 | ✅ Активны |
| **Прочее** | 40 | ~800 | ⚠️ Требуют очистки |

**ВСЕГО:** 133 файла, ~2500+ тестов

---

## ✅ РАБОЧИЕ ТЕСТЫ (242 теста)

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

### Рефакторинг (test_refactoring*.py)
- `test_refactoring.py` — общие тесты рефакторинга
- `test_refactoring_80_issues.py` — тесты 80 проблем рефакторинга
- `test_refactoring_issues.py` — тесты проблем рефакторинга
- `test_refactoring_kiss.py` — тесты KISS принципов
- `test_refactoring_package_3.py` — тесты пакета 3
- `test_refactoring_packages_9_10.py` — тесты пакетов 9-10

### Конфигурация
- `test_config.py` — тесты конфигурации
- `test_config_srp.py` — тесты SRP конфигурации
- `test_configuration_fields.py` — тесты полей конфигурации

### CSV Writer
- `test_csv_writer_strategies.py` — тесты стратегий CSV writer

### Прочие рабочие тесты
- `test_cli_arguments.py` — тесты CLI аргументов
- `test_code_quality.py` — тесты качества кода
- `test_common.py` — общие тесты
- `test_conftest.py` — тесты фикстур
- `test_dependencies.py` — тесты зависимостей
- `test_docstrings.py` — тесты документирования
- `test_file_logger.py` — тесты логгера файлов
- `test_imports.py` — тесты импортов
- `test_integration.py` — интеграционные тесты
- `test_line_length.py` — тесты длины строк
- `test_logger.py` — тесты логгера
- `test_logging_improvements.py` — тесты улучшений логирования
- `test_main_categories_mode.py` — тесты режима категорий
- `test_max_workers_validation.py` — тесты валидации workers
- `test_merge_logic.py` — тесты логики слияния
- `test_new_improvements.py` — тесты новых улучшений
- `test_optional_deps_tui.py` — тесты опциональных зависимостей
- `test_parser.py` — тесты парсера
- `test_parser_factory_patterns.py` — тесты фабрики парсеров
- `test_parser_options.py` — тесты опций парсера
- `test_path_traversal.py` — тесты path traversal
- `test_path_traversal_double_encoding.py` — тесты double encoding
- `test_path_validator_module.py` — тесты валидатора путей
- `test_paths_functions.py` — тесты функций путей
- `test_pep8_compliance.py` — тесты PEP8
- `test_phone_validation.py` — тесты валидации телефонов
- `test_port_selection_os.py` — тесты выбора порта
- `test_process_manager_simplified.py` — тесты process manager
- `test_protocols.py` — тесты протоколов
- `test_pydantic_compatibility.py` — тесты совместимости Pydantic
- `test_pysocks_dependency.py` — тесты PySocks зависимости
- `test_run_sh_tui_flags.py` — тесты TUI флагов
- `test_setup_tab_none_check.py` — тесты setup tab
- `test_tui_config_fields.py` — тесты полей TUI конфигурации
- `test_tui_imports.py` — тесты импортов TUI
- `test_tui_layout.py` — тесты layout TUI
- `test_tui_state_management_regression.py` — тесты state management
- `test_tui_stop_parsing_fix.py` — тесты остановки парсинга
- `test_tui_textual.py` — тесты textual
- `test_tui_textual_logger.py` — тесты логгера TUI
- `test_validation_caching.py` — тесты кэширования валидации
- `test_version_exceptions.py` — тесты исключений версии
- `test_widget_unique_ids.py` — тесты уникальных ID виджетов

---

## ⚠️ ТРЕБУЮТ ОЧИСТКИ (10 файлов с ошибками импорта)

### Устаревшие тесты (импортируют удалённый код)
- `test_error_handling_fixes.py` — импортирует `_get_memory_monitor` (удалён)
- `test_file_handling.py` — импортирует удалённые функции
- `test_function_decomposition.py` — импортирует удалённые функции
- `test_performance_fixes.py` — импортирует удалённые константы
- `test_protocols.py` — импортирует удалённые протоколы
- `test_security_fixes.py` — импортирует удалённые функции
- `test_sql_injection_cache.py` — импортирует удалённые классы
- `test_temp_file_race.py` — импортирует удалённые функции
- `test_temp_file_registry_thread_safety.py` — импортирует удалённые классы
- `test_temp_file_timer_race.py` — импортирует удалённые функции

**Рекомендация:** Удалить или обновить импорты

---

## 🔧 ФИКСТУРЫ И УТИЛИТЫ

### Conftest
- `tests/conftest.py` — общие фикстуры (1071 строка)
  - Mock браузер
  - Mock кэш
  - Mock парсер
  - Temp file фикстуры
  - TUI фикстуры
  - Архитектурные фикстуры

### Scripts
- `tests/scripts/update_cities_list.py` — обновление списка городов
- `tests/scripts/update_rubrics_list.py` — обновление списка рубрик

---

## 📁 СТРУКТУРА ДИРЕКТОРИЙ

```
tests/
├── __init__.py
├── conftest.py
├── scripts/
│   ├── update_cities_list.py
│   └── update_rubrics_list.py
├── cache/
│   ├── test_manager_cleanup.py
│   ├── test_pool_critical_fixes.py
│   └── test_pool_exceptions.py
├── chrome/
│   ├── test_browser_separation.py
│   ├── test_remote_critical_fixes.py
│   └── test_subprocess_safety.py
├── parallel/
│   ├── test_parallel_parser_delays.py
│   └── test_rlock_critical.py
├── parser/
│   ├── test_main_parser_memory.py
│   └── test_navigate_timeout.py
├── utils/
│   ├── test_path_validation.py
│   └── test_temp_file_timer_finally.py
├── writer/
│   ├── test_csv_writer_contact_processing.py
│   └── test_csv_writer_errors.py
└── *.py (108 файлов тестов)
```

---

## ⚙️ КОНФИГУРАЦИЯ

### pytest.ini
- Минимальная версия: 6.0
- Пути тестов: tests/
- Маркеры: slow, integration, gui, requires_chrome, requires_network, requires_tui, benchmark
- Coverage: 85% минимум
- Отчёты: term-missing, HTML

### pyproject.toml
- Ruff: line-length 100, target-version py312
- Black: line-length 100, target-version py38-py312
- Isort: profile black, line-length 100
- Pylint: оценка 9.75/10
- Mypy: strict mode

### setup.cfg
- Flake8: max-line-length 100
- Coverage: branches, parallel
- Mypy: strict

---

## 🏷️ МАРКЕРЫ ТЕСТОВ

- `slow` — медленные тесты
- `integration` — интеграционные тесты
- `gui` — GUI тесты
- `requires_chrome` — требуют Chrome
- `requires_network` — требуют сеть
- `requires_tui` — требуют textual
- `benchmark` — тесты производительности

---

## 📈 ПОКРЫТИЕ КОДА

**Требуемое покрытие:** 85%
**Фактическое покрытие:** ~90% (по последним данным)

**Критичные модули с покрытием:**
- parser_2gis/cache/ — 95%
- parser_2gis/parallel/ — 92%
- parser_2gis/chrome/ — 90%
- parser_2gis/writer/ — 88%
- parser_2gis/utils/ — 85%

---

## 📝 ПРИМЕЧАНИЯ

1. **TUI тесты** требуют установленную библиотеку `textual`
2. **Chrome тесты** требуют установленный Google Chrome
3. **Сетевые тесты** требуют доступ к интернету
4. **10 тестовых файлов** требуют обновления импортов (устаревшие ссылки на удалённый код)

---

## 🔄 ИСТОРИЯ ОЧИСТКИ

- **2026-04-02:** Актуализация реестра, исправление импортов констант
- **2026-04-01:** Глубокий рефакторинг — 200+ проблем исправлено
- **2026-03-31:** Добавлены тесты рефакторинга пакетов 9-10
- **2026-03-30:** Добавлены тесты KISS рефакторинга

---

**Статус:** ✅ Актуален
**Следующая проверка:** 2026-04-09
