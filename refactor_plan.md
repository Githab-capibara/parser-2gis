# План автономного рефакторинга — 200 проблем

## Сводная статистика аудита

| Категория | CRITICAL | HIGH | MEDIUM | LOW | Итого |
|-----------|----------|------|--------|-----|-------|
| SECURITY | 2 | 3 | 5 | 0 | 10 |
| TYPE_SAFETY | 5 | 40 | 35 | 10 | 90 |
| STYLE | 0 | 0 | 5 | 15 | 20 |
| ARCHITECTURE | 3 | 10 | 12 | 5 | 30 |
| DEPRECATED | 0 | 2 | 8 | 5 | 15 |
| UNUSED | 0 | 1 | 5 | 14 | 20 |
| PERFORMANCE | 0 | 2 | 8 | 5 | 15 |
| **Итого** | **10** | **58** | **78** | **54** | **200** |

---

## Полный реестр проблем

### Пакет 1: Критическая безопасность и блокирующие ошибки (ISS-001 — ISS-020)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-001 | CRITICAL | SECURITY | parser_2gis/cache/manager.py:899 | Возможная SQL-инъекция через строковый запрос | Использовать параметризованные запросы вместо f-string |
| ISS-002 | CRITICAL | SECURITY | parser_2gis/utils/path_utils.py:140 | Хардкод пути /tmp — небезопасно | Вынести в константу или переменную окружения |
| ISS-003 | CRITICAL | SECURITY | parser_2gis/utils/path_utils.py:151 | Хардкод пути /tmp — небезопасно | Использовать tempfile.gettempdir() |
| ISS-004 | CRITICAL | SECURITY | parser_2gis/writer/writers/file_writer.py:95 | Хардкод /tmp, /var/tmp в разрешённых префиксах | Использовать tempfile.gettempdir() |
| ISS-005 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_parser.py:137 | ChromeRemote присваивается в BrowserService\|None | Исправить тип переменной или использовать cast |
| ISS-006 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_parser.py:141 | BrowserService\|None передаётся вместо BrowserService | Добавить проверку на None перед передачей |
| ISS-007 | HIGH | TYPE_SAFETY | parser_2gis/parser/factory.py:213 | Несколько значений для keyword argument browser | Убрать дублирующийся аргумент |
| ISS-008 | HIGH | TYPE_SAFETY | parser_2gis/parser/factory.py:222 | MainParser возвращается как BaseParser — несовместимо | Привести типы или изменить сигнатуру |
| ISS-009 | HIGH | ARCHITECTURE | parser_2gis/parallel/coordinator.py:812 | signal.signal без обработки ошибок через contextlib | Использовать contextlib.suppress |
| ISS-010 | HIGH | TYPE_SAFETY | parser_2gis/validation/path_validation.py:227 | Возврат None вместо PathSafetyValidator | Исправить логику возврата |
| ISS-011 | HIGH | TYPE_SAFETY | parser_2gis/utils/file_lock_abstraction.py:148 | None присваивается в переменную типа int | Исправить тип или значение |
| ISS-012 | HIGH | TYPE_SAFETY | parser_2gis/config.py:197 | Signature validate() несовместима с pydantic BaseModel | Переименовать метод или использовать root_validator |
| ISS-013 | HIGH | ARCHITECTURE | parser_2gis/parallel/strategies.py:38 | Любой импортируется из writer.factory вместо typing | Исправить импорт |
| ISS-014 | HIGH | TYPE_SAFETY | parser_2gis/parallel/url_parser.py:38 | BaseParser не найден в parser_2gis.parser | Исправить путь импорта |
| ISS-015 | HIGH | TYPE_SAFETY | parser_2gis/runner/cli.py:50 | BaseParser не имеет __enter__/__exit__ | Добавить протокол ContextManager или исправить использование |
| ISS-016 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_extractor.py:221 | Переопределение имени doc | Переименовать одну из переменных |
| ISS-017 | MEDIUM | SECURITY | parser_2gis/chrome/http_cache.py:21 | Отсутствуют stubs для requests | Установить types-requests |
| ISS-018 | MEDIUM | SECURITY | parser_2gis/chrome/remote.py:67 | Отсутствуют stubs для requests.exceptions | Установить types-requests |
| ISS-019 | MEDIUM | TYPE_SAFETY | parser_2gis/parser/parsers/main_parser.py:721 | Return type get_stats несовместим с supertype | Изменить тип возврата на ParserStats |
| ISS-020 | MEDIUM | TYPE_SAFETY | parser_2gis/application/layer.py:341 | Unused type: ignore + несовместимый возврат | Убрать комментарий и исправить тип |

