# План автономного рефакторинга — 200 проблем

## Сводная статистика аудита

| Категория | CRITICAL | HIGH | MEDIUM | LOW | Итого |
|-----------|----------|------|--------|-----|-------|
| TYPE_SAFETY | 5 | 35 | 45 | 5 | 90 |
| STYLE | 0 | 0 | 14 | 64 | 78 |
| UNUSED | 0 | 0 | 20 | 60 | 80 |
| SECURITY | 2 | 6 | 0 | 6 | 14 |
| ARCHITECTURE | 3 | 5 | 8 | 12 | 28 |
| PERFORMANCE | 0 | 2 | 5 | 3 | 10 |
| DEPRECATED | 0 | 0 | 3 | 2 | 5 |
| **Итого** | **10** | **48** | **95** | **152** | **200** |

**Размер кодовой базы:** 187 файлов, 42 519 строк кода (parser_2gis/)
**Pylint оценка:** 9.89/10
**Ruff ошибок:** 80 (50 SIM117, 14 SIM102, 8 B017, 6 E402, 1 SIM105, 1 RUF012)
**Mypy ошибок:** 90
**Bandit проблем:** 14 (Low severity)
**Vulture unused:** 80+ единиц неиспользуемого кода

---

## Реестр проблем

### Пакет 1 — Критические проблемы безопасности и типы (ISS-001..ISS-020)

| ID | Sev | Category | Location | Description | SuggestedFix |
|----|-----|----------|----------|-------------|--------------|
| ISS-001 | CRITICAL | SECURITY | parser_2gis/cache/manager.py:912 | nosec comment B608 suppresses SQL injection check | Replace hardcoded SQL with parameterized queries |
| ISS-002 | CRITICAL | SECURITY | parser_2gis/parser/parsers/firm.py:401-411 | Unsafe indexing on union type without null checks | Add explicit type guards before dict access |
| ISS-003 | CRITICAL | TYPE_SAFETY | parser_2gis/parser/factory.py:260-262 | Incompatible parser types passed to register | Fix type annotations to match actual types |
| ISS-004 | CRITICAL | TYPE_SAFETY | parser_2gis/application/layer.py:135 | Incompatible return value BaseParser vs MainParser | Narrow return type annotation |
| ISS-005 | CRITICAL | TYPE_SAFETY | parser_2gis/parallel/strategies.py:437-459 | None-type access without guards on parser/writer | Add explicit None checks before __enter__/parse |
| ISS-006 | CRITICAL | TYPE_SAFETY | parser_2gis/parallel/parallel_parser.py:921 | set[Path] used with .get() method | Fix to use correct dict type |
| ISS-007 | CRITICAL | ARCHITECTURE | parser_2gis/constants/__init__.py:229 | Module imports itself (import-self) | Refactor to avoid circular import |
| ISS-008 | HIGH | TYPE_SAFETY | parser_2gis/parallel/parallel_parser.py:864-930 | Signal handler type mismatch in _do_merge_cleanup | Use proper Handlers type annotation |
| ISS-009 | HIGH | TYPE_SAFETY | parser_2gis/parallel/merger.py:558-613 | FrameType and signal handler type incompatibilities | Fix signal handler type signatures |
| ISS-010 | HIGH | TYPE_SAFETY | parser_2gis/utils/decorators.py:324-544 | Decorator return type mismatch (int vs float for timeout) | Fix WaitConfig.timeout type to int\|float |
| ISS-011 | HIGH | TYPE_SAFETY | parser_2gis/utils/decorators.py:427 | Wrapped decorator loses Callable type info | Use ParamSpec correctly for decorator signature |
| ISS-012 | HIGH | TYPE_SAFETY | parser_2gis/parallel/common/signal_handler_common.py:82-83 | Signal handler assignment type incompatible | Use proper Callable type for signal handlers |
| ISS-013 | HIGH | SECURITY | parser_2gis/parallel/common/file_lock.py:26 | Import not at top of module | Move import to module top |
| ISS-014 | HIGH | ARCHITECTURE | parser_2gis/parallel/url_parser.py:360 | BaseParser\|MainParser assigned to BaseParser\|None | Fix variable type annotation |
| ISS-015 | HIGH | TYPE_SAFETY | parser_2gis/parser/parsers/firm.py:293 | Dict assigned to variable with union type including list | Add proper type narrowing with isinstance |
| ISS-016 | HIGH | SECURITY | parser_2gis/cache/pool.py:212 | LockType passed where RLock expected in finalize | Use threading.RLock explicitly |
| ISS-017 | HIGH | TYPE_SAFETY | parser_2gis/writer/writers/csv_buffer_manager.py:139 | mmap passed to TextIOWrapper expecting _WrappedBuffer | Add proper type cast or use io.BytesIO wrapper |
| ISS-018 | HIGH | TYPE_SAFETY | parser_2gis/writer/writers/csv_post_processor.py:89 | DictReader called with incompatible fieldnames type | Convert fieldnames to Sequence[str] |
| ISS-019 | HIGH | TYPE_SAFETY | parser_2gis/writer/writers/csv_post_processor.py:157 | Same DictReader overload mismatch | Convert fieldnames to Sequence[str] |
| ISS-020 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_deduplicator.py:179-180 | Missing type annotation for line variable | Add explicit type annotation |

