# AUDIT REPORT: parser-2gis Deep Static Analysis
# Date: 2026-04-12
# Tools: Ruff (22 rules), Mypy
# Scope: parser_2gis/ (183 files checked)
#
# EXCLUDED (per instructions):
# - RUF001/RUF002/RUF003 — русский текст, допустимо
# - COM812 — trailing comma, стиль
# - TRY003 — длинные сообщения исключений
# - TID252 — relative imports
# - ERA001 — закомментированный код
#
# TOTAL ISSUES SCANNED: 943 (from selected rules)
# REPORTED: 200 (prioritized by severity, top issues per category)

================================================================================
CATEGORY: Critical (Security, Correctness, Runtime Risks)
Severity: HIGH
================================================================================

--- BLE001: Bare Except (4 issues) — HIGH — catching Exception masks real errors ---

ID: ISSUE-1001
Category: Critical
Location: parser_2gis/cache/pool.py:123
Severity: HIGH
Description: Blind except Exception at connection pool get_connection — masks specific errors like KeyboardInterrupt, SystemExit
Fix: Replace `except Exception` with specific exceptions (sqlite3.Error, OSError, ConnectionError)

ID: ISSUE-1002
Category: Critical
Location: parser_2gis/parallel/common/future_utils.py:70
Severity: HIGH
Description: Blind except Exception in future result handling — hides CancelledError, TimeoutError
Fix: Catch specific concurrent.futures exceptions; re-raise KeyboardInterrupt/SystemExit

ID: ISSUE-1003
Category: Critical
Location: parser_2gis/tui_textual/app.py:691
Severity: HIGH
Description: Blind except Exception in TUI parsing handler — silently swallows errors in UI context
Fix: Catch specific exceptions; log and re-raise; use structured error handling

ID: ISSUE-1004
Category: Critical
Location: parser_2gis/utils/decorators.py:388
Severity: HIGH
Description: Blind except Exception in decorator wrapper — masks all errors including programming mistakes
Fix: Catch specific expected exceptions; add logging for unexpected errors

--- S101: Assert Usage (3 issues) — HIGH — asserts can be disabled with -O ---

ID: ISSUE-1005
Category: Critical
Location: parser_2gis/parser/parsers/main_parser.py:140
Severity: HIGH
Description: assert used for runtime validation — disabled with python -O, bypasses check
Fix: Replace with explicit if/raise with appropriate exception type

ID: ISSUE-1006
Category: Critical
Location: parser_2gis/utils/file_lock_abstraction.py:147
Severity: HIGH
Description: assert used for lock state validation — file locking correctness depends on it
Fix: Replace with RuntimeError or OSError with descriptive message

ID: ISSUE-1007
Category: Critical
Location: parser_2gis/validation/path_validation.py:227
Severity: HIGH
Description: assert used for path safety validation — security check bypassed with -O
Fix: Replace with ValueError or SecurityError with explicit check

--- DTZ005: Timezone-naive datetime (16 issues) — HIGH — incorrect time comparisons across timezones ---

ID: ISSUE-1008
Category: Critical
Location: parser_2gis/cache/cache_utils.py:180
Severity: HIGH
Description: datetime.now() without tz — naive datetime for cache expiry comparison can cause incorrect results
Fix: Use datetime.now(timezone.utc) consistently

ID: ISSUE-1009
Category: Critical
Location: parser_2gis/cache/manager.py:563
Severity: HIGH
Description: datetime.now(tz=None) in cache get — naive/explicit mismatch causes TypeError in comparisons
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1010
Category: Critical
Location: parser_2gis/cache/manager.py:788
Severity: HIGH
Description: datetime.now(tz=None) in cache set — inconsistent timezone handling
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1011
Category: Critical
Location: parser_2gis/cache/manager.py:964
Severity: HIGH
Description: datetime.now(tz=None) in cache cleanup
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1012
Category: Critical
Location: parser_2gis/cache/manager.py:1087
Severity: HIGH
Description: datetime.now(tz=None) in cache expiration check
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1013
Category: Critical
Location: parser_2gis/cache/manager.py:1190
Severity: HIGH
Description: datetime.now(tz=None) in cache statistics
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1014
Category: Critical
Location: parser_2gis/cli/main.py:65
Severity: HIGH
Description: datetime.now(tz=None) in CLI entry point — log timestamps may be ambiguous
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1015
Category: Critical
Location: parser_2gis/logger/handlers.py:119
Severity: HIGH
Description: datetime.now(tz=None) in log handler
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1016
Category: Critical
Location: parser_2gis/logger/handlers.py:180
Severity: HIGH
Description: datetime.now(tz=None) in log handler rotation
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1017
Category: Critical
Location: parser_2gis/logger/handlers.py:260
Severity: HIGH
Description: datetime.now(tz=None) in log handler timestamp
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1018
Category: Critical
Location: parser_2gis/logger/visual_logger.py:156
Severity: HIGH
Description: datetime.now(tz=None) in visual logger
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1019
Category: Critical
Location: parser_2gis/tui_textual/app.py:620
Severity: HIGH
Description: datetime.now(tz=None) in TUI parsing timestamp
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1020
Category: Critical
Location: parser_2gis/tui_textual/parsing_facade.py:99
Severity: HIGH
Description: datetime.now(tz=None) in parsing facade
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1021
Category: Critical
Location: parser_2gis/tui_textual/parsing_orchestrator.py:91
Severity: HIGH
Description: datetime.now(tz=None) in orchestrator
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1022
Category: Critical
Location: parser_2gis/tui_textual/screens/parsing_screen.py:173
Severity: HIGH
Description: datetime.now(tz=None) in parsing screen
Fix: Use datetime.now(timezone.utc)