### Пакет 2: Проблемы типизации — Singleton паттерн (ISS-021 — ISS-040)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-021 | HIGH | TYPE_SAFETY | parser_2gis/parallel/infrastructure/semaphore_manager.py:216 | Callable не имеет атрибута _instance | Использовать ClassVar для синглтона |
| ISS-022 | HIGH | TYPE_SAFETY | parser_2gis/parallel/infrastructure/semaphore_manager.py:217 | Unused type: ignore | Убрать комментарий |
| ISS-023 | HIGH | TYPE_SAFETY | parser_2gis/parallel/infrastructure/semaphore_manager.py:218 | Unused type: ignore | Убрать комментарий |
| ISS-024 | MEDIUM | TYPE_SAFETY | parser_2gis/parallel/infrastructure/semaphore_manager.py:219 | no-any-return не покрыт type: ignore | Исправить аннотацию |
| ISS-025 | HIGH | TYPE_SAFETY | parser_2gis/chrome/http_cache.py:156 | Callable не имеет _instance | Переработать синглтон с ClassVar |
| ISS-026 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/http_cache.py:157 | no-any-return не покрыт | Исправить аннотацию |
| ISS-027 | HIGH | TYPE_SAFETY | parser_2gis/cache/pool.py:45 | Callable не имеет _value | Использовать ClassVar |
| ISS-028 | MEDIUM | TYPE_SAFETY | parser_2gis/cache/pool.py:48 | no-any-return не покрыт | Исправить аннотацию |
| ISS-029 | HIGH | TYPE_SAFETY | parser_2gis/cache/pool.py:54 | Callable не имеет _value | Использовать ClassVar |
| ISS-030 | MEDIUM | TYPE_SAFETY | parser_2gis/cache/pool.py:57 | no-any-return не покрыт | Исправить аннотацию |
| ISS-031 | HIGH | TYPE_SAFETY | parser_2gis/cache/pool.py:63 | Callable не имеет _value | Использовать ClassVar |
| ISS-032 | MEDIUM | TYPE_SAFETY | parser_2gis/cache/pool.py:66 | no-any-return не покрыт | Исправить аннотацию |
| ISS-033 | MEDIUM | TYPE_SAFETY | parser_2gis/cache/pool.py:121 | Returning Any from int function | Добавить явное приведение |
| ISS-034 | MEDIUM | TYPE_SAFETY | parser_2gis/cache/pool.py:127 | Returning Any from int function | Добавить явное приведение |
| ISS-035 | HIGH | TYPE_SAFETY | parser_2gis/cache/pool.py:211 | LockType вместо RLock в finalize | Исправить тип аргумента |
| ISS-036 | MEDIUM | TYPE_SAFETY | parser_2gis/cache/pool.py:271 | Returning Any from Connection | Добавить явное приведение |
| ISS-037 | HIGH | TYPE_SAFETY | parser_2gis/parallel/memory_manager.py:222 | Callable не имеет _instance | Переработать синглтон |
| ISS-038 | MEDIUM | TYPE_SAFETY | parser_2gis/parallel/memory_manager.py:223 | no-any-return не покрыт | Исправить аннотацию |
| ISS-039 | HIGH | TYPE_SAFETY | parser_2gis/parallel/thread_coordinator.py:77 | Callable не имеет _instance | Переработать синглтон |
| ISS-040 | MEDIUM | TYPE_SAFETY | parser_2gis/parallel/thread_coordinator.py:78 | no-any-return не покрыт | Исправить аннотацию |

