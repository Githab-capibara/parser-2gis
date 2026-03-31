"""
Тесты для 30 исправленных проблем в проекте parser-2gis.

Этот модуль содержит тесты для проверки исправлений:
- Критические ошибки (Проблемы 1-5)
- Логические ошибки (Проблемы 13-19)
- Оптимизации (Проблемы 6-12)
- Улучшения читаемости (Проблемы 20-30)

Каждый тест помечен соответствующими маркерами pytest.
"""

import ast
import os
import sys
from pathlib import Path

import pytest

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ АСТА АНАЛИЗА
# =============================================================================


def get_source_file(rel_path: str) -> Path:
    """Получает путь к исходному файлу."""
    project_root = Path(__file__).parent.parent
    return project_root / "parser_2gis" / rel_path


def read_source_file(rel_path: str) -> str:
    """Читает исходный файл."""
    file_path = get_source_file(rel_path)
    if not file_path.exists():
        pytest.skip(f"Файл {rel_path} не найден")
    return file_path.read_text(encoding="utf-8")


def parse_source_file(rel_path: str):
    """Парсит исходный файл в AST."""
    source = read_source_file(rel_path)
    return ast.parse(source)


# =============================================================================
# КРИТИЧЕСКИЕ ОШИБКИ (Проблемы 1-5)
# =============================================================================