### Пакет 2 — Mypy type errors и unused type: ignore (ISS-021..ISS-040)

| ID | Sev | Category | Location | Description | SuggestedFix |
|----|-----|----------|----------|-------------|--------------|
| ISS-021 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/exceptions.py:70 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-022 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/exceptions.py:74 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-023 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/rate_limiter.py:22 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-024 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/remote.py:63 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-025 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/remote.py:64 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-026 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/remote.py:67 | Library stubs not installed for requests | Install types-requests or add type: ignore |
| ISS-027 | MEDIUM | TYPE_SAFETY | parser_2gis/chrome/remote.py:69 | Unused type: ignore[misc,assignment] | Remove unused type: ignore |
| ISS-028 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/settings.py:38 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-029 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/settings.py:199 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-030 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/settings.py:370 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-031 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/parsing_screen.py:16 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-032 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/other_screens.py:14 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-033 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/other_screens.py:189 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-034 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/main_menu.py:14 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-035 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/city_selector.py:16 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-036 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/screens/category_selector.py:14 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-037 | MEDIUM | TYPE_SAFETY | parser_2gis/tui_textual/app.py:173 | Unused type: ignore comment | Remove unused type: ignore |
| ISS-038 | MEDIUM | TYPE_SAFETY | parser_2gis/application/layer.py:402 | Unused type: ignore + no-any-return | Fix type annotation and remove ignore |
| ISS-039 | MEDIUM | TYPE_SAFETY | parser_2gis/utils/path_utils.py:47 | Callable has no _allowed_dirs attribute | Fix attribute access with proper type |
| ISS-040 | MEDIUM | TYPE_SAFETY | parser_2gis/utils/path_utils.py:52 | Returning Any from function returning list[Path] | Add explicit type cast |

### Пакет 3 — Ruff SIM117: nested with statements (tests, batch 1) (ISS-041..ISS-060)