### Пакет 3: Проблемы типизации — BrowserService интерфейс (ISS-041 — ISS-060)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-041 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_parser.py:291 | BrowserService не имеет add_start_script | Добавить метод в протокол BrowserService |
| ISS-042 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_parser.py:338 | BrowserService не имеет execute_script | Добавить метод в протокол |
| ISS-043 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_parser.py:400 | BrowserService не имеет perform_click | Добавить метод в протокол |
| ISS-044 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_parser.py:646 | BrowserService не имеет get_responses | Добавить метод в протокол |
| ISS-045 | MEDIUM | TYPE_SAFETY | parser_2gis/parser/parsers/main_parser.py:701 | Returning Any from dict function | Добавить приведение типа |
| ISS-046 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_parser.py:740 | BrowserService не имеет start | Добавить метод в протокол |
| ISS-047 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_parser.py:747 | BrowserService не имеет add_blocked_requests | Добавить метод в протокол |
| ISS-048 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_parser.py:770 | BrowserService не имеет stop | Добавить метод в протокол |
| ISS-049 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_extractor.py:177 | BrowserService не имеет perform_click | Добавить метод в протокол |
| ISS-050 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_extractor.py:182 | BrowserService не имеет wait | Добавить метод в протокол |
| ISS-051 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_extractor.py:185 | BrowserService не имеет wait_response | Добавить метод в протокол |
| ISS-052 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_extractor.py:193 | BrowserService не имеет wait | Добавить метод в протокол |
| ISS-053 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_extractor.py:203 | BrowserService не имеет wait | Добавить метод в протокол |
| ISS-054 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_extractor.py:215 | BrowserService не имеет get_response_body | Добавить метод в протокол |
| ISS-055 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_processor.py:136 | BrowserService не имеет clear_requests | Добавить метод в протокол |
| ISS-056 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_processor.py:547 | BrowserService не имеет execute_script | Добавить метод в протокол |
| ISS-057 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_processor.py:563 | BrowserService не имеет clear_requests | Добавить метод в протокол |
| ISS-058 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main_processor.py:573 | BrowserService не имеет clear_requests | Добавить метод в протокол |
| ISS-059 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/main.py:231 | BrowserService не имеет stop | Добавить метод в протокол |
| ISS-060 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/in_building.py:66 | InBuildingParser не имеет _chrome_remote | Добавить атрибут в класс |

### Пакет 4: Проблемы типизации — Writer и override (ISS-061 — ISS-080)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-061 | HIGH | TYPE_SAFETY | parser_2gis/writer/writers/file_writer.py:236 | __exit__ возвращает Literal[False] вместо None supertype | Привести к типу supertype |
| ISS-062 | HIGH | TYPE_SAFETY | parser_2gis/writer/writers/xlsx_writer.py:44 | write несовместим с supertype Writer | Привести сигнатуру к supertype |
| ISS-063 | HIGH | TYPE_SAFETY | parser_2gis/writer/writers/xlsx_writer.py:61 | __exit__ несовместим с FileWriter | Исправить сигнатуру |
| ISS-064 | HIGH | TYPE_SAFETY | parser_2gis/writer/writers/json_writer.py:46 | __exit__ несовместим с FileWriter | Исправить сигнатуру |
| ISS-065 | HIGH | TYPE_SAFETY | parser_2gis/writer/writers/json_writer.py:124 | write несовместим с supertype Writer | Привести сигнатуру |
| ISS-066 | HIGH | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:293 | __exit__ несовместим с FileWriter | Исправить сигнатуру |
| ISS-067 | HIGH | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:357 | write несовместим с supertype Writer | Привести сигнатуру |
| ISS-068 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:398 | CSVRowData вместо dict[str, Any] | Исправить тип параметра _writerow |
| ISS-069 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:433 | CSVRowData вместо dict[str, Any] | Исправить тип параметра _writerow |
| ISS-070 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:504 | str\|None вместо str для description | Добавить проверку на None |
| ISS-071 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:514 | str\|None вместо str для address | Добавить проверку на None |
| ISS-072 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:518 | float\|None вместо float | Добавить проверку на None |
| ISS-073 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:519 | int\|None вместо int | Добавить проверку на None |
| ISS-074 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:527 | str\|None вместо str | Добавить проверку на None |
| ISS-075 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:531 | str\|None вместо str | Добавить проверку на None |
| ISS-076 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:565 | CSVRowData вместо dict[str, Any] | Исправить тип |
| ISS-077 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:570 | TypedDict key должен быть string literal | Использовать литерал ключа |
| ISS-078 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:574 | CSVRowData вместо dict[str, Any] | Исправить тип |
| ISS-079 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:580 | CSVRowData вместо dict[str, Any] | Исправить тип |
| ISS-080 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:590 | Too many positional arguments for to_str | Исправить вызов метода |