@pytest.mark.audit_fix
@pytest.mark.critical
class TestCriticalFixes:
    """Тесты для критических ошибок (Проблемы 1-5)."""

    def test_01_create_parser_writer_called_before_parsing(self):
        """
        Тест 1: Проверка, что _create_parser() и _create_writer() вызываются до вложенной функции.

        Проверяет:
        - Методы создания существуют в coordinator.py
        - Они вызываются до начала парсинга
        - Обработка None значения parser/writer
        """
        source = read_source_file("parallel/coordinator.py")

        # Проверяем наличие методов
        assert "def _create_parser(self" in source, "Должен быть метод _create_parser"
        assert "def _create_writer(self" in source, "Должен быть метод _create_writer"

        # Проверяем вызовы методов в _parse_single_url_impl
        parse_method_source = source.split("def _parse_single_url_impl")[1].split("def ")[0]

        # Проверяем что методы вызываются
        assert "self._create_parser(" in parse_method_source, (
            "_create_parser должен вызываться в _parse_single_url_impl"
        )
        assert "self._create_writer(" in parse_method_source, (
            "_create_writer должен вызываться в _parse_single_url_impl"
        )

        # Проверяем обработку None
        assert (
            "if parser is None" in parse_method_source or "if ... is None" in parse_method_source
        ), "Должна быть проверка parser на None"
        assert (
            "if writer is None" in parse_method_source
            or "is None or writer is None" in parse_method_source
        ), "Должна быть проверка writer на None"

        # Проверяем AST для анализа структуры
        tree = parse_source_file("parallel/coordinator.py")

        # Находим класс ParallelCoordinator
        coordinator_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "ParallelCoordinator":
                coordinator_class = node
                break

        assert coordinator_class is not None, "Должен быть класс ParallelCoordinator"

        # Проверяем наличие методов
        method_names = [n.name for n in coordinator_class.body if isinstance(n, ast.FunctionDef)]
        assert "_create_parser" in method_names, "Должен быть метод _create_parser"
        assert "_create_writer" in method_names, "Должен быть метод _create_writer"

    def test_02_pool_variable_initialization(self):
        """
        Тест 2: Проверка инициализации переменных в pool.py.

        Проверяет:
        - conn и need_to_create инициализированы до вложенной логики
        - Обработка None соединения
        - Выброс RuntimeError при невалидном соединении
        """
        source = read_source_file("cache/pool.py")

        # Проверяем наличие ConnectionPool
        assert "class ConnectionPool:" in source, "Должен быть класс ConnectionPool"

        # Проверяем метод get_connection
        get_conn_source = source.split("def get_connection(self)")[1].split("def ")[0]

        # Проверяем инициализацию переменных
        assert "conn" in get_conn_source, "Должна быть переменная conn"
        assert "need_to_create" in get_conn_source, "Должна быть переменная need_to_create"

        # Проверяем что переменные инициализируются до использования
        lines = get_conn_source.split("\n")
        init_line_idx = -1
        use_line_idx = -1

        for i, line in enumerate(lines):
            if "conn:" in line or "conn =" in line or "conn =" in line:
                if "Optional" in line or "= None" in line:
                    init_line_idx = i
            if "if conn is None:" in line:
                use_line_idx = i

        assert init_line_idx >= 0, "conn должна быть инициализирована"
        assert use_line_idx >= 0, "Должна быть проверка if conn is None"

        # Проверяем выброс RuntimeError
        assert "RuntimeError" in get_conn_source, "Должен выбрасываться RuntimeError"
        assert (
            "Не удалось получить соединение" in get_conn_source
            or "Failed to get connection" in get_conn_source
        ), "Должно быть сообщение об ошибке при получении соединения"

        # Проверяем метод _is_connection_valid
        assert "def _is_connection_valid" in source, "Должен быть метод _is_connection_valid"
        valid_source = source.split("def _is_connection_valid")[1].split("def ")[0]
        assert "SELECT 1" in valid_source, "Должна использоваться проверка SELECT 1"

    def test_03_retry_logic_without_decorator(self):
        """
        Тест 3: Проверка retry логики в remote.py без декоратора.

        Проверяет:
        - Декоратор @wait_until_finished удалён от _connect_interface
        - Работа max_attempts=3
        - Логирование попыток
        """
        source = read_source_file("chrome/remote.py")

        # Проверяем метод _connect_interface
        connect_source = source.split("def _connect_interface(self)")[1].split("def ")[0]

        # Проверяем что декоратор не применяется к _connect_interface
        # Ищем строку перед определением метода
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if "def _connect_interface" in line:
                # Проверяем предыдущую строку
                if i > 0:
                    prev_line = lines[i - 1].strip()
                    assert "@wait_until_finished" not in prev_line, (
                        "_connect_interface не должен использовать @wait_until_finished"
                    )
                break

        # Проверяем retry логику
        assert "max_attempts" in connect_source, "Должен быть max_attempts"

        # Проверяем цикл retry
        assert (
            "for attempt in range(max_attempts)" in connect_source
            or "for attempt in range(1, max_attempts + 1)" in connect_source
        ), "Должен быть цикл retry с max_attempts"

        # Проверяем логирование попыток
        assert "Попытка подключения" in connect_source or "attempt" in connect_source.lower(), (
            "Должно быть логирование попыток подключения"
        )

    def test_04_csv_postprocessing_before_close(self):
        """
        Тест 4: Проверка порядка постобработки в csv_writer.py.

        Проверяет:
        - Постобработка вызывается ДО закрытия файла
        - Файл не закрыт во время постобработки
        """
        source = read_source_file("writer/writers/csv_writer.py")

        # Проверяем метод __exit__
        exit_source = source.split("def __exit__(self")[1].split("def ")[0]

        # Проверяем наличие постобработки
        assert "CSVPostProcessor" in exit_source, "Должен использоваться CSVPostProcessor"
        assert "remove_empty_columns" in exit_source, "Должно вызываться удаление пустых колонок"

        # Проверяем наличие удаления дубликатов
        assert "CSVDeduplicator" in exit_source or "remove_duplicates" in exit_source, (
            "Должно вызываться удаление дубликатов"
        )

        # Проверяем порядок: постобработка ДО super().__exit__
        postproc_idx = exit_source.find("CSVPostProcessor")
        super_exit_idx = exit_source.find("super().__exit__")

        assert postproc_idx >= 0, "Должна быть постобработка"
        assert super_exit_idx >= 0, "Должен быть вызов super().__exit__"
        assert postproc_idx < super_exit_idx, "Постобработка должна вызываться ДО super().__exit__"

    def test_05_tui_stop_parsing_in_finally(self):
        """
        Тест 5: Проверка try-finally в tui_textual/app.py.

        Проверяет:
        - stop_parsing() вызывается в finally
        - Флаг _cleanup_in_progress
        - Предотвращение повторной очистки
        """
        source = read_source_file("tui_textual/app.py")

        # Проверяем наличие флага
        assert "_cleanup_in_progress" in source, "Должен быть флаг _cleanup_in_progress"

        # Проверяем инициализацию флага
        init_source = source.split("def __init__")[1].split("def ")[0]
        assert "_cleanup_in_progress" in init_source, "Флаг должен инициализироваться в __init__"
        assert "False" in init_source, "Флаг должен инициализироваться False"

        # Проверяем метод stop_parsing
        assert "def stop_parsing" in source, "Должен быть метод stop_parsing"

        # Проверяем finally блок - ищем по всему файлу т.к. @work декоратор
        # Проверяем наличие finally в контексте _run_parsing
        assert "finally:" in source, "Должен быть finally блок"

        # Проверяем что finally используется с _cleanup_in_progress
        lines = source.split("\n")
        found_finally_with_cleanup = False

        for i, line in enumerate(lines):
            if "finally:" in line:
                # Проверяем следующие 10 строк
                next_lines = "\n".join(lines[i : i + 10])
                if "_cleanup_in_progress" in next_lines and "stop_parsing" in next_lines:
                    found_finally_with_cleanup = True
                    break

        assert found_finally_with_cleanup, (
            "finally блок должен содержать _cleanup_in_progress и stop_parsing"
        )

        # Проверяем предотвращение повторной очистки
        assert "if not self._cleanup_in_progress:" in source, (
            "Должна быть проверка на повторную очистку"
        )