| ID | Sev | Category | Location | Description | SuggestedFix |
|----|-----|----------|----------|-------------|--------------|
| ISS-041 | LOW | STYLE | tests/cache/test_manager_cleanup.py:266 | Nested with statements | Combine into single with |
| ISS-042 | LOW | STYLE | tests/cache/test_manager_cleanup.py:361 | Nested with statements | Combine into single with |
| ISS-043 | LOW | STYLE | tests/cache/test_manager_retry.py:51 | Nested with statements | Combine into single with |
| ISS-044 | LOW | STYLE | tests/cache/test_manager_retry.py:74 | Nested with statements | Combine into single with |
| ISS-045 | LOW | STYLE | tests/cache/test_manager_retry.py:99 | Nested with statements | Combine into single with |
| ISS-046 | LOW | STYLE | tests/cache/test_manager_retry.py:116 | Nested with statements | Combine into single with |
| ISS-047 | LOW | STYLE | tests/cache/test_manager_retry.py:130 | Nested with statements | Combine into single with |
| ISS-048 | LOW | STYLE | tests/cache/test_manager_retry.py:197 | Nested with statements | Combine into single with |
| ISS-049 | LOW | STYLE | tests/cache/test_pool_critical_fixes.py:78 | Nested with statements | Combine into single with |
| ISS-050 | LOW | STYLE | tests/cache/test_pool_critical_fixes.py:200 | Nested with statements | Combine into single with |
| ISS-051 | LOW | STYLE | tests/cache/test_pool_critical_fixes.py:261 | Nested with statements | Combine into single with |
| ISS-052 | LOW | STYLE | tests/cache/test_pool_exceptions.py:233 | Nested with statements | Combine into single with |
| ISS-053 | LOW | STYLE | tests/cache/test_pool_exceptions.py:254 | Nested with statements | Combine into single with |
| ISS-054 | LOW | STYLE | tests/cache/test_pool_exceptions.py:276 | Nested with statements | Combine into single with |
| ISS-055 | LOW | STYLE | tests/cache/test_pool_exceptions.py:298 | Nested with statements | Combine into single with |
| ISS-056 | LOW | STYLE | tests/chrome/test_browser_separation.py:61 | Nested with statements | Combine into single with |
| ISS-057 | LOW | STYLE | tests/chrome/test_browser_separation.py:81 | Nested with statements | Combine into single with |
| ISS-058 | LOW | STYLE | tests/chrome/test_browser_separation.py:106 | Nested with statements | Combine into single with |
| ISS-059 | LOW | STYLE | tests/chrome/test_browser_separation.py:126 | Nested with statements | Combine into single with |
| ISS-060 | LOW | STYLE | tests/chrome/test_rate_limiter.py:103 | Nested with statements | Combine into single with |

### Пакет 4 — Ruff SIM117 nested with (tests, batch 2) + SIM102 (ISS-061..ISS-080)

| ID | Sev | Category | Location | Description | SuggestedFix |
|----|-----|----------|----------|-------------|--------------|
| ISS-061 | LOW | STYLE | tests/chrome/test_rate_limiter.py:163 | Nested with statements | Combine into single with |
| ISS-062 | LOW | STYLE | tests/chrome/test_remote_critical_fixes.py:68 | Nested with statements | Combine into single with |
| ISS-063 | LOW | STYLE | tests/chrome/test_remote_critical_fixes.py:93 | Nested with statements | Combine into single with |
| ISS-064 | LOW | STYLE | tests/chrome/test_remote_critical_fixes.py:112 | Nested with statements | Combine into single with |
| ISS-065 | LOW | STYLE | tests/chrome/test_remote_critical_fixes.py:118 | Nested with statements | Combine into single with |
| ISS-066 | LOW | STYLE | tests/chrome/test_remote_critical_fixes.py:133 | Nested with statements | Combine into single with |
| ISS-067 | LOW | STYLE | tests/chrome/test_remote_critical_fixes.py:139 | Nested with statements | Combine into single with |
| ISS-068 | LOW | STYLE | tests/chrome/test_remote_critical_fixes.py:156 | Nested with statements | Combine into single with |
| ISS-069 | LOW | STYLE | tests/chrome/test_remote_critical_fixes.py:173 | Nested with statements | Combine into single with |
| ISS-070 | LOW | STYLE | tests/parser/test_navigate_timeout.py:239 | Nested with statements | Combine into single with |
| ISS-071 | LOW | STYLE | tests/test_chrome_browser_finalizer.py:17 | Nested with statements | Combine into single with |
| ISS-072 | LOW | STYLE | tests/test_chrome_browser_finalizer.py:49 | Nested with statements | Combine into single with |
| ISS-073 | LOW | STYLE | tests/test_chrome_browser_finalizer.py:105 | Nested with statements | Combine into single with |
| ISS-074 | LOW | STYLE | tests/test_cleanup_parallel_exceptions.py:102 | Nested with statements | Combine into single with |
| ISS-075 | LOW | STYLE | tests/test_connect_interface_timeout.py:67 | Nested with statements | Combine into single with |
| ISS-076 | LOW | STYLE | tests/test_architecture_solid.py:361 | Nested if statements | Combine with `and` |
| ISS-077 | LOW | STYLE | tests/test_architecture_solid.py:752 | Nested if statements | Combine with `and` |
| ISS-078 | LOW | STYLE | tests/test_architecture_solid.py:790 | Nested if statements | Combine with `and` |
| ISS-079 | LOW | STYLE | tests/test_code_quality.py:100 | Nested if statements | Combine with `and` |
| ISS-080 | LOW | STYLE | tests/test_code_quality.py:102 | Nested if statements | Combine with `and` |