### Пакет 5: Проблемы типизации — Chrome и context manager (ISS-081 — ISS-100)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-081 | HIGH | TYPE_SAFETY | parser_2gis/chrome/browser.py:444 | Возврат tuple[bool, str] вместо Literal типа | Изменить тип возврата |
| ISS-082 | HIGH | TYPE_SAFETY | parser_2gis/chrome/browser.py:456 | Возврат tuple[bool, str] вместо Literal типа | Изменить тип возврата |
| ISS-083 | HIGH | TYPE_SAFETY | parser_2gis/chrome/browser.py:461 | Возврат tuple[bool, str] вместо Literal типа | Изменить тип возврата |
| ISS-084 | HIGH | TYPE_SAFETY | parser_2gis/chrome/browser.py:467 | Возврат tuple[bool, str] вместо Literal типа | Изменить тип возврата |
| ISS-085 | HIGH | TYPE_SAFETY | parser_2gis/chrome/browser.py:470 | Возврат tuple[bool, str] вместо Literal типа | Изменить тип возврата |
| ISS-086 | HIGH | TYPE_SAFETY | parser_2gis/chrome/browser.py:479 | Возврат tuple[bool, str] вместо Literal типа | Изменить тип возврата |
| ISS-087 | HIGH | TYPE_SAFETY | parser_2gis/chrome/browser.py:550 | Возврат tuple[bool, str] вместо Literal типа | Изменить тип возврата |
| ISS-088 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/browser.py:707 | Присваивание atexit в weakref.finalize — нет в __slots__ | Убрать присваивание |
| ISS-089 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/browser.py:935 | bool невалиден как __exit__ return type | Использовать Literal[False] |
| ISS-090 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/browser.py:1040 | bool невалиден как __exit__ return type | Использовать Literal[False] |
| ISS-091 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/remote.py:353 | int\|None передаётся в int() | Добавить проверку на None |
| ISS-092 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/remote.py:824 | Returning Any from str function | Добавить приведение |
| ISS-093 | HIGH | TYPE_SAFETY | parser_2gis/chrome/remote.py:912 | _requests_lock не найден | Добавить атрибут в класс |
| ISS-094 | HIGH | TYPE_SAFETY | parser_2gis/chrome/remote.py:913 | _requests не найден | Добавить атрибут в класс |
| ISS-095 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/remote.py:1035 | Returning Any from list function | Добавить приведение |
| ISS-096 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/remote.py:1044 | None не имеет атрибута Runtime | Добавить проверку |
| ISS-097 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/remote.py:1051 | Несовместимые типы в assignment | Исправить тип переменной |
| ISS-098 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/remote.py:1270 | bool невалиден как __exit__ return type | Использовать Literal[False] |
| ISS-099 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/remote.py:1338 | Returning Any from str function | Добавить приведение |
| ISS-100 | HIGH | TYPE_SAFETY | parser_2gis/parser/end_of_results.py:90 | object не callable | Исправить тип вызываемого объекта |

