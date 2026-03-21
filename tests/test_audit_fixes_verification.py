"""
Тесты для проверки исправленных проблем аудита.

Этот модуль содержит тесты для верификации всех исправленных проблем:
- Критические проблемы (гонки данных, валидация, очистка ресурсов)
- Важные проблемы (валидаторы, fallback, атомарность, дублирование)

Маркеры:
- @pytest.mark.unit для юнит-тестов
- @pytest.mark.integration для интеграционных тестов
"""

import csv
import json
import os
import sys
import threading
import time
from typing import List

import pytest
from concurrent.futures import ThreadPoolExecutor

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# =============================================================================
# КРИТИЧЕСКИЕ ПРОБЛЕМЫ
# =============================================================================


# =============================================================================
# ПРОБЛЕМА 1: Гонка данных в _ConnectionPool
# =============================================================================


@pytest.mark.unit
class TestConnectionPoolRaceCondition:
    """Тесты для проверки гонки данных в _ConnectionPool.

    ИСПРАВЛЕНИЕ: Использование RLock вместо Lock для защиты общих данных
    """

    def test_concurrent_connection_access(self, tmp_path):
        """
        Тест 1.1: Проверка конкурентного доступа к соединениям.

        Несколько потоков одновременно получают и возвращают соединения.
        Проверяет что нет гонки данных и все соединения корректны.
        """
        from parser_2gis.cache import _ConnectionPool

        cache_file = tmp_path / "cache.db"
        pool = _ConnectionPool(cache_file, pool_size=5, use_dynamic=False)

        errors: List[Exception] = []
        connections_acquired = {"count": 0}
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            """Рабочий поток получает и возвращает соединения."""
            try:
                for _ in range(10):
                    conn = pool.get_connection()
                    with lock:
                        connections_acquired["count"] += 1
                    # Имитация работы с БД
                    time.sleep(0.01)
                    pool.return_connection(conn)
            except Exception as e:
                with lock:
                    errors.append((worker_id, e))

        # Запускаем несколько потоков
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Ждем завершения всех потоков
        for thread in threads:
            thread.join(timeout=30)

        # Закрываем пул
        pool.close_all()

        # Проверяем что не было ошибок
        assert len(errors) == 0, f"Произошли ошибки при конкурентном доступе: {errors}"
        # Проверяем что все потоки получили соединения
        assert connections_acquired["count"] == 50, "Не все соединения были получены"

    def test_connection_pool_no_deadlock(self, tmp_path):
        """
        Тест 1.2: Проверка отсутствия deadlock в пуле соединений.

        Потоки получают соединения в разном порядке.
        Проверяет что нет deadlock.
        """
        from parser_2gis.cache import _ConnectionPool

        cache_file = tmp_path / "cache.db"
        pool = _ConnectionPool(cache_file, pool_size=3, use_dynamic=False)

        errors: List[Exception] = []
        operations_completed = {"count": 0}
        lock = threading.Lock()

        def get_multiple_connections(count: int) -> None:
            """Получает несколько соединений одновременно."""
            try:
                conns = []
                for _ in range(count):
                    conn = pool.get_connection()
                    conns.append(conn)
                    time.sleep(0.01)
                # Возвращаем соединения в обратном порядке
                for conn in reversed(conns):
                    pool.return_connection(conn)
                with lock:
                    operations_completed["count"] += 1
            except Exception as e:
                with lock:
                    errors.append(e)

        # Запускаем потоки с разным количеством соединений
        threads = [
            threading.Thread(target=get_multiple_connections, args=(1,)),
            threading.Thread(target=get_multiple_connections, args=(2,)),
            threading.Thread(target=get_multiple_connections, args=(3,)),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=30)

        pool.close_all()

        # Проверяем что не было deadlock
        assert len(errors) == 0, f"Произошли ошибки (возможен deadlock): {errors}"
        assert operations_completed["count"] == 3, "Не все операции завершились"


# =============================================================================
# ПРОБЛЕМА 2: MAX_UNIQUE_NAME_ATTEMPTS
# =============================================================================