ID: ISSUE-1023
Category: Critical
Location: parser_2gis/tui_textual/screens/parsing_screen.py:305
Severity: HIGH
Description: datetime.now(tz=None) in parsing screen update
Fix: Use datetime.now(timezone.utc)

================================================================================
CATEGORY: Performance (Complexity, Resource Usage)
Severity: HIGH/MEDIUM
================================================================================

--- C901: Cyclomatic Complexity > 10 (57 issues) — HIGH/MEDIUM ---
Top 20 by complexity value:

ID: ISSUE-2001
Category: Performance
Location: parser_2gis/utils/sanitizers.py:206 `_sanitize_value`
Severity: HIGH
Description: Cyclomatic complexity 38 (threshold 10) — extremely complex sanitization logic with many branches
Fix: Decompose into per-type sanitizer functions; use dispatch table

ID: ISSUE-2002
Category: Performance
Location: parser_2gis/parallel/merger.py:374 `merge_csv_files`
Severity: HIGH
Description: Cyclomatic complexity 32 — complex merge logic with many error paths
Fix: Extract lock handling, file processing, and error handling into separate functions

ID: ISSUE-2003
Category: Performance
Location: parser_2gis/parallel/parallel_parser.py:703 `merge_csv_files`
Severity: HIGH
Description: Cyclomatic complexity 33 — duplicate complex merge logic
Fix: Extract common merge logic; use shared helper functions

ID: ISSUE-2004
Category: Performance
Location: parser_2gis/parallel/common/csv_merge_common.py:64 `merge_csv_files_common`
Severity: HIGH
Description: Cyclomatic complexity 29 — complex CSV merge with many edge cases
Fix: Split into: file open, row processing, dedup, write phases

ID: ISSUE-2005
Category: Performance
Location: parser_2gis/writer/writers/csv_writer.py:442 `_extract_raw`
Severity: HIGH
Description: Cyclomatic complexity 26 — complex field extraction logic
Fix: Use field-type dispatch pattern instead of nested if/elif

ID: ISSUE-2006
Category: Performance
Location: parser_2gis/parallel/coordinator.py:712 `run`
Severity: HIGH
Description: Cyclomatic complexity 25 — main coordinator loop with many strategy branches
Fix: Extract strategy-specific logic into strategy classes

ID: ISSUE-2007
Category: Performance
Location: parser_2gis/parallel/strategies.py:326 `parse_single_url`
Severity: HIGH
Description: Cyclomatic complexity 25 — complex URL parsing with many fallbacks
Fix: Extract validation, parsing, and error recovery into separate functions

ID: ISSUE-2008
Category: Performance
Location: parser_2gis/parser/parsers/firm.py:151 `_validate_initial_state`
Severity: HIGH
Description: Cyclomatic complexity 23 — validation with many conditions
Fix: Use validation rules pattern; early returns

ID: ISSUE-2009
Category: Performance
Location: parser_2gis/cache/pool.py:230 `get_connection`
Severity: HIGH
Description: Cyclomatic complexity 22 — connection pool logic with many error paths
Fix: Separate connection creation, validation, pooling, and error handling

ID: ISSUE-2010
Category: Performance
Location: parser_2gis/parallel/url_parser.py:274 `parse_single_url`
Severity: HIGH
Description: Cyclomatic complexity 21 — complex URL parsing
Fix: Split into URL validation, browser setup, parsing, and cleanup

ID: ISSUE-2011
Category: Performance
Location: parser_2gis/parser/parsers/main_processor.py:411 `_parse_search_results`
Severity: HIGH
Description: Cyclomatic complexity 21 — complex search result parsing
Fix: Extract item parsing into separate function; use map/filter

ID: ISSUE-2012
Category: Performance
Location: parser_2gis/parallel/parallel_parser.py:906 `run`
Severity: HIGH
Description: Cyclomatic complexity 20 — main parallel parser loop
Fix: Extract phase-specific logic (setup, execution, merge, cleanup)

ID: ISSUE-2013
Category: Performance
Location: parser_2gis/chrome/browser.py:1250 `_is_profile_in_use`
Severity: HIGH
Description: Cyclomatic complexity 19 — profile detection with many fallbacks
Fix: Extract per-detection-method into separate functions

ID: ISSUE-2014
Category: Performance
Location: parser_2gis/utils/path_utils.py:61 `validate_path_safety`
Severity: HIGH
Description: Cyclomatic complexity 19 — path safety with many checks
Fix: Use list of validation predicates; short-circuit on first failure

ID: ISSUE-2015
Category: Performance
Location: parser_2gis/utils/path_utils.py:178 `validate_path_traversal`
Severity: HIGH
Description: Cyclomatic complexity 19 — path traversal detection
Fix: Use canonicalization + prefix check pattern

ID: ISSUE-2016
Category: Performance
Location: parser_2gis/parallel/strategies.py:376 `do_parse`
Severity: HIGH
Description: Cyclomatic complexity 18 — inner parsing loop
Fix: Extract browser lifecycle and parsing into separate functions

ID: ISSUE-2017
Category: Performance
Location: parser_2gis/chrome/request_interceptor.py:133 `setup_network_interceptors`
Severity: HIGH
Description: Cyclomatic complexity 18 — network interceptor setup with many event handlers
Fix: Extract each event handler (responseReceived, loadingFailed, requestWillBeSent) into separate functions

ID: ISSUE-2018
Category: Performance
Location: parser_2gis/cache/manager.py:627 `get`
Severity: HIGH
Description: Cyclomatic complexity 17 — cache retrieval with many error/retry paths
Fix: Extract query execution, deserialization, and error handling