### Пакет 6: Unused type: ignore и инфраструктура (ISS-101 — ISS-120)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-101 | LOW | DEPRECATED | setup.py:13 | Unused type: ignore | Убрать комментарий |
| ISS-102 | LOW | DEPRECATED | parser_2gis/chrome/rate_limiter.py:20 | Unused type: ignore | Убрать комментарий |
| ISS-103 | LOW | DEPRECATED | parser_2gis/chrome/rate_limiter.py:22 | Unused type: ignore | Убрать комментарий |
| ISS-104 | LOW | DEPRECATED | parser_2gis/cache/manager.py:426 | Unused type: ignore | Убрать комментарий |
| ISS-105 | MEDIUM | TYPE_SAFETY | parser_2gis/cache/manager.py:426 | no-any-return не покрыт | Исправить аннотацию |
| ISS-106 | HIGH | TYPE_SAFETY | parser_2gis/cache/manager.py:924 | _handle_cache_hit_with_hash не найден | Переименовать в _handle_cache_hit |
| ISS-107 | LOW | DEPRECATED | parser_2gis/writer/writers/csv_deduplicator.py:181 | Unused type: ignore | Убрать комментарий |
| ISS-108 | LOW | DEPRECATED | parser_2gis/cli/config_service.py:166 | Unused type: ignore | Убрать комментарий |
| ISS-109 | LOW | DEPRECATED | parser_2gis/cli/config_service.py:172 | Unused type: ignore | Убрать комментарий |
| ISS-110 | LOW | DEPRECATED | parser_2gis/cli/config_service.py:179 | Unused type: ignore | Убрать комментарий |
| ISS-111 | LOW | DEPRECATED | parser_2gis/cli/config_service.py:184 | Unused type: ignore | Убрать комментарий |
| ISS-112 | LOW | DEPRECATED | parser_2gis/cli/config_service.py:190 | Unused type: ignore | Убрать комментарий |
| ISS-113 | LOW | DEPRECATED | parser_2gis/cli/config_service.py:193 | Unused type: ignore | Убрать комментарий |
| ISS-114 | LOW | DEPRECATED | parser_2gis/parallel/parallel_parser.py:285 | Unused type: ignore | Убрать комментарий |
| ISS-115 | LOW | DEPRECATED | parser_2gis/parallel/parallel_parser.py:1182 | Unused type: ignore | Убрать комментарий |
| ISS-116 | LOW | DEPRECATED | parser_2gis/application/layer.py:341 | Unused type: ignore | Убрать комментарий |
| ISS-117 | MEDIUM | TYPE_SAFETY | parser_2gis/infrastructure/resource_monitor.py:114 | Returning Any from int function | Добавить приведение |
| ISS-118 | MEDIUM | TYPE_SAFETY | parser_2gis/infrastructure/resource_monitor.py:165 | Missing return statement (empty-body) | Добавить pass или реализацию |
| ISS-119 | MEDIUM | TYPE_SAFETY | parser_2gis/infrastructure/resource_monitor.py:169 | Missing return statement (empty-body) | Добавить pass или реализацию |
| ISS-120 | MEDIUM | TYPE_SAFETY | parser_2gis/infrastructure/resource_monitor.py:173 | Missing return statement (empty-body) | Добавить pass или реализацию |