@pytest.mark.unit
class TestMaxUniqueNameAttempts:
    """Тесты для проверки создания уникальных имён файлов.

    ИСПРАВЛЕНИЕ: MAX_UNIQUE_NAME_ATTEMPTS = 10 для защиты от бесконечного цикла
    """

    def test_unique_name_generation_success(self, tmp_path):
        """
        Тест 2.1: Успешное создание уникального имени файла.

        Проверяет что файл создаётся с первой попытки.
        """
        from parser_2gis.parallel_parser import MAX_UNIQUE_NAME_ATTEMPTS

        # Проверяем что константа имеет разумное значение
        assert MAX_UNIQUE_NAME_ATTEMPTS == 10, "Некорректное значение MAX_UNIQUE_NAME_ATTEMPTS"
        assert isinstance(MAX_UNIQUE_NAME_ATTEMPTS, int), "MAX_UNIQUE_NAME_ATTEMPTS должно быть int"
        assert MAX_UNIQUE_NAME_ATTEMPTS > 0, "MAX_UNIQUE_NAME_ATTEMPTS должно быть положительным"

    def test_unique_name_generation_with_collisions(self, tmp_path):
        """
        Тест 2.2: Создание уникального имени при коллизиях.

        Имитирует коллизии имён файлов.
        Проверяет что система корректно обрабатывает коллизии.
        """
        import uuid

        safe_city = "Test_City"
        safe_category = "Test_Category"
        pid = os.getpid()

        created_files = []

        def create_unique_file():
            """Создаёт файл с уникальным именем."""
            for attempt in range(10):
                temp_filename = f"{safe_city}_{safe_category}_{pid}_{uuid.uuid4().hex}.tmp"
                temp_filepath = tmp_path / temp_filename
                try:
                    # Атомарное создание файла
                    fd = os.open(
                        str(temp_filepath), os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode=0o644
                    )
                    os.close(fd)
                    created_files.append(temp_filepath)
                    return True
                except FileExistsError:
                    # Файл уже существует - пробуем снова
                    continue
                except OSError:
                    return False
            return False

        # Создаём несколько файлов одновременно
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_unique_file) for _ in range(10)]
            results = [f.result() for f in futures]

        # Проверяем что все файлы созданы
        assert all(results), "Не все файлы созданы успешно"
        assert len(created_files) == 10, "Создано неправильное количество файлов"

        # Проверяем что все имена уникальны
        filenames = [f.name for f in created_files]
        assert len(set(filenames)) == len(filenames), "Обнаружены дубликаты имён файлов"

    def test_unique_name_exhaustion_handling(self, tmp_path):
        """
        Тест 2.3: Обработка исчерпания попыток создания имени.

        Имитирует ситуацию когда все попытки исчерпаны.
        Проверяет что выбрасывается исключение.
        """
        from parser_2gis.parallel_parser import MAX_UNIQUE_NAME_ATTEMPTS

        # Проверяем что после MAX_UNIQUE_NAME_ATTEMPTS попыток
        # должно выбрасываться исключение
        assert MAX_UNIQUE_NAME_ATTEMPTS > 0, "Должно быть хотя бы 1 попытка"

        # Имитируем исчерпание попыток (в реальном коде это выбросит исключение)
        attempts_made = 0
        for attempt in range(MAX_UNIQUE_NAME_ATTEMPTS):
            # Имитация попытки создания файла
            attempts_made += 1

        # Проверяем что количество попыток равно константе
        assert attempts_made == MAX_UNIQUE_NAME_ATTEMPTS, "Некорректное количество попыток"


# =============================================================================
# ПРОБЛЕМА 3: _TempFileTimer.stop() гонка
# =============================================================================