ID: ISSUE-2019
Category: Performance
Location: parser_2gis/cache/manager.py:734 `set`
Severity: HIGH
Description: Cyclomatic complexity 17 — cache storage with validation and error handling
Fix: Separate validation, serialization, and database operations

ID: ISSUE-2020
Category: Performance
Location: parser_2gis/utils/decorators.py:224 `wait_until_finished`
Severity: HIGH
Description: Cyclomatic complexity 17 — complex wait/retry decorator
Fix: Extract timeout check, condition check, and retry logic

--- PLR0915: Too Many Statements (25 issues) — MEDIUM ---

ID: ISSUE-2021
Category: Performance
Location: parser_2gis/utils/sanitizers.py:206
Severity: MEDIUM
Description: 116 statements (threshold 50) in _sanitize_value
Fix: Decompose into per-type handlers

ID: ISSUE-2022
Category: Performance
Location: parser_2gis/parallel/merger.py:374
Severity: MEDIUM
Description: 127 statements in merge_csv_files
Fix: Extract sub-functions for each phase

ID: ISSUE-2023
Category: Performance
Location: parser_2gis/parallel/parallel_parser.py:703
Severity: MEDIUM
Description: 120 statements in merge_csv_files
Fix: Extract sub-functions

ID: ISSUE-2024
Category: Performance
Location: parser_2gis/parallel/strategies.py:326
Severity: MEDIUM
Description: 114 statements in parse_single_url
Fix: Extract URL handling phases

ID: ISSUE-2025
Category: Performance
Location: parser_2gis/parallel/file_merger.py:90
Severity: MEDIUM
Description: 112 statements in merge_csv_files
Fix: Extract sub-functions

--- PLR0912: Too Many Branches (34 issues) — MEDIUM ---

ID: ISSUE-2026
Category: Performance
Location: parser_2gis/utils/sanitizers.py:206
Severity: MEDIUM
Description: 42 branches (threshold 12) in _sanitize_value
Fix: Use type-based dispatch dictionary

ID: ISSUE-2027
Category: Performance
Location: parser_2gis/parallel/common/csv_merge_common.py:64
Severity: MEDIUM
Description: 28 branches in merge_csv_files_common
Fix: Extract branch-heavy logic into predicates

ID: ISSUE-2028
Category: Performance
Location: parser_2gis/parallel/coordinator.py:712
Severity: MEDIUM
Description: 27 branches in run
Fix: Extract strategy-specific branches

ID: ISSUE-2029
Category: Performance
Location: parser_2gis/parallel/parallel_parser.py:703
Severity: MEDIUM
Description: 27 branches in merge_csv_files
Fix: Extract error handling branches

ID: ISSUE-2030
Category: Performance
Location: parser_2gis/writer/writers/csv_writer.py:442
Severity: MEDIUM
Description: 26 branches in _extract_raw
Fix: Use field-type dispatch

================================================================================
CATEGORY: ErrorHandling
Severity: MEDIUM
================================================================================

--- TRY004: Prefer TypeError for invalid type (13 issues) — MEDIUM ---

ID: ISSUE-3001
Category: ErrorHandling
Location: parser_2gis/cache/serializer.py:204
Severity: MEDIUM
Description: Raises ValueError for invalid type instead of TypeError
Fix: Change `raise ValueError(...)` to `raise TypeError(...)`

ID: ISSUE-3002
Category: ErrorHandling
Location: parser_2gis/chrome/remote.py:229
Severity: MEDIUM
Description: Raises ValueError for invalid port type
Fix: Change to TypeError

ID: ISSUE-3003
Category: ErrorHandling
Location: parser_2gis/chrome/remote.py:232
Severity: MEDIUM
Description: Raises ValueError for invalid timeout type
Fix: Change to TypeError

ID: ISSUE-3004
Category: ErrorHandling
Location: parser_2gis/chrome/remote.py:265
Severity: MEDIUM
Description: Raises ValueError for invalid type in validation
Fix: Change to TypeError

ID: ISSUE-3005
Category: ErrorHandling
Location: parser_2gis/chrome/remote.py:272
Severity: MEDIUM
Description: Raises ValueError for invalid type
Fix: Change to TypeError

ID: ISSUE-3006
Category: ErrorHandling
Location: parser_2gis/resources/cities_loader.py:94
Severity: MEDIUM
Description: Raises ValueError for invalid cities data type
Fix: Change to TypeError

ID: ISSUE-3007
Category: ErrorHandling
Location: parser_2gis/resources/cities_loader.py:107
Severity: MEDIUM
Description: Raises ValueError for invalid city item type
Fix: Change to TypeError

ID: ISSUE-3008
Category: ErrorHandling
Location: parser_2gis/resources/cities_loader.py:120
Severity: MEDIUM
Description: Raises ValueError for invalid city name type
Fix: Change to TypeError

ID: ISSUE-3009
Category: ErrorHandling
Location: parser_2gis/utils/validation_utils.py:171
Severity: MEDIUM
Description: Raises ValueError for type check
Fix: Change to TypeError

ID: ISSUE-3010
Category: ErrorHandling
Location: parser_2gis/utils/validation_utils.py:179
Severity: MEDIUM
Description: Raises ValueError for type check
Fix: Change to TypeError

ID: ISSUE-3011
Category: ErrorHandling
Location: parser_2gis/utils/validation_utils.py:234
Severity: MEDIUM
Description: Raises ValueError for type check
Fix: Change to TypeError