### Пакет 5 — B017 blind exception + E402 import order + SIM102 (ISS-081..ISS-100)

| ID | Sev | Category | Location | Description | SuggestedFix |
|----|-----|----------|----------|-------------|--------------|
| ISS-081 | MEDIUM | STYLE | tests/cache/test_pool_exceptions.py:145 | Blind exception assert | Use specific exception type |
| ISS-082 | MEDIUM | STYLE | tests/test_chrome_integration.py:73 | Blind exception assert | Use ValueError or specific type |
| ISS-083 | MEDIUM | STYLE | tests/test_chrome_integration.py:76 | Blind exception assert | Use ValueError or specific type |
| ISS-084 | MEDIUM | STYLE | tests/test_common.py:306 | Blind exception assert | Use specific exception type |
| ISS-085 | LOW | STYLE | tests/test_chrome_integration.py:27-33 | Module imports not at top (pytestmark before import) | Move imports to top of file |
| ISS-086 | LOW | STYLE | tests/test_chrome_integration.py:29 | Module imports not at top | Move imports to top of file |
| ISS-087 | LOW | STYLE | tests/test_chrome_integration.py:30 | Module imports not at top | Move imports to top of file |
| ISS-088 | LOW | STYLE | tests/test_chrome_integration.py:31 | Module imports not at top | Move imports to top of file |
| ISS-089 | LOW | STYLE | tests/test_chrome_integration.py:32 | Module imports not at top | Move imports to top of file |
| ISS-090 | LOW | STYLE | tests/test_chrome_integration.py:33 | Module imports not at top | Move imports to top of file |
| ISS-091 | LOW | STYLE | tests/test_code_quality.py:156 | Nested if statements | Combine with `and` |
| ISS-092 | LOW | STYLE | tests/test_code_quality.py:226 | Nested if statements | Combine with `and` |
| ISS-093 | LOW | STYLE | tests/test_code_quality.py:236 | Nested if statements | Combine with `and` |
| ISS-094 | LOW | STYLE | tests/test_code_quality.py:284 | Nested if statements | Combine with `and` |
| ISS-095 | LOW | STYLE | tests/test_code_quality.py:312 | Nested if statements | Combine with `and` |
| ISS-096 | LOW | STYLE | parser_2gis/cache/manager.py:780 | SIM105: try-except-pass could use contextlib.suppress | Replace with contextlib.suppress(sqlite3.Error) |
| ISS-097 | MEDIUM | TYPE_SAFETY | parser_2gis/parser/parsers/main_parser.py:342 | Returning Any from function declared to return bool | Add explicit bool cast |
| ISS-098 | MEDIUM | TYPE_SAFETY | parser_2gis/parser/parsers/main_parser.py:705 | Returning Any from function declared to return dict\|None | Add explicit type annotation |
| ISS-099 | MEDIUM | TYPE_SAFETY | parser_2gis/parser/parsers/main_extractor.py:90 | Returning Any from function declared to return str\|None | Add explicit type annotation |
| ISS-100 | MEDIUM | TYPE_SAFETY | parser_2gis/writer/writers/csv_writer.py:468 | Returning Any from function declared to return dict\|None | Add explicit type annotation |

### Пакет 6 — Vulture: unused code in cache/chrome modules (ISS-101..ISS-120)