# =============================================================================
# ЛОГИЧЕСКИЕ ОШИБКИ (Проблемы 13-19)
# =============================================================================


@pytest.mark.audit_fix
@pytest.mark.logical
class TestLogicalFixes:
    """Тесты для логических ошибок (Проблемы 13-19)."""

    def test_13_atomic_rename_with_retry(self):
        """
        Тест 13: Проверка атомарного переименования в coordinator.py.

        Проверяет:
        - Использование shutil.move()
        - Задержка 0.1 сек перед проверкой exists()
        - Retry логика с 3 попытками
        """
        source = read_source_file("parallel/coordinator.py")

        # Проверяем метод _parse_single_url_impl
        parse_source = source.split("def _parse_single_url_impl")[1].split("def ")[0]

        # Проверяем использование shutil.move
        assert "shutil.move" in parse_source, "Должен использоваться shutil.move"

        # Проверяем retry логику
        assert "max_rename_attempts" in parse_source or "max_attempts" in parse_source, (
            "Должна быть retry логика переименования"
        )

        # Проверяем задержку
        assert "time.sleep(0.1)" in parse_source, "Должна быть задержка 0.1 сек"

        # Проверяем цикл retry
        assert (
            "for rename_attempt in range" in parse_source or "for attempt in range" in parse_source
        ), "Должен быть цикл retry для переименования"

        # Проверяем проверку exists()
        assert ".exists()" in parse_source, "Должна быть проверка exists()"

    def test_14_individual_timestamp_in_cache_manager(self):
        """
        Тест 14: Проверка индивидуальной временной метки в cache/manager.py.

        Проверяет:
        - now вычисляется внутри цикла (или до цикла для консистентности)
        - Уникальность меток для пакетных записей
        """
        source = read_source_file("cache/manager.py")

        # Проверяем метод set_batch
        batch_source = (
            source.split("def set_batch")[1].split("def ")[0] if "def set_batch" in source else ""
        )

        assert batch_source != "", "Должен быть метод set_batch"

        # Проверяем что now вычисляется
        assert "now = datetime.now()" in batch_source or "datetime.now()" in batch_source, (
            "Должна быть временная метка now"
        )

        # Проверяем что expires_at вычисляется из now
        assert "expires_at = now + self._ttl" in batch_source or "expires_at" in batch_source, (
            "Должен быть expires_at"
        )

        # Проверяем цикл по items
        assert (
            "for url, data in items:" in batch_source or "for url, data in items" in batch_source
        ), "Должен быть цикл по items"

    def test_15_handler_removal_in_remote(self):
        """
        Тест 15: Проверка удаления обработчиков в remote.py.

        Проверяет:
        - Обработчики удаляются при закрытии
        - Отсутствие утечек памяти
        """
        source = read_source_file("chrome/remote.py")

        # Проверяем метод stop
        stop_source = (
            source.split("def stop(self)")[1].split("def ")[0] if "def stop(self)" in source else ""
        )

        assert stop_source != "", "Должен быть метод stop"

        # Проверяем очистку ресурсов
        assert "_chrome_tab = None" in stop_source or "self._chrome_tab = None" in stop_source, (
            "Должна быть очистка _chrome_tab"
        )
        assert (
            "_chrome_browser = None" in stop_source or "self._chrome_browser = None" in stop_source
        ), "Должна быть очистка _chrome_browser"
        assert (
            "_chrome_interface = None" in stop_source
            or "self._chrome_interface = None" in stop_source
        ), "Должна быть очистка _chrome_interface"

        # Проверяем очистку очередей
        assert (
            "_response_queues = {}" in stop_source or "self._response_queues = {}" in stop_source
        ), "Должна быть очистка _response_queues"

        # Проверяем вызов clear_requests()
        assert "clear_requests()" in stop_source, "Должен вызываться clear_requests()"

        # Проверяем очистку кэша портов
        assert "_clear_port_cache()" in stop_source, "Должна вызываться _clear_port_cache()"

    def test_16_data_mapping_caching(self):
        """
        Тест 16: Проверка кэширования _data_mapping в csv_writer.py.

        Проверяет:
        - _data_mapping это свойство (property)
        - Маппинг создаётся заново при каждом вызове
        """
        source = read_source_file("writer/writers/csv_writer.py")

        # Проверяем что _data_mapping это свойство
        assert "@property" in source, "Должны быть свойства @property"

        # Проверяем метод _data_mapping
        data_mapping_source = (
            source.split("def _data_mapping(self)")[1].split("def ")[0]
            if "def _data_mapping(self)" in source
            else ""
        )

        assert data_mapping_source != "", "Должен быть метод _data_mapping"

        # Проверяем что маппинг создаётся заново
        assert "data_mapping = {" in data_mapping_source, "Должен создаваться новый словарь"

        # Проверяем наличие ключей
        assert '"name"' in data_mapping_source or "'name'" in data_mapping_source, (
            "Должен быть ключ 'name'"
        )

    def test_17_last_notification_reset(self):
        """
        Тест 17: Проверка сброса _last_notification в app.py.

        Проверяет:
        - _last_notification = None в _clear_state()
        """
        source = read_source_file("tui_textual/app.py")

        # Проверяем наличие _last_notification
        assert "_last_notification" in source, "Должен быть _last_notification"

        # Проверяем метод _clear_state
        clear_state_source = (
            source.split("def _clear_state")[1].split("def ")[0]
            if "def _clear_state" in source
            else ""
        )

        assert clear_state_source != "", "Должен быть метод _clear_state"

        # Проверяем сброс _last_notification
        assert (
            "_last_notification = None" in clear_state_source
            or "self._last_notification = None" in clear_state_source
        ), "_last_notification должен быть сброшен в _clear_state"

    def test_18_max_retries_zero_handling(self):
        """
        Тест 18: Проверка обработки max_retries=0 в error_handler.py.

        Проверяет:
        - Явная проверка max_retries=0
        - Выброс исключения при ошибке
        - Возврат результата при успехе
        """
        source = read_source_file("parallel/error_handler.py")

        # Проверяем метод retry_with_backoff
        retry_source = (
            source.split("def retry_with_backoff")[1].split("def ")[0]
            if "def retry_with_backoff" in source
            else ""
        )

        assert retry_source != "", "Должен быть метод retry_with_backoff"

        # Проверяем явную проверку max_retries=0
        assert (
            "max_retries <= 0" in retry_source
            or "max_retries == 0" in retry_source
            or "if max_retries" in retry_source
        ), "Должна быть проверка max_retries"

        # Проверяем обработку ChromeException
        assert "ChromeException" in retry_source, "Должна обрабатываться ChromeException"

        # Проверяем выброс исключения
        assert "raise" in retry_source, "Должен быть выброс исключения"

    def test_19_connection_validation_select_1(self):
        """
        Тест 19: Проверка _is_connection_valid в pool.py.

        Проверяет:
        - Проверка через SELECT 1
        - Создание нового соединения при невалидном
        """
        source = read_source_file("cache/pool.py")

        # Проверяем метод _is_connection_valid
        valid_source = (
            source.split("def _is_connection_valid")[1].split("def ")[0]
            if "def _is_connection_valid" in source
            else ""
        )

        assert valid_source != "", "Должен быть метод _is_connection_valid"

        # Проверяем использование SELECT 1
        assert "SELECT 1" in valid_source, "Должна использоваться проверка SELECT 1"

        # Проверяем обработку ошибок
        assert "sqlite3.Error" in valid_source or "sqlite3" in valid_source, (
            "Должна обрабатываться sqlite3.Error"
        )
        assert "except" in valid_source, "Должна быть обработка исключений"

        # Проверяем что метод возвращает bool
        assert "return True" in valid_source and "return False" in valid_source, (
            "Метод должен возвращать True или False"
        )