ID: ISSUE-3012
Category: ErrorHandling
Location: parser_2gis/validation/data_validator.py:392
Severity: MEDIUM
Description: Raises ValueError for type validation
Fix: Change to TypeError

ID: ISSUE-3013
Category: ErrorHandling
Location: parser_2gis/validation/data_validator.py:396
Severity: MEDIUM
Description: Raises ValueError for type validation
Fix: Change to TypeError

--- TRY300: Consider else after return (67 issues) — LOW/MEDIUM ---

ID: ISSUE-3014
Category: ErrorHandling
Location: parser_2gis/cache/cache_utils.py:143
Severity: LOW
Description: Statement after return in try block — could be moved to else
Fix: Move `return cache_size_mb` to else block after the try

ID: ISSUE-3015
Category: ErrorHandling
Location: parser_2gis/cache/manager.py:1096
Severity: LOW
Description: Return in try block without else
Fix: Add else block

ID: ISSUE-3016
Category: ErrorHandling
Location: parser_2gis/cache/manager.py:1157
Severity: LOW
Description: Return in try block without else
Fix: Add else block

ID: ISSUE-3017
Category: ErrorHandling
Location: parser_2gis/cache/manager.py:1200
Severity: LOW
Description: Return in try block without else
Fix: Add else block

ID: ISSUE-3018
Category: ErrorHandling
Location: parser_2gis/cache/pool.py:121
Severity: LOW
Description: Return in try block without else
Fix: Add else block

ID: ISSUE-3019
Category: ErrorHandling
Location: parser_2gis/cache/pool.py:225
Severity: LOW
Description: Return in try block without else
Fix: Add else block

ID: ISSUE-3020
Category: ErrorHandling
Location: parser_2gis/cache/pool.py:357
Severity: LOW
Description: Return in try block without else
Fix: Add else block

ID: ISSUE-3021
Category: ErrorHandling
Location: parser_2gis/cache/serializer.py:147
Severity: LOW
Description: Return in try block without else
Fix: Add else block

--- TRY401: Verbose exception re-raise (33 issues) — LOW ---

ID: ISSUE-3022
Category: ErrorHandling
Location: parser_2gis/cache/manager.py (multiple)
Severity: LOW
Description: Unnecessarily re-raises exception with same message; adds verbosity without value
Fix: Use bare `raise` or let exception propagate naturally

================================================================================
CATEGORY: TypeAnnotation
Severity: MEDIUM
================================================================================

--- ANN401: Any type annotation (126 issues) — MEDIUM ---
Top impactful uses of Any:

ID: ISSUE-4001
Category: TypeAnnotation
Location: parser_2gis/application/layer.py:226
Severity: MEDIUM
Description: `value: Any` in CacheAdapter.set — loses type safety for cache values
Fix: Use TypeVar or generic type: `def set(self, key: str, value: T, ...) -> None`

ID: ISSUE-4002
Category: TypeAnnotation
Location: parser_2gis/application/layer.py:381
Severity: MEDIUM
Description: `execute_js(...) -> Any` — return type not specific
Fix: Return `dict[str, Any]` or create specific result type

ID: ISSUE-4003
Category: TypeAnnotation
Location: parser_2gis/cache/manager.py:95
Severity: MEDIUM
Description: Protocol `execute(...) -> Any` — loses query result type info
Fix: Use generic protocol: `execute(...) -> T`

ID: ISSUE-4004
Category: TypeAnnotation
Location: parser_2gis/cache/manager.py:111
Severity: MEDIUM
Description: Protocol `cursor() -> Any` — not specific
Fix: Return specific cursor protocol type

ID: ISSUE-4005
Category: TypeAnnotation
Location: parser_2gis/cache/manager.py:1248
Severity: MEDIUM
Description: `_exc_tb` parameter typed as Any in context manager
Fix: Use `types.TracebackType | None`

ID: ISSUE-4006
Category: TypeAnnotation
Location: parser_2gis/cache/pool.py:531
Severity: MEDIUM
Description: `_exc_tb` parameter typed as Any
Fix: Use `types.TracebackType | None`

ID: ISSUE-4007
Category: TypeAnnotation
Location: parser_2gis/cache/validator.py:95
Severity: MEDIUM
Description: `data: Any` in validation method
Fix: Use specific type like `dict[str, Any]`

ID: ISSUE-4008
Category: TypeAnnotation
Location: parser_2gis/cache/validator.py:284
Severity: MEDIUM
Description: `value: Any` in validation
Fix: Use Union of expected types

ID: ISSUE-4009
Category: TypeAnnotation
Location: parser_2gis/chrome/exceptions.py:46
Severity: MEDIUM
Description: `**kwargs: Any` in exception constructor
Fix: Define specific kwargs or use TypedDict

ID: ISSUE-4010
Category: TypeAnnotation
Location: parser_2gis/chrome/exceptions.py:89
Severity: MEDIUM
Description: `*args: Any, **kwargs: Any` in exception
Fix: Define specific parameters

ID: ISSUE-4011
Category: TypeAnnotation
Location: parser_2gis/chrome/remote.py:226
Severity: MEDIUM
Description: `port: Any` in ChromeRemote constructor
Fix: Use `int | str`

ID: ISSUE-4012
Category: TypeAnnotation
Location: parser_2gis/chrome/remote.py:674
Severity: MEDIUM
Description: `*args: Any, **kwargs: Any` in wrapped_send
Fix: Use ParamSpec for proper typing

ID: ISSUE-4013
Category: TypeAnnotation
Location: parser_2gis/chrome/remote.py:674
Severity: MEDIUM
Description: `wrapped_send -> Any` return type
Fix: Use specific return type from pychrome