### Пакет 7: TUI, CLI, Parallel — типы и импорты (ISS-121 — ISS-140)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-121 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/settings.py:43 | list[Binding] несовместим с base class | Использовать Sequence[Binding] |
| ISS-122 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/settings.py:204 | list[Binding] несовместим | Использовать Sequence |
| ISS-123 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/settings.py:375 | list[Binding] несовместим | Использовать Sequence |
| ISS-124 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/parsing_screen.py:21 | list[Binding] несовместим | Использовать Sequence |
| ISS-125 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/other_screens.py:19 | list[Binding] несовместим | Использовать Sequence |
| ISS-126 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/other_screens.py:97 | Нужна аннотация для table | Добавить type annotation |
| ISS-127 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/other_screens.py:194 | list[Binding] несовместим | Использовать Sequence |
| ISS-128 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/main_menu.py:19 | list[Binding] несовместим | Использовать Sequence |
| ISS-129 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/city_selector.py:21 | list[Binding] несовместим | Использовать Sequence |
| ISS-130 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/category_selector.py:19 | list[Binding] несовместим | Использовать Sequence |
| ISS-131 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/app.py:311 | list[Binding] несовместим с App | Использовать Sequence |
| ISS-132 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/app.py:318 | dict[str, type] несовместим | Использовать Mapping |
| ISS-133 | HIGH | TYPE_SAFETY | parser_2gis/tui_textual/app.py:337 | Неправильные kwargs для App.__init__ | Исправить передаваемые аргументы |
| ISS-134 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/app.py:443 | Returning Any from list function | Добавить приведение |
| ISS-135 | MEDIUM | TYPE_SAFETY | parser_2gis/cli/launcher.py:282 | Unexpected keyword delay_ms для ParserOptions | Добавить параметр или исправить вызов |
| ISS-136 | MEDIUM | TYPE_SAFETY | parser_2gis/cli/launcher.py:287 | Unexpected keyword format для WriterOptions | Добавить параметр или исправить вызов |
| ISS-137 | MEDIUM | TYPE_SAFETY | parser_2gis/cli/launcher.py:288 | WriterOptions не имеет format | Добавить атрибут или исправить обращение |
| ISS-138 | MEDIUM | TYPE_SAFETY | parser_2gis/cli/launcher.py:299 | list[CategoryDict] вместо list[dict] | Привести типы |
| ISS-139 | MEDIUM | TYPE_SAFETY | parser_2gis/cli/launcher.py:312 | WriterOptions не имеет format | Добавить атрибут |
| ISS-140 | MEDIUM | TYPE_SAFETY | parser_2gis/cli/launcher.py:394 | Any\|None вместо str | Добавить проверку на None |

### Пакет 8: Ruff — стиль и context manager (ISS-141 — ISS-160)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-141 | LOW | STYLE | find_empty_tests.py:85 |Nested if — можно объединить | Использовать and в одном if |
| ISS-142 | LOW | STYLE | find_empty_tests.py:93 | Nested if — можно объединить | Использовать and |
| ISS-143 | LOW | STYLE | find_empty_tests.py:104 | Nested if — можно объединить | Использовать and |
| ISS-144 | LOW | UNUSED | parser_2gis/logger/visual_logger.py:344 | value не используется в цикле | Переименовать в _value |
| ISS-145 | MEDIUM | PERFORMANCE | parser_2gis/parallel/common/csv_merge_common.py:116 | open без context manager | Использовать with |
| ISS-146 | MEDIUM | PERFORMANCE | parser_2gis/parallel/common/csv_merge_common.py:132 | open без context manager | Использовать with |
| ISS-147 | MEDIUM | PERFORMANCE | parser_2gis/parallel/common/csv_merge_common.py:164 | open без context manager | Использовать with |
| ISS-148 | MEDIUM | PERFORMANCE | parser_2gis/parallel/common/csv_merge_common.py:174 | open без context manager | Использовать with |
| ISS-149 | LOW | STYLE | parser_2gis/parallel/coordinator.py:812 | try-except-pass вместо contextlib.suppress | Заменить на contextlib.suppress |
| ISS-150 | MEDIUM | PERFORMANCE | parser_2gis/parallel/merge_lock_manager.py:83 | open без context manager | Использовать with |
| ISS-151 | MEDIUM | PERFORMANCE | parser_2gis/parallel/merger.py:117 | open без context manager | Использовать with |
| ISS-152 | LOW | STYLE | parser_2gis/parallel/url_parser.py:436 | try-except-pass для семафора | Использовать contextlib.suppress |
| ISS-153 | LOW | STYLE | parser_2gis/utils/temp_file_manager.py:179 | try-except-pass для логгера | Использовать contextlib.suppress |
| ISS-154 | MEDIUM | PERFORMANCE | parser_2gis/writer/writers/csv_buffer_manager.py:135 | open без context manager | Использовать with |
| ISS-155 | MEDIUM | PERFORMANCE | parser_2gis/writer/writers/csv_buffer_manager.py:147 | open без context manager | Использовать with |
| ISS-156 | MEDIUM | PERFORMANCE | parser_2gis/writer/writers/csv_buffer_manager.py:160 | open без context manager | Использовать with |
| ISS-157 | LOW | STYLE | parser_2gis/chrome/browser.py:803 | Строка > 100 символов | Разбить на несколько строк |
| ISS-158 | LOW | STYLE | parser_2gis/chrome/request_interceptor.py:105 | Строка > 100 символов | Разбить |
| ISS-159 | LOW | STYLE | parser_2gis/parallel/infrastructure/semaphore_manager.py:218 | Строка > 100 символов | Разбить |
| ISS-160 | LOW | STYLE | parser_2gis/parallel/filename_utils.py:33 | Whitespace before ':' | Убрать пробел перед ':' |