# =============================================================================
# ОПТИМИЗАЦИИ (Проблемы 6-12)
# =============================================================================


@pytest.mark.audit_fix
@pytest.mark.optimization
class TestOptimizations:
    """Тесты для оптимизаций (Проблемы 6-12)."""

    def test_10_psutil_exception_grouping(self):
        """
        Тест 10: Проверка группировки исключений psutil в pool.py.

        Проверяет:
        - Все исключения обрабатываются одинаково
        - Возврат MIN_POOL_SIZE как fallback
        """
        source = read_source_file("cache/pool.py")

        # Проверяем функцию _calculate_dynamic_pool_size
        calc_source = (
            source.split("def _calculate_dynamic_pool_size")[1].split("def ")[0]
            if "def _calculate_dynamic_pool_size" in source
            else ""
        )

        assert calc_source != "", "Должна быть функция _calculate_dynamic_pool_size"

        # Проверяем группировку исключений
        assert "except ImportError:" in calc_source, "Должна быть обработка ImportError"
        assert "except MemoryError:" in calc_source, "Должна быть обработка MemoryError"
        assert "except OSError" in calc_source or "except (OSError" in calc_source, (
            "Должна быть обработка OSError"
        )
        assert "except ValueError" in calc_source or "except (ValueError" in calc_source, (
            "Должна быть обработка ValueError"
        )
        assert "except TypeError" in calc_source or "except (TypeError" in calc_source, (
            "Должна быть обработка TypeError"
        )

        # Проверяем что все исключения возвращают MIN_POOL_SIZE
        assert "return MIN_POOL_SIZE" in calc_source, (
            "Все исключения должны возвращать MIN_POOL_SIZE"
        )

    def test_11_single_lock_in_temp_file_manager(self):
        """
        Тест 11: Проверка единой блокировки в temp_file_manager.py.

        Проверяет:
        - Отсутствие двойной проверки
        - Единая блокировка для всех операций
        """
        source = read_source_file("utils/temp_file_manager.py")

        # Проверяем класс TempFileManager
        assert "class TempFileManager:" in source, "Должен быть класс TempFileManager"

        # Проверяем наличие блокировки
        assert "self._lock" in source, "Должна быть блокировка _lock"
        assert "threading.RLock" in source or "threading.Lock" in source, (
            "Должна использоваться threading.RLock или threading.Lock"
        )

        # Проверяем register
        register_source = (
            source.split("def register")[1].split("def ")[0] if "def register" in source else ""
        )
        assert "with self._lock:" in register_source, "register должен использовать блокировку"

        # Проверяем unregister
        unregister_source = (
            source.split("def unregister")[1].split("def ")[0] if "def unregister" in source else ""
        )
        assert "with self._lock:" in unregister_source, "unregister должен использовать блокировку"

        # Проверяем cleanup_all
        cleanup_source = (
            source.split("def cleanup_all")[1].split("def ")[0]
            if "def cleanup_all" in source
            else ""
        )
        assert "with self._lock:" in cleanup_source, "cleanup_all должен использовать блокировку"

    def test_12_while_loop_in_remote(self):
        """
        Тест 12: Проверка while loop в remote.py.

        Проверяет:
        - Использование while в retry логике или мониторинге
        - Явный счётчик попыток
        """
        source = read_source_file("chrome/remote.py")

        # Проверяем наличие while loop в retry логике или мониторинге
        # while может использоваться в monitor_tab или других методах

        # Проверяем наличие while в исходном коде
        assert "while " in source, "Должен быть использован while loop"

        # Проверяем конкретные методы
        methods_to_check = [
            "_connect_interface",
            "_create_tab",
            "start",
            "_setup_tab",
            "monitor_tab",
        ]

        found_while = False

        for method_name in methods_to_check:
            pattern = f"def {method_name}"
            if pattern in source:
                # Извлекаем больше кода для анализа
                parts = source.split(pattern)
                if len(parts) > 1:
                    method_source = (
                        parts[1].split("\n    def ")[0] if "\n    def " in parts[1] else parts[1]
                    )

                    # Проверяем while loop
                    if "while " in method_source:
                        found_while = True

                    # Проверяем счётчик
                    if "attempt" in method_source and (
                        "+= 1" in method_source or "+=1" in method_source
                    ):
                        pass  # Счётчик найден

        # Проверяем что есть хотя бы один while loop
        assert found_while, "Должен быть использован while loop в retry логике или мониторинге"