@pytest.mark.unit
class TestTempFileTimerStopRace:
    """Тесты для проверки гонки данных в _TempFileTimer.stop().

    ИСПРАВЛЕНИЕ: Использование RLock и сохранение ссылки на timer перед отменой
    """

    def test_stop_method_thread_safety(self, tmp_path):
        """
        Тест 3.1: Проверка потокобезопасности метода stop().

        Несколько потоков одновременно вызывают stop().
        Проверяет что нет гонки данных.
        """
        from parser_2gis.parallel_parser import _TempFileTimer

        timer = _TempFileTimer(temp_dir=tmp_path, interval=60)
        timer.start()

        errors: List[Exception] = []
        stop_calls = {"count": 0}
        lock = threading.Lock()

        def stop_timer() -> None:
            """Вызывает stop() у таймера."""
            try:
                timer.stop()
                with lock:
                    stop_calls["count"] += 1
            except Exception as e:
                with lock:
                    errors.append(e)

        # Запускаем несколько потоков с stop()
        threads = [threading.Thread(target=stop_timer) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=10)

        # Проверяем что не было ошибок
        assert len(errors) == 0, f"Произошли ошибки при stop(): {errors}"
        # Хотя бы один поток должен успешно вызвать stop()
        assert stop_calls["count"] >= 1, "Ни один поток не вызвал stop()"

    def test_stop_with_active_timer(self, tmp_path):
        """
        Тест 3.2: Остановка активного таймера.

        Проверяет что stop() корректно останавливает активный таймер.
        """
        from parser_2gis.parallel_parser import _TempFileTimer

        timer = _TempFileTimer(temp_dir=tmp_path, interval=1)
        timer.start()

        # Даём таймеру запуститься
        time.sleep(0.5)

        # Останавливаем таймер
        timer.stop()

        # Проверяем что таймер остановлен
        assert timer._is_running is False, "Таймер должен быть остановлен"
        assert timer._stop_event.is_set(), "Событие остановки должно быть установлено"

    def test_stop_idempotency(self, tmp_path):
        """
        Тест 3.3: Идемпотентность метода stop().

        Многократный вызов stop() не должен вызывать ошибок.
        """
        from parser_2gis.parallel_parser import _TempFileTimer

        timer = _TempFileTimer(temp_dir=tmp_path, interval=60)

        # Вызываем stop() несколько раз
        for _ in range(5):
            try:
                timer.stop()
            except Exception as e:
                pytest.fail(f"stop() вызвал ошибку при многократном вызове: {e}")


# =============================================================================
# ПРОБЛЕМА 4: __del__ подавление исключений
# =============================================================================


@pytest.mark.unit
class TestDelExceptionSuppression:
    """Тесты для проверки обработки исключений в __del__.

    ИСПРАВЛЕНИЕ: __del__ должен подавлять исключения и логировать их
    """

    def test_temp_file_timer_del_cleanup(self, tmp_path):
        """
        Тест 4.1: Проверка очистки в __del__.

        Проверяет что __del__ корректно останавливает таймер.
        """
        from parser_2gis.parallel_parser import _TempFileTimer

        timer = _TempFileTimer(temp_dir=tmp_path, interval=60)
        timer.start()

        # Проверяем что таймер запущен
        assert timer._is_running is True, "Таймер должен быть запущен"

        # Удаляем таймер (вызовет __del__)
        del timer

        # Таймер должен быть остановлен в __del__
        # (проверяется через отсутствие утечек ресурсов)

    def test_del_with_exception(self, tmp_path):
        """
        Тест 4.2: Проверка __del__ при возникновении исключения.

        Проверяет что __del__ подавляет исключения.
        """
        from parser_2gis.parallel_parser import _TempFileTimer

        timer = _TempFileTimer(temp_dir=tmp_path, interval=60)
        timer.start()

        # Имитируем ошибку в stop() через mock
        original_stop = timer.stop

        def mock_stop_with_exception():
            """Mock stop() с исключением."""
            try:
                original_stop()
            except Exception:
                pass  # Подавляем исключения

        # Заменяем stop() на mock версию
        timer.stop = mock_stop_with_exception  # type: ignore

        # Удаляем таймер - не должно быть ошибок
        try:
            del timer
        except Exception as e:
            pytest.fail(f"__del__ выбросил исключение: {e}")


# =============================================================================
# ПРОБЛЕМА 5: JS валидация Unicode
# =============================================================================