| ID | Sev | Category | Location | Description | SuggestedFix |
|----|-----|----------|----------|-------------|--------------|
| ISS-101 | LOW | UNUSED | parser_2gis/cache/manager.py:65 | Unused variable CacheItem | Remove or prefix with _ |
| ISS-102 | LOW | UNUSED | parser_2gis/cache/manager.py:94 | Unused variable params | Remove or use in implementation |
| ISS-103 | LOW | UNUSED | parser_2gis/cache/manager.py:107 | Unused class ConnectionProtocol | Remove or prefix with _ |
| ISS-104 | LOW | UNUSED | parser_2gis/cache/manager.py:122 | Unused variable params | Remove or use in implementation |
| ISS-105 | LOW | UNUSED | parser_2gis/cache/manager.py:246 | Unused variable GET_CACHE_SIZE_SQL | Remove or use |
| ISS-106 | LOW | UNUSED | parser_2gis/cache/manager.py:320 | Unused attribute _validator | Remove or document as reserved |
| ISS-107 | LOW | UNUSED | parser_2gis/cache/manager.py:326 | Unused attribute _weak_ref | Remove or document as reserved |
| ISS-108 | LOW | UNUSED | parser_2gis/cache/manager.py:446 | Unused method _delete_cached_entry | Remove or prefix with _ |
| ISS-109 | LOW | UNUSED | parser_2gis/cache/manager.py:505 | Unused method _handle_cache_miss | Remove or prefix with _ |
| ISS-110 | LOW | UNUSED | parser_2gis/cache/manager.py:871 | Unused method get_batch | Remove or prefix with _ |
| ISS-111 | LOW | UNUSED | parser_2gis/cache/manager.py:950 | Unused method set_batch | Remove or prefix with _ |
| ISS-112 | LOW | UNUSED | parser_2gis/cache/manager.py:1081 | Unused method clear_expired | Remove or prefix with _ |
| ISS-113 | LOW | UNUSED | parser_2gis/cache/manager.py:1121 | Unused method clear_batch | Remove or prefix with _ |
| ISS-114 | LOW | UNUSED | parser_2gis/cache/config_cache.py:205 | Unused attribute _cities_cache_size | Remove or use |
| ISS-115 | LOW | UNUSED | parser_2gis/cache/config_cache.py:206 | Unused attribute _categories_cache_size | Remove or use |
| ISS-116 | LOW | UNUSED | parser_2gis/cache/config_cache.py:233 | Unused method load_cities | Remove or prefix with _ |
| ISS-117 | LOW | UNUSED | parser_2gis/cache/config_cache.py:254 | Unused method clear_cities_cache | Remove or prefix with _ |
| ISS-118 | LOW | UNUSED | parser_2gis/cache/config_cache.py:258 | Unused method cities_cache_info | Remove or prefix with _ |
| ISS-119 | LOW | UNUSED | parser_2gis/cache/config_cache.py:287 | Unused method clear_categories_cache | Remove or prefix with _ |
| ISS-120 | LOW | UNUSED | parser_2gis/cache/pool.py:197 | Unused attribute _max_size | Remove or use |

### Пакет 7 — Vulture: unused code in chrome/cli modules (ISS-121..ISS-140)

| ID | Sev | Category | Location | Description | SuggestedFix |
|----|-----|----------|----------|-------------|--------------|
| ISS-121 | LOW | UNUSED | parser_2gis/cache/pool.py:211 | Unused attribute _weak_ref | Remove or document |
| ISS-122 | LOW | UNUSED | parser_2gis/cache/serializer.py:48 | Unused attribute use_orjson | Remove or use |
| ISS-123 | LOW | UNUSED | parser_2gis/chrome/browser.py:61 | Unused variable ProcessStatus | Remove or use |
| ISS-124 | LOW | UNUSED | parser_2gis/chrome/browser.py:650 | Unused method terminate_process_graceful | Remove or prefix with _ |
| ISS-125 | LOW | UNUSED | parser_2gis/chrome/browser.py:654 | Unused method terminate_process_forceful | Remove or prefix with _ |
| ISS-126 | LOW | UNUSED | parser_2gis/chrome/browser_builder.py:39 | Unused method with_options | Remove or prefix with _ |
| ISS-127 | LOW | UNUSED | parser_2gis/chrome/browser_builder.py:52 | Unused method build | Remove or prefix with _ |
| ISS-128 | LOW | UNUSED | parser_2gis/chrome/constants.py:63 | Unused DEFAULT_REMOTE_DEBUGGING_PORT_RANGE | Remove or prefix with _ |
| ISS-129 | LOW | UNUSED | parser_2gis/chrome/constants.py:98-99 | Unused RATE_LIMIT_CALLS, RATE_LIMIT_PERIOD | Remove or use |
| ISS-130 | LOW | UNUSED | parser_2gis/chrome/constants.py:103-106 | Unused timeout constants | Remove or prefix with _ |
| ISS-131 | LOW | UNUSED | parser_2gis/chrome/constants.py:110 | Unused PORT_CACHE_MAXSIZE | Remove or use |
| ISS-132 | LOW | UNUSED | parser_2gis/chrome/constants.py:140 | Unused DEFAULT_REMOTE_DEBUGGING_PORT | Remove or use |
| ISS-133 | LOW | UNUSED | parser_2gis/chrome/constants.py:152-153 | Unused CSS color constants | Remove or prefix with _ |
| ISS-134 | LOW | UNUSED | parser_2gis/chrome/constants.py:178 | Unused DEFAULT_CONNECTION_TIMEOUT_SEC | Remove or use |
| ISS-135 | LOW | UNUSED | parser_2gis/chrome/dom.py:62 | Unused method validate_attributes | Remove or prefix with _ |
| ISS-136 | LOW | UNUSED | parser_2gis/chrome/http_cache.py:34 | Unused HTTP_CACHE_RATE_LIMIT_DELAY | Remove or use |
| ISS-137 | LOW | UNUSED | parser_2gis/chrome/http_cache.py:128 | Unused method size | Remove or prefix with _ |
| ISS-138 | LOW | UNUSED | parser_2gis/chrome/http_cache.py:160 | Unused function _get_cache_key | Remove or use |
| ISS-139 | LOW | UNUSED | parser_2gis/chrome/http_cache.py:175 | Unused function _cleanup_expired_cache | Remove or use |
| ISS-140 | LOW | UNUSED | parser_2gis/chrome/js_executor.py:550 | Unused function _sanitize_js_string | Remove or use |