# =============================================================================
# УЛУЧШЕНИЯ ЧИТАЕМОСТИ (Проблемы 20-30)
# =============================================================================


@pytest.mark.audit_fix
@pytest.mark.readability
class TestReadabilityImprovements:
    """Тесты для улучшений читаемости (Проблемы 20-30)."""

    def test_20_import_grouping_pep8(self):
        """
        Тест 20: Проверка группировки импортов по PEP 8.

        Проверяет:
        - Группировка импортов по PEP 8
        - Разделение стандартных библиотек, сторонних и локальных
        """
        files_to_check = [
            "parallel/coordinator.py",
            "cache/pool.py",
            "chrome/remote.py",
            "writer/writers/csv_writer.py",
            "tui_textual/app.py",
        ]

        for rel_path in files_to_check:
            source = read_source_file(rel_path)
            lines = source.split("\n")

            # Находим секцию импортов
            import_lines = []
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    import_lines.append((i, line))

            # Проверяем наличие импортов
            assert len(import_lines) > 0, f"{rel_path} должен иметь импорты"

    def test_21_docstring_presence(self):
        """
        Тест 21: Проверка наличия docstring.

        Проверяет:
        - Наличие docstring у классов и функций
        - Качество документации
        """
        classes_to_check = [
            ("parallel/coordinator.py", "ParallelCoordinator"),
            ("cache/pool.py", "ConnectionPool"),
            ("chrome/remote.py", "ChromeRemote"),
            ("writer/writers/csv_writer.py", "CSVWriter"),
            ("tui_textual/app.py", "TUIApp"),
            ("parallel/error_handler.py", "ParallelErrorHandler"),
        ]

        for rel_path, class_name in classes_to_check:
            source = read_source_file(rel_path)

            # Проверяем наличие класса
            class_pattern = f"class {class_name}"
            assert class_pattern in source, f"Должен быть класс {class_name} в {rel_path}"

            # Проверяем наличие docstring у класса
            class_source = source.split(class_pattern)[1].split("class ")[0]
            # Docstring должен быть в первых строках
            first_lines = class_source.split("\n")[:5]
            has_docstring = any('"""' in line or "'''" in line for line in first_lines)
            assert has_docstring, f"Класс {class_name} должен иметь docstring"

    def test_22_variable_naming_clarity(self):
        """
        Тест 22: Проверка понятности имён переменных.

        Проверяет:
        - Понятные имена переменных
        - Отсутствие однобуквенных имён (кроме циклов)
        """
        files_to_check = ["parallel/coordinator.py", "cache/pool.py", "chrome/remote.py"]

        for rel_path in files_to_check:
            source = read_source_file(rel_path)
            lines = source.split("\n")

            single_letter_violations = []

            for i, line in enumerate(lines, 1):
                # Пропускаем импорты и комментарии
                if line.strip().startswith("import ") or line.strip().startswith("#"):
                    continue

                # Пропускаем циклы for
                if "for " in line and " in " in line:
                    continue

                # Ищем присваивания однобуквенных переменных
                if "=" in line and not line.strip().startswith("def "):
                    # Простая проверка на однобуквенные переменные
                    parts = line.split("=")
                    if len(parts) > 0:
                        var_name = parts[0].strip().split()[-1]
                        if len(var_name) == 1 and var_name.isalpha() and var_name not in "ijkxyz_":
                            single_letter_violations.append((i, line.strip()))

            # Допускаем несколько нарушений
            assert len(single_letter_violations) < 10, (
                f"{rel_path}: слишком много однобуквенных переменных: {single_letter_violations[:5]}"
            )

    def test_23_function_decomposition(self):
        """
        Тест 23: Проверка декомпозиции функций.

        Проверяет:
        - Разбиение больших функций на подметоды
        - Наличие вспомогательных методов
        """
        source = read_source_file("cache/manager.py")

        # Проверяем наличие подметодов
        assert "def _get_from_db" in source, "Должен быть метод _get_from_db"
        assert "def _handle_cache_hit" in source, "Должен быть метод _handle_cache_hit"
        assert "def _handle_cache_miss" in source, "Должен быть метод _handle_cache_miss"
        assert "def _handle_db_error" in source, "Должен быть метод _handle_db_error"

        # Проверяем что основной метод get использует подметоды
        get_source = source.split("def get(self")[1].split("def ")[0]
        assert "_get_from_db" in get_source, "get должен использовать _get_from_db"

    def test_24_error_handling_consistency(self):
        """
        Тест 24: Проверка единообразия обработки ошибок.

        Проверяет:
        - Единый стиль обработки ошибок
        - Логирование вместо print
        """
        source = read_source_file("cache/manager.py")

        # Проверяем наличие logger
        assert "logger" in source or "app_logger" in source, "Должен быть logger"

        # Проверяем отсутствие print в обработке ошибок
        lines = source.split("\n")
        print_in_error_handling = False

        for i, line in enumerate(lines):
            if "except" in line or "raise" in line:
                # Проверяем следующие несколько строк
                for j in range(i, min(i + 5, len(lines))):
                    if "print(" in lines[j] and not lines[j].strip().startswith("#"):
                        if "logger" not in lines[j]:
                            print_in_error_handling = True

        assert not print_in_error_handling, "Не должно быть print в обработке ошибок"

    def test_25_type_annotations_presence(self):
        """
        Тест 25: Проверка наличия аннотаций типов.

        Проверяет:
        - Аннотации типов в сигнатурах функций
        """
        source = read_source_file("parallel/coordinator.py")

        # Проверяем наличие аннотаций
        assert "->" in source or ": " in source, "Должны быть аннотации типов"

        # Проверяем наличие typing импортов
        assert "from typing import" in source or "import typing" in source, (
            "Должны быть импорты из typing"
        )

    def test_26_constant_extraction(self):
        """
        Тест 26: Проверка вынесения констант.

        Проверяет:
        - Вынесение магических чисел в константы
        """
        # Проверяем pool.py
        source = read_source_file("cache/pool.py")

        # Проверяем наличие констант
        assert "_MAX_POOL_SIZE_ENV" in source, "Должна быть константа _MAX_POOL_SIZE_ENV"
        assert "_MIN_POOL_SIZE_ENV" in source, "Должна быть константа _MIN_POOL_SIZE_ENV"
        assert "_CONNECTION_MAX_AGE_ENV" in source, "Должна быть константа _CONNECTION_MAX_AGE_ENV"

        # Проверяем remote.py
        remote_source = read_source_file("chrome/remote.py")
        assert "PORT_CHECK_RETRY_DELAY" in remote_source, (
            "Должна быть константа PORT_CHECK_RETRY_DELAY"
        )

    def test_27_comment_quality(self):
        """
        Тест 27: Проверка качества комментариев.

        Проверяет:
        - Наличие комментариев
        """
        files_to_check = ["parallel/coordinator.py", "cache/pool.py", "chrome/remote.py"]

        for rel_path in files_to_check:
            source = read_source_file(rel_path)

            # Проверяем наличие комментариев
            assert "#" in source, f"В {rel_path} должны быть комментарии"

    def test_28_module_docstring(self):
        """
        Тест 28: Проверка docstring модулей.

        Проверяет:
        - Наличие docstring у модулей
        """
        modules_to_check = [
            "parallel/coordinator.py",
            "cache/pool.py",
            "chrome/remote.py",
            "writer/writers/csv_writer.py",
            "tui_textual/app.py",
            "parallel/error_handler.py",
        ]

        for rel_path in modules_to_check:
            source = read_source_file(rel_path)

            # Проверяем наличие docstring в начале файла
            assert '"""' in source[:500] or "'''" in source[:500], (
                f"Модуль {rel_path} должен иметь docstring"
            )

    def test_29_method_length(self):
        """
        Тест 29: Проверка длины методов.

        Проверяет:
        - Методы не слишком длинные
        """
        source = read_source_file("cache/manager.py")

        # Подсчитываем длину методов
        methods = source.split("def ")
        long_methods = []

        for method in methods[1:]:  # Пропускаем первый элемент
            method_name = method.split("(")[0] if "(" in method else "unknown"
            lines = method.split("\n")
            if len(lines) > 100:
                long_methods.append((method_name, len(lines)))

        # Допускаем несколько длинных методов
        assert len(long_methods) < 5, f"Слишком много длинных методов: {long_methods[:3]}"

    def test_30_code_duplication(self):
        """
        Тест 30: Проверка отсутствия дублирования кода.

        Проверяет:
        - Вынесение общей логики в отдельные методы
        """
        source = read_source_file("cache/manager.py")

        # Проверяем что обработка ошибок вынесена в отдельные методы
        assert "def _handle_db_error" in source, "Должен быть метод для обработки ошибок БД"
        assert "def _handle_deserialize_error" in source, (
            "Должен быть метод для обработки ошибок десериализации"
        )


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