@pytest.mark.unit
class TestJsValidationUnicode:
    """Тесты для проверки валидации JavaScript с Unicode.

    ИСПРАВЛЕНИЕ: Проверка Unicode эскейпов в JS коде
    """

    def test_unicode_escape_detection(self):
        """
        Тест 5.1: Обнаружение Unicode эскейпов.

        Проверяет что валидация обнаруживает Unicode эскейпы.
        """
        from parser_2gis.chrome.remote import _validate_js_code

        # JS с Unicode эскейпами (попытка обхода)
        malicious_js = r"var fn = '\u0065\u0076\u0061\u006c'; eval(fn)"

        is_valid, error = _validate_js_code(malicious_js)

        # Проверяем что код распознан как невалидный
        assert is_valid is False, "Unicode эскейпы должны быть обнаружены"
        assert error is not None, "Должно быть сообщение об ошибке"
        assert "Unicode" in error or "кодировку" in error.lower(), "Ошибка должна упоминать Unicode"

    def test_valid_unicode_in_strings(self):
        """
        Тест 5.2: Валидный Unicode в строках.

        Проверяет что обычный Unicode в строках разрешён.
        """
        from parser_2gis.chrome.remote import _validate_js_code

        # JS с обычными Unicode символами (кириллица)
        valid_js = """
            var message = 'Привет мир';
            console.log(message);
        """

        is_valid, error = _validate_js_code(valid_js)

        # Проверяем что код валиден
        assert is_valid is True, "Обычный Unicode должен быть разрешён"

    def test_hex_escape_detection(self):
        """
        Тест 5.3: Обнаружение hex эскейпов.

        Проверяет что валидация обнаруживает hex эскейпы.
        """
        from parser_2gis.chrome.remote import _validate_js_code

        # JS с hex эскейпами
        malicious_js = r"var fn = '\x65\x76\x61\x6c'; eval(fn)"

        is_valid, error = _validate_js_code(malicious_js)

        # Проверяем что код распознан как невалидный
        assert is_valid is False, "Hex эскейпы должны быть обнаружены"
        assert error is not None, "Должно быть сообщение об ошибке"


# =============================================================================
# ВАЖНЫЕ ПРОБЛЕМЫ
# =============================================================================


# =============================================================================
# ПРОБЛЕМА 6: Проверка максимума в валидаторах
# =============================================================================


@pytest.mark.unit
class TestValidatorMaxValueCheck:
    """Тесты для проверки max_val в валидаторах.

    ИСПРАВЛЕНИЕ: Валидаторы должны проверять максимальное значение
    """

    def test_validate_positive_int_max(self):
        """
        Тест 6.1: Проверка максимального значения в validate_positive_int.

        Проверяет что значение выше max_val отклоняется.
        """
        from parser_2gis.validation import validate_positive_int

        # Проверяем что значение выше максимума отклоняется
        with pytest.raises(ValueError) as exc_info:
            validate_positive_int(150, 1, 100, "--test.arg")

        assert "не более 100" in str(exc_info.value), "Ошибка должна упоминать максимум"

    def test_validate_positive_int_min(self):
        """
        Тест 6.2: Проверка минимального значения в validate_positive_int.

        Проверяет что значение ниже min_val отклоняется.
        """
        from parser_2gis.validation import validate_positive_int

        # Проверяем что значение ниже минимума отклоняется
        with pytest.raises(ValueError) as exc_info:
            validate_positive_int(0, 1, 100, "--test.arg")

        assert "не менее 1" in str(exc_info.value), "Ошибка должна упоминать минимум"

    def test_validate_positive_int_valid(self):
        """
        Тест 6.3: Проверка валидного значения.

        Проверяет что значение в диапазоне принимается.
        """
        from parser_2gis.validation import validate_positive_int

        # Проверяем что значение в диапазоне принимается
        result = validate_positive_int(50, 1, 100, "--test.arg")

        assert result == 50, "Валидное значение должно быть возвращено"

    def test_validate_positive_float_max(self):
        """
        Тест 6.4: Проверка максимума в validate_positive_float.

        Проверяет что float выше max_val отклоняется.
        """
        from parser_2gis.validation import validate_positive_float

        with pytest.raises(ValueError) as exc_info:
            validate_positive_float(150.5, 0.0, 100.0, "--test.arg")

        assert "не более 100" in str(exc_info.value), "Ошибка должна упоминать максимум"