### Пакет 8 — Vulture: unused code in chrome/parallel/logger (ISS-141..ISS-160)

| ID | Sev | Category | Location | Description | SuggestedFix |
|----|-----|----------|----------|-------------|--------------|
| ISS-141 | LOW | UNUSED | parser_2gis/chrome/patches/pychrome.py:54 | Unused attribute _recv_loop | Remove or use |
| ISS-142 | LOW | UNUSED | parser_2gis/chrome/rate_limiter.py:97 | Unused property request_count | Remove or prefix with _ |
| ISS-143 | LOW | UNUSED | parser_2gis/chrome/remote.py:126 | Unused variable ProcessStatus | Remove or use |
| ISS-144 | LOW | UNUSED | parser_2gis/chrome/remote.py:144 | Unused function get_port_cache_info | Remove or prefix with _ |
| ISS-145 | LOW | UNUSED | parser_2gis/chrome/remote.py:189 | Unused function _check_port_available | Remove or use |
| ISS-146 | LOW | UNUSED | parser_2gis/chrome/remote.py:208 | Unused function invalidate_port_cache | Remove or prefix with _ |
| ISS-147 | LOW | UNUSED | parser_2gis/chrome/remote.py:926 | Unused method get_requests | Remove or prefix with _ |
| ISS-148 | LOW | UNUSED | parser_2gis/chrome/remote.py:1004 | Unused method execute_script_batch | Remove or prefix with _ |
| ISS-149 | LOW | UNUSED | parser_2gis/chrome/remote.py:1394 | Unused method screenshot | Remove or prefix with _ |
| ISS-150 | LOW | UNUSED | parser_2gis/chrome/request_interceptor.py:60 | Unused method unregister_response_pattern | Remove or prefix with _ |
| ISS-151 | LOW | UNUSED | parser_2gis/chrome/request_interceptor.py:120 | Unused method get_request | Remove or prefix with _ |
| ISS-152 | LOW | UNUSED | parser_2gis/cli/formatter.py:153 | Unused attribute __str__ | Remove or fix |
| ISS-153 | LOW | UNUSED | parser_2gis/cli/progress.py:137 | Unused method update_page | Remove or prefix with _ |
| ISS-154 | LOW | UNUSED | parser_2gis/cli/progress.py:151 | Unused method update_record | Remove or prefix with _ |
| ISS-155 | LOW | UNUSED | parser_2gis/cli/progress.py:233 | Unused method reset | Remove or prefix with _ |
| ISS-156 | LOW | UNUSED | parser_2gis/cli/progress.py:254 | Unused property is_started | Remove or prefix with _ |
| ISS-157 | LOW | UNUSED | parser_2gis/cli/progress.py:264 | Unused property is_finished | Remove or prefix with _ |
| ISS-158 | LOW | UNUSED | parser_2gis/logger/handlers.py:77 | Unused attribute _auto_session | Remove or use |
| ISS-159 | LOW | UNUSED | parser_2gis/logger/handlers.py:312 | Unused property is_enabled | Remove or prefix with _ |
| ISS-160 | LOW | UNUSED | parser_2gis/logger/logger.py:96 | Unused class LoggerProvider | Remove or prefix with _ |