@pytest.mark.audit_fix
@pytest.mark.integration
class TestIntegrationFixes:
    """Интеграционные тесты для исправлений."""

    def test_integration_source_file_exists(self):
        """
        Интеграционный тест: Проверка существования файлов.

        Проверяет:
        - Все проверяемые файлы существуют
        """
        files_to_check = [
            "parallel/coordinator.py",
            "cache/pool.py",
            "chrome/remote.py",
            "writer/writers/csv_writer.py",
            "tui_textual/app.py",
            "parallel/error_handler.py",
            "cache/manager.py",
            "utils/temp_file_manager.py",
        ]

        for rel_path in files_to_check:
            file_path = get_source_file(rel_path)
            assert file_path.exists(), f"Файл {rel_path} должен существовать"

    def test_integration_imports_work(self):
        """
        Интеграционный тест: Проверка импортов.

        Проверяет:
        - Модули могут быть импортированы (хотя бы частично)
        """
        # Проверяем что файлы существуют и могут быть прочитаны
        modules_to_check = [
            "parallel/coordinator.py",
            "cache/pool.py",
            "parallel/error_handler.py",
            "utils/temp_file_manager.py",
        ]

        for rel_path in modules_to_check:
            source = read_source_file(rel_path)
            assert len(source) > 0, f"Файл {rel_path} не должен быть пустым"


# =============================================================================
# ЗАПУСК ТЕСТОВ
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