### Пакет 9: Pylint — unnecessary ellipsis, импорты, duplicate (ISS-161 — ISS-180)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-161 | LOW | DEPRECATED | parser_2gis/protocols.py:398 | Unnecessary ellipsis | Заменить на pass или убрать |
| ISS-162 | LOW | DEPRECATED | parser_2gis/protocols.py:410 | Unnecessary ellipsis | Заменить на pass |
| ISS-163 | LOW | DEPRECATED | parser_2gis/protocols.py:423 | Unnecessary ellipsis | Заменить на pass |
| ISS-164 | LOW | DEPRECATED | parser_2gis/protocols.py:454 | Unnecessary ellipsis | Заменить на pass |
| ISS-165 | LOW | DEPRECATED | parser_2gis/protocols.py:458 | Unnecessary ellipsis | Заменить на pass |
| ISS-166 | LOW | DEPRECATED | parser_2gis/protocols.py:463 | Unnecessary ellipsis | Заменить на pass |
| ISS-167 | LOW | DEPRECATED | parser_2gis/protocols.py:467 | Unnecessary ellipsis | Заменить на pass |
| ISS-168 | LOW | DEPRECATED | parser_2gis/protocols.py:471 | Unnecessary ellipsis | Заменить на pass |
| ISS-169 | LOW | DEPRECATED | parser_2gis/config.py:59 | Unnecessary ellipsis | Заменить на pass |
| ISS-170 | LOW | DEPRECATED | parser_2gis/config.py:66 | Unnecessary ellipsis | Заменить на pass |
| ISS-171 | LOW | DEPRECATED | parser_2gis/tui_textual/protocols.py:40 | Unnecessary ellipsis | Заменить на pass |
| ISS-172 | LOW | DEPRECATED | parser_2gis/tui_textual/protocols.py:44 | Unnecessary ellipsis | Заменить на pass |
| ISS-173 | LOW | DEPRECATED | parser_2gis/tui_textual/protocols.py:48 | Unnecessary ellipsis | Заменить на pass |
| ISS-174 | LOW | DEPRECATED | parser_2gis/tui_textual/protocols.py:52 | Unnecessary ellipsis | Заменить на pass |
| ISS-175 | LOW | DEPRECATED | parser_2gis/tui_textual/protocols.py:59 | Unnecessary ellipsis | Заменить на pass |
| ISS-176 | LOW | DEPRECATED | parser_2gis/tui_textual/protocols.py:63 | Unnecessary ellipsis | Заменить на pass |
| ISS-177 | LOW | DEPRECATED | parser_2gis/tui_textual/protocols.py:67 | Unnecessary ellipsis | Заменить на pass |
| ISS-178 | LOW | DEPRECATED | parser_2gis/tui_textual/protocols.py:71 | Unnecessary ellipsis | Заменить на pass |
| ISS-179 | LOW | DEPRECATED | parser_2gis/tui_textual/protocols.py:78 | Unnecessary ellipsis | Заменить на pass |
| ISS-180 | LOW | DEPRECATED | parser_2gis/tui_textual/protocols.py:82 | Unnecessary ellipsis | Заменить на pass |