### Пакет 9 — Vulture: unused code in config/constants/types + pylint issues (ISS-161..ISS-180)

| ID | Sev | Category | Location | Description | SuggestedFix |
|----|-----|----------|----------|-------------|--------------|
| ISS-161 | LOW | UNUSED | parser_2gis/logger/logger.py:106 | Unused method get_logger | Remove or prefix with _ |
| ISS-162 | LOW | UNUSED | parser_2gis/logger/logger.py:131 | Unused method configure_logger | Remove or prefix with _ |
| ISS-163 | LOW | UNUSED | parser_2gis/logger/options.py:38 | Unused variable file_datefmt | Remove or use |
| ISS-164 | LOW | UNUSED | parser_2gis/logger/options.py:60 | Unused method level_validation | Remove or prefix with _ |
| ISS-165 | LOW | UNUSED | parser_2gis/logger/options.py:66 | Unused method format_validation | Remove or prefix with _ |
| ISS-166 | LOW | UNUSED | parser_2gis/logger/presentation_bridge.py:42 | Unused property is_enabled | Remove or prefix with _ |
| ISS-167 | LOW | UNUSED | parser_2gis/logger/visual_logger.py:48 | Unused variable UNDERLINE | Remove or use |
| ISS-168 | LOW | UNUSED | parser_2gis/config.py:49 | Unused class ConfigServiceProtocol | Remove or prefix with _ |
| ISS-169 | LOW | UNUSED | parser_2gis/config.py:101 | Unused variable model_config | Remove or use |
| ISS-170 | LOW | UNUSED | parser_2gis/config.py:133 | Unused method merge_with | Remove or prefix with _ |
| ISS-171 | LOW | UNUSED | parser_2gis/constants.py:122 | Unused class EnvValidationEntry | Remove or prefix with _ |
| ISS-172 | LOW | UNUSED | parser_2gis/constants.py:133 | Unused variable log_template | Remove or use |
| ISS-173 | LOW | UNUSED | parser_2gis/constants.py:149 | Unused function _reset_constant_cache | Remove or use |
| ISS-174 | LOW | UNUSED | parser_2gis/constants/__init__.py:23 | Unused function __getattr__ | Remove or prefix with _ |
| ISS-175 | LOW | UNUSED | parser_2gis/constants/__init__.py:141 | Unused function __dir__ | Remove or prefix with _ |
| ISS-176 | LOW | UNUSED | parser_2gis/constants/__init__.py:224 | Unused function _reset_constant_cache | Remove or use |
| ISS-177 | LOW | UNUSED | parser_2gis/constants/env_config.py:237 | Unused method to_dict | Remove or prefix with _ |
| ISS-178 | LOW | UNUSED | parser_2gis/constants/env_config.py:320 | Unused method refresh | Remove or prefix with _ |
| ISS-179 | LOW | UNUSED | parser_2gis/constants/env_config.py:330 | Unused method is_cached | Remove or prefix with _ |
| ISS-180 | MEDIUM | ARCHITECTURE | parser_2gis/chrome/constants.py:17 | Unused imports DEFAULT_TTL_HOURS, MAX_RESPONSE_SIZE | Remove unused imports |

### Пакет 10 — Core types unused + remaining mypy/architecture (ISS-181..ISS-200)