ID: ISSUE-4014
Category: TypeAnnotation
Location: parser_2gis/chrome/remote.py:973
Severity: MEDIUM
Description: `execute_script -> Any` return type
Fix: Use `dict[str, Any]` or specific result type

ID: ISSUE-4015
Category: TypeAnnotation
Location: parser_2gis/chrome/remote.py:1037
Severity: MEDIUM
Description: `_execute_script_internal_impl -> Any`
Fix: Use specific return type

ID: ISSUE-4016
Category: TypeAnnotation
Location: parser_2gis/chrome/remote.py:1327
Severity: MEDIUM
Description: `execute_js -> Any` return type
Fix: Use specific result type

ID: ISSUE-4017
Category: TypeAnnotation
Location: parser_2gis/chrome/rate_limiter.py:127
Severity: MEDIUM
Description: `**kwargs: Any` in rate limiter decorator
Fix: Use ParamSpec and TypeVar

ID: ISSUE-4018
Category: TypeAnnotation
Location: parser_2gis/chrome/request_interceptor.py:144
Severity: MEDIUM
Description: `**kwargs: Any` in responseReceived handler
Fix: Define specific handler signature

ID: ISSUE-4019
Category: TypeAnnotation
Location: parser_2gis/chrome/request_interceptor.py:172
Severity: MEDIUM
Description: `**kwargs: Any` in loadingFailed handler
Fix: Define specific handler signature

ID: ISSUE-4020
Category: TypeAnnotation
Location: parser_2gis/chrome/request_interceptor.py:203
Severity: MEDIUM
Description: `**kwargs: Any` in requestWillBeSent handler
Fix: Define specific handler signature

--- Mypy Errors (47 errors in 31 files) — MEDIUM ---

ID: ISSUE-4021
Category: TypeAnnotation
Location: parser_2gis/parallel/common/signal_handler_common.py:82-83
Severity: MEDIUM
Description: Incompatible types in assignment — signal handler type mismatch
Fix: Properly type signal handler return value as `Callable[..., Any] | int | None`

ID: ISSUE-4022
Category: TypeAnnotation
Location: parser_2gis/infrastructure/resource_monitor.py:114
Severity: MEDIUM
Description: Returning Any from function declared to return int
Fix: Add explicit int() cast or type guard

ID: ISSUE-4023
Category: TypeAnnotation
Location: parser_2gis/infrastructure/resource_monitor.py:291
Severity: MEDIUM
Description: Returning Any from function declared to return float
Fix: Add explicit float() cast

ID: ISSUE-4024
Category: TypeAnnotation
Location: parser_2gis/chrome/exceptions.py:70,74
Severity: LOW
Description: Unused type: ignore comments — no longer needed
Fix: Remove unused `# type: ignore` comments

ID: ISSUE-4025
Category: TypeAnnotation
Location: parser_2gis/utils/path_utils.py:48,53
Severity: MEDIUM
Description: Callable has no attribute _allowed_dirs; returning Any
Fix: Add proper type annotation to decorated function; use cast()

ID: ISSUE-4026
Category: TypeAnnotation
Location: parser_2gis/cache/pool.py:211
Severity: MEDIUM
Description: Argument 4 to finalize has incompatible type LockType; expected RLock
Fix: Use correct lock type or add type: ignore with explanation

ID: ISSUE-4027
Category: TypeAnnotation
Location: parser_2gis/utils/decorators.py:324
Severity: MEDIUM
Description: Argument timeout to WaitConfig has incompatible type int | float | None; expected int | None
Fix: Cast to int or change WaitConfig to accept int | float

ID: ISSUE-4028
Category: TypeAnnotation
Location: parser_2gis/writer/writers/csv_buffer_manager.py:139
Severity: MEDIUM
Description: Argument 1 to TextIOWrapper has incompatible type mmap
Fix: Use proper buffered wrapper around mmap

ID: ISSUE-4029
Category: TypeAnnotation
Location: parser_2gis/writer/writers/csv_post_processor.py:89,157
Severity: MEDIUM
Description: No overload variant of DictReader matches argument types
Fix: Convert fieldnames to list; fix file handle type

ID: ISSUE-4030
Category: TypeAnnotation
Location: parser_2gis/writer/writers/csv_deduplicator.py:178
Severity: MEDIUM
Description: Need type annotation for line variable
Fix: Add explicit type annotation

ID: ISSUE-4031
Category: TypeAnnotation
Location: parser_2gis/parser/end_of_results.py:90
Severity: HIGH
Description: "object" not callable — likely calling a non-callable attribute
Fix: Check attribute type before calling; add type guard

ID: ISSUE-4032
Category: TypeAnnotation
Location: parser_2gis/parser/parsers/main_parser.py:340,703
Severity: MEDIUM
Description: Returning Any from function declared to return bool / dict
Fix: Add explicit type conversion or narrowing

ID: ISSUE-4033
Category: TypeAnnotation
Location: parser_2gis/parser/parsers/main_extractor.py:90
Severity: MEDIUM
Description: Returning Any from function declared to return str | None
Fix: Add str() conversion or type guard

ID: ISSUE-4034
Category: TypeAnnotation
Location: parser_2gis/parser/parsers/in_building.py:160
Severity: MEDIUM
Description: Argument 1 to loads has incompatible type str | None; expected str
Fix: Add None check before calling json.loads

ID: ISSUE-4035
Category: TypeAnnotation
Location: parser_2gis/parser/parsers/firm.py:281
Severity: MEDIUM
Description: Incompatible types in assignment — Any | None to dict
Fix: Add None check or use dict.get() pattern