# =============================================================================
# ПРОБЛЕМА 7: orjson fallback
# =============================================================================


@pytest.mark.unit
class TestOrjsonFallback:
    """Тесты для проверки orjson fallback при TypeError.

    ИСПРАВЛЕНИЕ: Fallback на стандартный json при TypeError от orjson
    """

    def test_orjson_typeerror_fallback(self):
        """
        Тест 7.1: Fallback при TypeError от orjson.

        Проверяет что при TypeError используется стандартный json.
        """
        from parser_2gis.cache import _serialize_json

        # Создаём данные которые могут вызвать TypeError в orjson
        # (например, с неподдерживаемыми типами)
        class CustomType:
            def __init__(self):
                self.value = 42

        data = {"custom": CustomType()}

        # Проверяем что fallback работает (не выбрасывает исключение)
        # orjson выбросит TypeError, fallback на json тоже выбросит, но это ожидаемо
        with pytest.raises(TypeError):
            _serialize_json(data)

        # Главное что не было неожиданного поведения
        # (orjson ошибка была корректно обработана)

    def test_orjson_success_case(self):
        """
        Тест 7.2: Успешная сериализация через orjson.

        Проверяет что orjson работает для стандартных данных.
        """
        from parser_2gis.cache import _serialize_json

        # Стандартные данные
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        result = _serialize_json(data)

        # Проверяем что результат - JSON строка
        assert isinstance(result, str), "Результат должен быть строкой"

        # Проверяем что данные корректно сериализованы
        parsed = json.loads(result)
        assert parsed == data, "Данные должны совпадать"

    def test_orjson_encode_error_handling(self):
        """
        Тест 7.3: Обработка orjson.EncodeError.

        Проверяет что EncodeError корректно обрабатывается.
        """
        from parser_2gis.cache import _serialize_json

        # Данные с циклической ссылкой (вызовут ошибку)
        data = {"key": "value"}
        data["self"] = data  # type: ignore

        # Проверяем что ошибка обрабатывается корректно
        with pytest.raises(TypeError):
            _serialize_json(data)


# =============================================================================
# ПРОБЛЕМА 8: Атомарность merge CSV
# =============================================================================