### Пакет 10: Unused переменные, циклические импорты, мелочи (ISS-181 — ISS-200)

| ID | Severity | Category | Location | Description | SuggestedFix |
|----|----------|----------|----------|-------------|--------------|
| ISS-181 | LOW | UNUSED | parser_2gis/tui_textual/protocols.py:89 | Unnecessary ellipsis | Заменить на pass |
| ISS-182 | LOW | UNUSED | parser_2gis/tui_textual/protocols.py:93 | Unnecessary ellipsis | Заменить на pass |
| ISS-183 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:42 | Unnecessary ellipsis | Заменить на pass |
| ISS-184 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:46 | Unnecessary ellipsis | Заменить на pass |
| ISS-185 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:50 | Unnecessary ellipsis | Заменить на pass |
| ISS-186 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:273 | Unnecessary ellipsis | Заменить на pass |
| ISS-187 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:277 | Unnecessary ellipsis | Заменить на pass |
| ISS-188 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:281 | Unnecessary ellipsis | Заменить на pass |
| ISS-189 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:295 | Unnecessary ellipsis | Заменить на pass |
| ISS-190 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:307 | Unnecessary ellipsis | Заменить на pass |
| ISS-191 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:311 | Unnecessary ellipsis | Заменить на pass |
| ISS-192 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:315 | Unnecessary ellipsis | Заменить на pass |
| ISS-193 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:319 | Unnecessary ellipsis | Заменить на pass |
| ISS-194 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:332 | Unnecessary ellipsis | Заменить на pass |
| ISS-195 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:336 | Unnecessary ellipsis | Заменить на pass |
| ISS-196 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:340 | Unnecessary ellipsis | Заменить на pass |
| ISS-197 | LOW | DEPRECATED | parser_2gis/parallel/protocols.py:352 | Unnecessary ellipsis | Заменить на pass |
| ISS-198 | LOW | UNUSED | parser_2gis/cache/manager.py:95 | Unused variable params | Удалить или использовать |
| ISS-199 | LOW | UNUSED | parser_2gis/cache/manager.py:123 | Unused variable params | Удалить или использовать |
| ISS-200 | LOW | UNUSED | parser_2gis/cli/launcher.py:123 | Unused variable cache_path_obj | Удалить или использовать |

---

## Группировка по пакетам

### Пакет 1 (ISS-001 — ISS-020): Критическая безопасность и блокирующие ошибки
SQL-инъекции, хардкод путей temp, критические несовместимости типов в парсере и фабрике, проблемы signal handler.

### Пакет 2 (ISS-021 — ISS-040): Singleton паттерн — исправление типизации
Все проблемы с Callable не имеющими _instance/_value — переработка синглтон-паттернов с ClassVar.

### Пакет 3 (ISS-041 — ISS-060): BrowserService интерфейс
Добавление недостающих методов в протокол BrowserService, исправление attr-defined ошибок.

### Пакет 4 (ISS-061 — ISS-080): Writer override и TypedDict
Исправление несовместимых сигнатур __exit__, write в writer классах, TypedDict проблемы.

### Пакет 5 (ISS-081 — ISS-100): Chrome context manager и типы
Исправление return type Literal, __exit__ возвращаемых типов, атрибуты ChromeRemote.

### Пакет 6 (ISS-101 — ISS-120): Unused type: ignore и инфраструктура
Удаление неиспользуемых type: ignore комментариев, исправление resource_monitor.

### Пакет 7 (ISS-121 — ISS-140): TUI, CLI, Parallel — типы и импорты
Sequence вместо list[Binding], исправление CLI launcher, TUI app.

### Пакет 8 (ISS-141 — ISS-160): Ruff — стиль и context manager
Nested if, unused переменные, open без context manager, длинные строки.

### Пакет 9 (ISS-161 — ISS-180): Pylint — unnecessary ellipsis
Замена ellipsis на pass в protocols файлах.

### Пакет 10 (ISS-181 — ISS-200): Оставшийся ellipsis и unused переменные
Добиваем ellipsis, удаляем unused переменные.