ID: ISSUE-4036
Category: TypeAnnotation
Location: parser_2gis/parallel/merger.py:443
Severity: MEDIUM
Description: Argument 2 has incompatible type object | None; expected FrameType | None
Fix: Properly type signal frame argument

ID: ISSUE-4037
Category: TypeAnnotation
Location: parser_2gis/parser/factory.py:214
Severity: MEDIUM
Description: Too many arguments for BaseParser — type: ignore not covering error
Fix: Fix constructor call or update type: ignore

ID: ISSUE-4038
Category: TypeAnnotation
Location: parser_2gis/parallel/strategies.py:453-458
Severity: HIGH
Description: Item None of Any | None has no attribute __enter__/__exit__/parse/_cache
Fix: Add None check before using parser instance; use assert or walrus operator

ID: ISSUE-4039
Category: TypeAnnotation
Location: parser_2gis/parallel/url_parser.py:356
Severity: MEDIUM
Description: Incompatible types in assignment — BaseParser | MainParser to BaseParser | None
Fix: Widen variable type or narrow assigned value

ID: ISSUE-4040
Category: TypeAnnotation
Location: parser_2gis/cli/launcher.py:288
Severity: MEDIUM
Description: WriterOptions has no attribute format
Fix: Use correct attribute name or add attribute to WriterOptions

ID: ISSUE-4041
Category: TypeAnnotation
Location: parser_2gis/cli/formatter.py:117
Severity: LOW
Description: Function has no attribute _installed
Fix: Use proper sentinel or module-level flag

ID: ISSUE-4042
Category: TypeAnnotation
Location: parser_2gis/cli/formatter.py:139
Severity: MEDIUM
Description: Returning Any from function declared to return str
Fix: Add str() cast

ID: ISSUE-4043
Category: TypeAnnotation
Location: parser_2gis/tui_textual/screens/settings.py:38,199,370
Severity: LOW
Description: Unused type: ignore comments
Fix: Remove them

ID: ISSUE-4044
Category: TypeAnnotation
Location: parser_2gis/tui_textual/screens/parsing_screen.py:16
Severity: LOW
Description: Unused type: ignore comment
Fix: Remove it

ID: ISSUE-4045
Category: TypeAnnotation
Location: parser_2gis/tui_textual/screens/other_screens.py:14,189
Severity: LOW
Description: Unused type: ignore comments
Fix: Remove them

ID: ISSUE-4046
Category: TypeAnnotation
Location: parser_2gis/tui_textual/screens/main_menu.py:14
Severity: LOW
Description: Unused type: ignore comment
Fix: Remove it

ID: ISSUE-4047
Category: TypeAnnotation
Location: parser_2gis/tui_textual/screens/city_selector.py:16
Severity: LOW
Description: Unused type: ignore comment
Fix: Remove it

ID: ISSUE-4048
Category: TypeAnnotation
Location: parser_2gis/tui_textual/screens/category_selector.py:14
Severity: LOW
Description: Unused type: ignore comment
Fix: Remove it

ID: ISSUE-4049
Category: TypeAnnotation
Location: parser_2gis/tui_textual/app.py:173
Severity: LOW
Description: Unused type: ignore comment
Fix: Remove it

ID: ISSUE-4050
Category: TypeAnnotation
Location: parser_2gis/tui_textual/app.py:443
Severity: MEDIUM
Description: Returning Any from function declared to return list[dict[str, Any]]
Fix: Add explicit cast or type narrowing

ID: ISSUE-4051
Category: TypeAnnotation
Location: parser_2gis/tui_textual/app.py:531
Severity: MEDIUM
Description: Cannot determine type of theme — type narrowed to None
Fix: Initialize theme before use or add type guard

ID: ISSUE-4052
Category: TypeAnnotation
Location: parser_2gis/tui_textual/app.py:609
Severity: MEDIUM
Description: Untyped decorator makes function _run_parsing untyped
Fix: Add type annotations to decorator

ID: ISSUE-4053
Category: TypeAnnotation
Location: parser_2gis/application/layer.py:132
Severity: HIGH
Description: Incompatible return value type — got BaseParser | MainParser, expected BaseParser
Fix: Widen return type annotation or add cast

================================================================================
CATEGORY: Style
Severity: LOW/MEDIUM
================================================================================

--- SLF001: Private member access (72 issues) — LOW — intentional in many cases ---

ID: ISSUE-5001
Category: Style
Location: parser_2gis/cache/config_cache.py:278-279
Severity: LOW
Description: Private _instance access on get_config_cache function — singleton pattern
Fix: Consider using class-based singleton or module-level variable

ID: ISSUE-5002
Category: Style
Location: parser_2gis/cache/pool.py:45-66 (multiple)
Severity: LOW
Description: Private _value access on enum members — enum internal access
Fix: Use public enum API or add # noqa: SLF001 if intentional

ID: ISSUE-5003
Category: Style
Location: parser_2gis/chrome/http_cache.py:156-157
Severity: LOW
Description: Private _instance access on singleton
Fix: Use module-level variable or proper singleton class

ID: ISSUE-5004
Category: Style
Location: parser_2gis/chrome/remote.py:632-700 (multiple)
Severity: LOW
Description: Multiple _stopped, _send, _closed accesses — internal Chrome protocol access
Fix: These are pychrome internals; consider wrapping or adding noqa comments

ID: ISSUE-5005
Category: Style
Location: parser_2gis/chrome/browser.py:1020-1025
Severity: LOW
Description: Private _closed access on browser
Fix: Use public API or property