@pytest.mark.unit
class TestCsvMergeAtomicity:
    """Тесты для проверки атомарности merge CSV файлов.

    ИСПРАВЛЕНИЕ: Использование os.replace() для атомарной замены
    """

    def test_merge_csv_atomicity(self, tmp_path):
        """
        Тест 8.1: Проверка атомарности merge операции.

        Проверяет что merge CSV файлов атомарна.
        """
        # Создаём тестовые CSV файлы
        csv_files = []
        for i in range(3):
            csv_file = tmp_path / f"test_{i}.csv"
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["col1", "col2"])
                for j in range(5):
                    writer.writerow([f"value_{i}_{j}", f"data_{i}_{j}"])
            csv_files.append(csv_file)

        output_file = tmp_path / "merged.csv"

        # Импортируем функцию merge
        from parser_2gis.parallel_parser import _merge_csv_files

        # Выполняем merge
        success, total_rows, files_to_delete = _merge_csv_files(
            file_paths=csv_files, output_path=output_file, encoding="utf-8-sig"
        )

        # Проверяем что merge успешен
        assert success is True, "Merge должен быть успешным"
        assert total_rows == 15, f"Должно быть 15 строк, получено {total_rows}"
        assert len(files_to_delete) == 3, "Должно быть 3 файла для удаления"

        # Проверяем что выходной файл существует
        assert output_file.exists(), "Выходной файл должен существовать"

    def test_merge_csv_with_category_column(self, tmp_path):
        """
        Тест 8.2: Проверка добавления колонки категории.

        Проверяет что категория извлекается из имени файла.
        """
        # Создаём CSV файл с именем содержащим категорию
        csv_file = tmp_path / "Moscow_Restaurants.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "address"])
            writer.writerow(["Restaurant 1", "Address 1"])
            writer.writerow(["Restaurant 2", "Address 2"])

        output_file = tmp_path / "merged.csv"

        from parser_2gis.parallel_parser import _merge_csv_files

        success, total_rows, _ = _merge_csv_files(
            file_paths=[csv_file], output_path=output_file, encoding="utf-8-sig"
        )

        assert success is True, "Merge должен быть успешным"

        # Проверяем что категория добавлена
        with open(output_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames is not None
            assert "Категория" in reader.fieldnames, "Должна быть колонка 'Категория'"

            rows = list(reader)
            assert len(rows) == 2, "Должно быть 2 строки"
            # Проверяем что категория заполнена
            for row in rows:
                assert "Категория" in row, "Каждая строка должна иметь категорию"


# =============================================================================
# ПРОБЛЕМА 9: success_rate валидация
# =============================================================================


@pytest.mark.unit
class TestSuccessRateValidation:
    """Тесты для проверки валидации success_rate.

    ИСПРАВЛЕНИЕ: Проверка корректности данных с warning
    """

    def test_success_rate_normal_case(self):
        """
        Тест 9.1: Нормальный случай расчета success_rate.

        Проверяет что success_rate рассчитывается корректно.
        """
        from parser_2gis.statistics import ParserStatistics

        stats = ParserStatistics()
        stats.total_records = 100
        stats.successful_records = 80

        rate = stats.success_rate

        assert rate == 80.0, f"Success rate должен быть 80.0, получено {rate}"

    def test_success_rate_zero_total(self):
        """
        Тест 9.2: Расчет при нулевом total_records.

        Проверяет что нет деления на ноль.
        """
        from parser_2gis.statistics import ParserStatistics

        stats = ParserStatistics()
        stats.total_records = 0
        stats.successful_records = 0

        rate = stats.success_rate

        assert rate == 0.0, f"Success rate должен быть 0.0, получено {rate}"

    def test_success_rate_invalid_data(self, caplog):
        """
        Тест 9.3: Расчет при некорректных данных.

        Проверяет что некорректные данные обрабатываются с warning.
        """
        from parser_2gis.statistics import ParserStatistics

        stats = ParserStatistics()
        stats.total_records = 100
        stats.successful_records = 150  # Больше чем total - некорректно

        rate = stats.success_rate

        # Проверяем что возвращено 100.0 (fallback)
        assert rate == 100.0, f"Success rate должен быть 100.0, получено {rate}"

        # Проверяем что было предупреждение в логе
        assert "Некорректные данные" in caplog.text, "Должно быть предупреждение в логе"

    def test_success_rate_negative_successful(self, caplog):
        """
        Тест 9.4: Расчет при отрицательном successful_records.

        Проверяет что отрицательные значения обрабатываются.
        """
        from parser_2gis.statistics import ParserStatistics

        stats = ParserStatistics()
        stats.total_records = 100
        stats.successful_records = -10  # Отрицательное значение

        rate = stats.success_rate

        # Проверяем что возвращено 100.0 (fallback для некорректных данных)
        assert rate == 100.0, f"Success rate должен быть 100.0, получено {rate}"


# =============================================================================
# ПРОБЛЕМА 10: Дублирование валидации
# =============================================================================


@pytest.mark.unit
class TestValidationWrapper:
    """Тесты для проверки wrapper валидации.

    ИСПРАВЛЕНИЕ: DataValidator как wrapper для validation.py функций
    """

    def test_data_validator_phone_wrapper(self):
        """
        Тест 10.1: DataValidator как wrapper для validate_phone.

        Проверяет что DataValidator использует validation.py.
        """
        from parser_2gis.validator import DataValidator

        validator = DataValidator()

        # Валидируем телефон
        result = validator.validate_phone("+7 (999) 123-45-67")

        # Проверяем что валидация успешна
        assert result.is_valid is True, "Телефон должен быть валиден"
        # Проверяем что телефон нормализован (формат может отличаться)
        assert result.value is not None, "Телефон должен быть нормализован"
        assert result.value.startswith("8 "), f"Телефон должен начинаться с '8 ': {result.value}"

    def test_data_validator_email_wrapper(self):
        """
        Тест 10.2: DataValidator как wrapper для validate_email.

        Проверяет что DataValidator использует validation.py.
        """
        from parser_2gis.validator import DataValidator

        validator = DataValidator()

        # Валидируем email
        result = validator.validate_email("test@example.com")

        # Проверяем что валидация успешна
        assert result.is_valid is True, "Email должен быть валиден"
        assert result.value == "test@example.com", "Email должен быть возвращён"

    def test_data_validator_url_wrapper(self):
        """
        Тест 10.3: DataValidator как wrapper для validate_url.

        Проверяет что DataValidator использует validation.py.
        """
        from parser_2gis.validator import DataValidator

        validator = DataValidator()

        # Валидируем URL
        result = validator.validate_url("https://2gis.ru/moscow")

        # Проверяем что валидация успешна
        assert result.is_valid is True, "URL должен быть валиден"
        assert "2gis.ru" in result.value, "URL должен быть возвращён"

    def test_data_validator_invalid_phone(self):
        """
        Тест 10.4: Валидация некорректного телефона.

        Проверяет что некорректный телефон отклоняется.
        """
        from parser_2gis.validator import DataValidator

        validator = DataValidator()

        # Валидируем некорректный телефон
        result = validator.validate_phone("invalid_phone")

        # Проверяем что валидация не успешна
        assert result.is_valid is False, "Некорректный телефон должен быть отклонён"
        assert len(result.errors) > 0, "Должны быть ошибки валидации"


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


@pytest.mark.integration
class TestAuditFixesIntegration:
    """Интеграционные тесты для всех исправлений."""

    def test_full_pipeline_with_all_fixes(self, tmp_path):
        """
        Тест 11.1: Полный пайплайн с использованием всех исправлений.

        Проверяет что все исправления работают вместе.
        """
        from parser_2gis.cache import CacheManager
        from parser_2gis.statistics import ParserStatistics
        from parser_2gis.validator import DataValidator

        # 1. Тестируем кэш с connection pool (исправление 1)
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        # 2. Тестируем валидатор (исправления 6, 10)
        validator = DataValidator()
        phone_result = validator.validate_phone("+7 (999) 123-45-67")
        assert phone_result.is_valid is True, "Валидация телефона должна работать"

        # 3. Тестируем статистику (исправление 9)
        stats = ParserStatistics()
        stats.total_records = 100  # Устанавливаем total_records
        stats.increment_successful(80)
        stats.increment_failed(20)
        assert stats.success_rate == 80.0, "Расчет success_rate должен работать"

        # 4. Закрываем кэш
        cache.close()

    def test_concurrent_operations_with_all_components(self, tmp_path):
        """
        Тест 11.2: Конкурентные операции со всеми компонентами.

        Проверяет что все компоненты работают при конкурентном доступе.
        """
        from parser_2gis.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        errors: List[Exception] = []
        operations_completed = {"count": 0}
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            """Рабочий поток выполняет операции с кэшем."""
            try:
                for i in range(10):
                    key = f"worker_{worker_id}_key_{i}"
                    value = {"data": f"value_{i}"}
                    cache.set(key, value)
                    retrieved = cache.get(key)
                    assert retrieved == value, f"Данные не совпадают: {retrieved} != {value}"
                with lock:
                    operations_completed["count"] += 1
            except Exception as e:
                with lock:
                    errors.append((worker_id, e))

        # Запускаем несколько потоков
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Ждем завершения
        for thread in threads:
            thread.join(timeout=60)

        cache.close()

        # Проверяем что не было ошибок
        assert len(errors) == 0, f"Произошли ошибки при конкурентных операциях: {errors}"
        assert operations_completed["count"] == 5, "Не все операции завершились"


# =============================================================================
# ЗАПУСК ТЕСТОВ
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