| ID | Sev | Category | Location | Description | SuggestedFix |
|----|-----|----------|----------|-------------|--------------|
| ISS-181 | LOW | UNUSED | parser_2gis/core_types.py:21 | Unused variable K | Remove or prefix with _ |
| ISS-182 | LOW | UNUSED | parser_2gis/core_types.py:22 | Unused variable V | Remove or prefix with _ |
| ISS-183 | LOW | UNUSED | parser_2gis/core_types.py:27 | Unused class LogCallback | Remove or prefix with _ |
| ISS-184 | LOW | UNUSED | parser_2gis/core_types.py:72 | Unused class FileOperationResult | Remove or prefix with _ |
| ISS-185 | LOW | UNUSED | parser_2gis/core_types.py:87 | Unused class MergeStats | Remove or prefix with _ |
| ISS-186 | LOW | UNUSED | parser_2gis/core_types.py:97 | Unused variable total_files | Remove or use |
| ISS-187 | LOW | UNUSED | parser_2gis/core_types.py:99 | Unused variable deleted_files | Remove or use |
| ISS-188 | LOW | UNUSED | parser_2gis/core_types.py:130 | Unused method ok | Remove or prefix with _ |
| ISS-189 | LOW | UNUSED | parser_2gis/core_types.py:143 | Unused method fail | Remove or prefix with _ |
| ISS-190 | LOW | UNUSED | parser_2gis/infrastructure/resource_monitor.py:61 | Unused property used_mb | Remove or prefix with _ |
| ISS-191 | LOW | UNUSED | parser_2gis/infrastructure/resource_monitor.py:71 | Unused property total_mb | Remove or prefix with _ |
| ISS-192 | LOW | UNUSED | parser_2gis/infrastructure/resource_monitor.py:223 | Unused method get_memory_monitor | Remove or prefix with _ |
| ISS-193 | LOW | UNUSED | parser_2gis/infrastructure/resource_monitor.py:232 | Unused method is_memory_critical | Remove or prefix with _ |
| ISS-194 | LOW | UNUSED | parser_2gis/infrastructure/resource_monitor.py:250 | Unused method check_memory_before_operation | Remove or prefix with _ |
| ISS-195 | LOW | UNUSED | parser_2gis/infrastructure/resource_monitor.py:271 | Unused method get_cpu_usage | Remove or prefix with _ |
| ISS-196 | MEDIUM | ARCHITECTURE | parser_2gis/logger/visual_logger.py:223 | Statement seems to have no effect | Remove or assign to variable |
| ISS-197 | MEDIUM | ARCHITECTURE | parser_2gis/tui_textual/app.py:531 | Cannot determine type of "theme" | Add explicit type annotation |
| ISS-198 | MEDIUM | ARCHITECTURE | parser_2gis/tui_textual/app.py:609 | Untyped decorator makes _run_parsing untyped | Add type hints to decorator or function |
| ISS-199 | MEDIUM | TYPE_SAFETY | parser_2gis/cli/main.py:51 | ConfigSummaryDict incompatible with dict[str, Any]\|None | Fix type annotation |
| ISS-200 | MEDIUM | TYPE_SAFETY | parser_2gis/cli/formatter.py:139 | Returning Any from function declared to return str | Add explicit str cast |

---

## Пакеты обработки

| Пакет | Диапазон ID | Фокус | Кол-во |
|-------|-------------|-------|--------|
| Пакет-1 | ISS-001..ISS-020 | Критические: безопасность, типы, архитектура | 20 |
| Пакет-2 | ISS-021..ISS-040 | Mypy: unused type: ignore, type annotations | 20 |
| Пакет-3 | ISS-041..ISS-060 | Ruff SIM117: nested with (tests batch 1) | 20 |
| Пакет-4 | ISS-061..ISS-080 | Ruff SIM117/SIM102: nested with/if (tests batch 2) | 20 |
| Пакет-5 | ISS-081..ISS-100 | B017 blind exception + E402 import order + SIM102 | 20 |
| Пакет-6 | ISS-101..ISS-120 | Vulture: unused code в cache модулях | 20 |
| Пакет-7 | ISS-121..ISS-140 | Vulture: unused code в chrome/cli модулях | 20 |
| Пакет-8 | ISS-141..ISS-160 | Vulture: unused code в chrome/parallel/logger | 20 |
| Пакет-9 | ISS-161..ISS-180 | Vulture: unused config/constants/types + pylint | 20 |
| Пакет-10 | ISS-181..ISS-200 | Core types unused + remaining mypy/architecture | 20 |