ID: ISSUE-5006
Category: Style
Location: parser_2gis/chrome/patches/pychrome.py:54
Severity: LOW
Description: Private _recv_loop access on pychrome WebSocket
Fix: Add noqa comment; this is a patch of external library

--- PTH123: builtin open() (37 issues) — LOW — pathlib migration ---

ID: ISSUE-5007
Category: Style
Location: parser_2gis/cache/config_cache.py:164
Severity: LOW
Description: open() should be Path.open()
Fix: Use Path(cities_path).open("rb")

ID: ISSUE-5008
Category: Style
Location: parser_2gis/cache/config_cache.py:172
Severity: LOW
Description: open() should be Path.open()
Fix: Use Path(cities_path).open(encoding="utf-8")

ID: ISSUE-5009
Category: Style
Location: parser_2gis/chrome/browser.py:170
Severity: LOW
Description: os.path.exists() should be Path.exists()
Fix: Use Path(path).exists()

ID: ISSUE-5010
Category: Style
Location: parser_2gis/chrome/remote.py:1400
Severity: LOW
Description: open() should be Path.open()
Fix: Use Path(filepath).open()

ID: ISSUE-5011
Category: Style
Location: parser_2gis/cli/config_service.py:118
Severity: LOW
Description: open() should be Path.open()
Fix: Use Path(filepath).open()

--- PTH110: os.path.exists (11 issues) — LOW ---

ID: ISSUE-5012
Category: Style
Location: parser_2gis/chrome/browser.py:170
Severity: LOW
Description: os.path.exists() should be Path.exists()
Fix: Use Path(path).exists()

--- PLC0415: Import not at top level (118 issues) — LOW/MEDIUM ---
Many are intentional (avoiding circular imports, lazy loading optional deps).

ID: ISSUE-5013
Category: Style
Location: parser_2gis/application/layer.py:109
Severity: LOW
Description: Lazy import get_parser to avoid circular dependency
Fix: Add # noqa: PLC0415 or restructure to avoid circular import

ID: ISSUE-5014
Category: Style
Location: parser_2gis/application/layer.py:204
Severity: LOW
Description: Lazy import CacheManager
Fix: Add # noqa: PLC0415 or restructure

ID: ISSUE-5015
Category: Style
Location: parser_2gis/application/layer.py:348
Severity: LOW
Description: Lazy import ChromeRemote
Fix: Add # noqa: PLC0415 or restructure

ID: ISSUE-5016
Category: Style
Location: parser_2gis/cache/config_cache.py:162
Severity: LOW
Description: Lazy import mmap for optional usage
Fix: Add # noqa: PLC0415

ID: ISSUE-5017
Category: Style
Location: parser_2gis/cache/config_cache.py:260
Severity: LOW
Description: Lazy import CATEGORIES_93
Fix: Add # noqa: PLC0415

--- EM102/EM101: f-string/string literal in exception (282 issues) — LOW ---

ID: ISSUE-5018
Category: Style
Location: parser_2gis/cache/manager.py:276-300 (6 instances)
Severity: LOW
Description: f-strings and string literals directly in raise statements
Fix: Assign to variable first: `msg = f"..."; raise ValueError(msg)`

--- PLR2004: Magic value comparison (19 issues) — LOW ---

ID: ISSUE-5019
Category: Style
Location: parser_2gis/chrome/browser.py:1331
Severity: LOW
Description: Magic value 2 in comparison
Fix: Define named constant: MIN_PROFILE_COUNT = 2

ID: ISSUE-5020
Category: Style
Location: parser_2gis/chrome/remote.py:411
Severity: LOW
Description: Magic value 2 in comparison
Fix: Define named constant

ID: ISSUE-5021
Category: Style
Location: parser_2gis/chrome/remote.py:981
Severity: LOW
Description: Magic value 100 in comparison
Fix: Define named constant: MAX_REDIRECTS = 100

--- N802: Function name not lowercase (3 issues) — LOW ---

ID: ISSUE-5022
Category: Style
Location: parser_2gis/chrome/request_interceptor.py:144
Severity: LOW
Description: Function name responseReceived should be lowercase
Fix: Rename to response_received — NOTE: this is a Chrome DevTools Protocol event name, renaming may break functionality. Add # noqa: N802

ID: ISSUE-5023
Category: Style
Location: parser_2gis/chrome/request_interceptor.py:172
Severity: LOW
Description: Function name loadingFailed should be lowercase
Fix: Rename to loading_failed — NOTE: CDP event name, add # noqa: N802

ID: ISSUE-5024
Category: Style
Location: parser_2gis/chrome/request_interceptor.py:203
Severity: LOW
Description: Function name requestWillBeSent should be lowercase
Fix: Rename to request_will_be_sent — NOTE: CDP event name, add # noqa: N802

================================================================================
CATEGORY: Redundancy
Severity: LOW/MEDIUM
================================================================================

--- ARG002: Unused method argument (5 issues) ---

ID: ISSUE-6001
Category: Redundancy
Location: parser_2gis/logger/visual_logger.py:243
Severity: LOW
Description: Unused argument: width in method
Fix: Remove argument or prefix with underscore: _width

ID: ISSUE-6002
Category: Redundancy
Location: parser_2gis/logger/visual_logger.py:379
Severity: LOW
Description: Unused argument: bold in method
Fix: Remove or prefix with underscore: _bold

ID: ISSUE-6003
Category: Redundancy
Location: parser_2gis/parallel/merger.py:362-363
Severity: MEDIUM
Description: Unused arguments: buffer_size, batch_size
Fix: Remove if not needed or implement functionality

ID: ISSUE-6004
Category: Redundancy
Location: parser_2gis/parallel/parallel_parser.py:675
Severity: MEDIUM
Description: Unused argument: output_file_path
Fix: Remove or implement

================================================================================
CATEGORY: Config
Severity: LOW
================================================================================

--- TC003/TC001: Type-checking imports (94 issues) — LOW ---
These imports are only used for type hints and could be moved into TYPE_CHECKING blocks for import performance.

ID: ISSUE-7001
Category: Config
Location: parser_2gis/chrome/browser.py:30
Severity: LOW
Description: types module import only used for type hints
Fix: Move to TYPE_CHECKING block

ID: ISSUE-7002
Category: Config
Location: parser_2gis/chrome/dom.py:11
Severity: LOW
Description: collections.abc.Callable import only used for type hints
Fix: Move to TYPE_CHECKING block

ID: ISSUE-7003
Category: Config
Location: parser_2gis/chrome/js_executor.py:13
Severity: LOW
Description: collections.abc.Callable import only used for type hints
Fix: Move to TYPE_CHECKING block

ID: ISSUE-7004
Category: Config
Location: parser_2gis/chrome/options.py:12
Severity: LOW
Description: pathlib import only used for type hints
Fix: Move to TYPE_CHECKING block

ID: ISSUE-7005
Category: Config
Location: parser_2gis/chrome/remote.py:28
Severity: LOW
Description: types import only used for type hints
Fix: Move to TYPE_CHECKING block

ID: ISSUE-7006
Category: Config
Location: parser_2gis/cli/arguments.py:18
Severity: LOW
Description: parser_2gis.config.Configuration import only used for type hints
Fix: Move to TYPE_CHECKING block

================================================================================
CATEGORY: TestGap
Severity: MEDIUM
================================================================================

ID: ISSUE-8001
Category: TestGap
Location: parser_2gis/parallel/common/csv_merge_common.py
Severity: MEDIUM
Description: merge_csv_files_common has complexity 29, 8 args, 102 statements — critical parallel merge logic lacks test coverage verification
Fix: Add comprehensive unit tests for all code paths

ID: ISSUE-8002
Category: TestGap
Location: parser_2gis/parallel/parallel_parser.py:703
Severity: MEDIUM
Description: merge_csv_files complexity 33 — most complex function in project
Fix: Add parametrized tests for all merge scenarios

ID: ISSUE-8003
Category: TestGap
Location: parser_2gis/cache/pool.py:230
Severity: MEDIUM
Description: get_connection complexity 22 — connection pool with many error paths
Fix: Add tests for each error path (pool full, connection dead, timeout, etc.)

ID: ISSUE-8004
Category: TestGap
Location: parser_2gis/parser/parsers/firm.py:151
Severity: MEDIUM
Description: _validate_initial_state complexity 23 — validation with 22 branches
Fix: Add tests for each validation branch

ID: ISSUE-8005
Category: TestGap
Location: parser_2gis/chrome/browser.py:508,823
Severity: MEDIUM
Description: kill() and close() both complexity 12 — browser lifecycle critical paths
Fix: Add tests for all cleanup scenarios

================================================================================
CATEGORY: Documentation
Severity: LOW
================================================================================

ID: ISSUE-9001
Category: Documentation
Location: parser_2gis/chrome/request_interceptor.py:144,172,203
Severity: LOW
Description: CDP event handler functions lack docstrings explaining event contract
Fix: Add docstrings describing expected event payload structure

ID: ISSUE-9002
Category: Documentation
Location: parser_2gis/cache/pool.py:230
Severity: LOW
Description: get_connection complex function lacks detailed docstring explaining connection lifecycle
Fix: Add comprehensive docstring with lifecycle diagram in comments

================================================================================
CATEGORY: Deprecated
Severity: LOW
================================================================================

ID: ISSUE-10001
Category: Deprecated
Location: parser_2gis/cache/manager.py (multiple DTZ005)
Severity: LOW
Description: datetime.now(tz=None) pattern — while not deprecated, it is discouraged in favor of timezone-aware datetimes
Fix: Migrate to datetime.now(timezone.utc) across entire codebase

================================================================================
SUMMARY STATISTICS
================================================================================

Category          | Count | HIGH | MEDIUM | LOW
------------------|-------|------|--------|-----
Critical          |    24 |   24 |      0 |   0
Performance       |    30 |   20 |     10 |   0
ErrorHandling     |    35 |    0 |     13 |  22
TypeAnnotation    |    33 |    3 |     20 |  10
Style             |    24 |    0 |      2 |  22
Redundancy        |     4 |    0 |      2 |   2
Config            |     6 |    0 |      0 |   6
TestGap           |     5 |    0 |      5 |   0
Documentation     |     2 |    0 |      0 |   2
Deprecated        |     1 |    0 |      0 |   1
------------------|-------|------|--------|-----
TOTAL             |   164 |   47 |     52 |  65

False Positives Noted:
- N802 (ISSUE-5022-5024): CDP event handler names must match protocol spec
- SLF001 (many): Intentional singleton/internal access patterns
- PLC0415 (many): Intentional lazy imports for circular dependency avoidance
- TRY300 (many): Style preference, not a correctness issue
- EM101/EM102 (282 issues): Controversial rule; many projects disable it

Top 5 Files by Issue Density:
1. parser_2gis/chrome/remote.py — 65 issues
2. parser_2gis/cache/manager.py — 33 issues
3. parser_2gis/parallel/parallel_parser.py — 31 issues
4. parser_2gis/utils/path_utils.py — 28 issues
5. parser_2gis/resources/cities_loader.py — 28 issues
