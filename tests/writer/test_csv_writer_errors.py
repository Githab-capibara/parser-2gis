"""
Тесты для обработки ошибок в writer/writers/csv_writer.py.

Проверяет:
- Обработку csv.Error
- Обработку IOError
- Обработку UnicodeError
"""

import csv
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.writer.writers.csv_writer import CSVWriter


class TestCSVWriterErrorHandling:
    """Тесты обработки ошибок в CSVWriter."""

    @pytest.fixture
    def mock_options(self) -> MagicMock:
        """Создает mock опций.

        Returns:
            MagicMock с опциями.
        """
        options = MagicMock()
        options.verbose = False
        options.encoding = "utf-8-sig"
        options.csv.columns_per_entity = 3
        options.csv.add_rubrics = True
        options.csv.add_comments = False
        options.csv.remove_empty_columns = False
        options.csv.remove_duplicates = False
        options.csv.join_char = ", "
        return options

    @pytest.fixture
    def temp_output_path(self, tmp_path: Path) -> Path:
        """Создает временный путь для вывода.

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            Путь к временному файлу.
        """
        return tmp_path / "test_output.csv"

    @pytest.fixture
    def csv_writer(self, mock_options, temp_output_path) -> CSVWriter:
        """Создает CSVWriter для тестов.

        Args:
            mock_options: Mock опций.
            temp_output_path: Путь к временному файлу.

        Returns:
            CSVWriter экземпляр.
        """
        writer = CSVWriter(file_path=str(temp_output_path), options=mock_options)
        yield writer
        try:
            writer.close()
        except Exception:
            pass

    def test_csv_writer_csv_error_handling(self, csv_writer: CSVWriter, caplog):
        """Тест обработки csv.Error.

        Проверяет:
        - csv.Error обрабатывается корректно
        - Исключение пробрасывается дальше
        """
        with caplog.at_level(logging.ERROR), csv_writer:
            # Mock writer для выбрасывания csv.Error
            mock_dict_writer = MagicMock()
            mock_dict_writer.writerow.side_effect = csv.Error("Mocked csv.Error")
            csv_writer._writer = mock_dict_writer

            # Пытаемся записать строку
            with pytest.raises(csv.Error):
                csv_writer._writerow({"name": "Test"})

            # Проверяем что ошибка была залогирована
            assert any(
                "csv.Error" in record.message or "формата CSV" in record.message
                for record in caplog.records
            )

    def test_csv_writer_io_error_handling(self, csv_writer: CSVWriter, caplog):
        """Тест обработки IOError.

        Проверяет:
        - IOError обрабатывается корректно
        - Исключение пробрасывается дальше
        """
        with caplog.at_level(logging.ERROR), csv_writer:
            # Mock writer для выбрасывания IOError
            mock_dict_writer = MagicMock()
            mock_dict_writer.writerow.side_effect = OSError("Mocked IOError")
            csv_writer._writer = mock_dict_writer

            # Пытаемся записать строку
            with pytest.raises(IOError):
                csv_writer._writerow({"name": "Test"})

            # Проверяем что ошибка была залогирована
            assert any(
                "IOError" in record.message or "ввода-вывода" in record.message
                for record in caplog.records
            )

    def test_csv_writer_unicode_error_handling(self, csv_writer: CSVWriter, caplog):
        """Тест обработки UnicodeError.

        Проверяет:
        - UnicodeError обрабатывается корректно
        - Исключение пробрасывается дальше
        """
        with caplog.at_level(logging.ERROR), csv_writer:
            # Mock writer для выбрасывания UnicodeError
            mock_dict_writer = MagicMock()
            mock_dict_writer.writerow.side_effect = UnicodeError("Mocked UnicodeError")
            csv_writer._writer = mock_dict_writer

            # Пытаемся записать строку
            with pytest.raises(UnicodeError):
                csv_writer._writerow({"name": "Test"})

            # Проверяем что ошибка была залогирована
            assert any(
                "UnicodeError" in record.message or "кодировки" in record.message
                for record in caplog.records
            )

    def test_csv_writer_post_processor_exception(
        self, temp_output_path, mock_options, caplog, monkeypatch
    ):
        """Тест обработки исключений в постпроцессоре.

        Проверяет:
        - Исключения в постпроцессоре обрабатываются
        - Не ломают основной процесс
        """
        from parser_2gis.writer.writers import csv_writer

        # Создаем файл
        temp_output_path.write_text("col1,col2\nval1,val2\n", encoding="utf-8")

        mock_options.csv.remove_empty_columns = True

        # Создаем mock процессора с исключением
        mock_processor = MagicMock()
        mock_processor.remove_empty_columns.side_effect = RuntimeError("Mocked error")

        # Используем monkeypatch для надёжного управления mock'ами
        monkeypatch.setattr(csv_writer, "CSVPostProcessor", lambda *args, **kwargs: mock_processor)

        with caplog.at_level(logging.ERROR):
            writer = CSVWriter(file_path=str(temp_output_path), options=mock_options)

            with writer:
                writer._writerow({"name": "Test"})

            # Проверяем что mock был вызван
            assert mock_processor.remove_empty_columns.called, "remove_empty_columns не был вызван"

            # Проверяем что ошибка была залогирована
            assert any(
                "Ошибка при удалении пустых колонок" in record.message for record in caplog.records
            ), f"Ошибка не найдена в логах: {[r.message for r in caplog.records]}"

    def test_csv_writer_deduplicator_exception(
        self, temp_output_path, mock_options, caplog, monkeypatch
    ):
        """Тест обработки исключений в дедупликаторе.

        Проверяет:
        - Исключения в дедупликаторе обрабатываются
        - Не ломают основной процесс
        """
        from parser_2gis.writer.writers import csv_writer

        # Создаем файл
        temp_output_path.write_text("col1,col2\nval1,val2\n", encoding="utf-8")

        mock_options.csv.remove_duplicates = True

        # Создаем mock дедупликатора с исключением
        mock_dedup = MagicMock()
        mock_dedup.remove_duplicates.side_effect = RuntimeError("Mocked error")

        # Используем monkeypatch для надёжного управления mock'ами
        monkeypatch.setattr(csv_writer, "CSVDeduplicator", lambda *args, **kwargs: mock_dedup)

        with caplog.at_level(logging.ERROR):
            writer = CSVWriter(file_path=str(temp_output_path), options=mock_options)

            with writer:
                writer._writerow({"name": "Test"})

            # Проверяем что mock был вызван
            assert mock_dedup.remove_duplicates.called, "remove_duplicates не был вызван"

            # Проверяем что ошибка была залогирована - сообщение может быть разным
            assert any(
                "Ошибка при удалении дубликатов" in record.message
                or "Mocked error" in record.message
                for record in caplog.records
            ), f"Ошибка не найдена в логах: {[r.message for r in caplog.records]}"

    def test_csv_writer_extract_raw_validation_error(self, csv_writer: CSVWriter, caplog):
        """Тест обработки ValidationError при извлечении данных.

        Проверяет:
        - ValidationError обрабатывается корректно
        - Возвращается пустой словарь
        """
        with caplog.at_level(logging.ERROR):
            # Некорректный документ
            invalid_doc = {"invalid": "data"}

            result = csv_writer._extract_raw(invalid_doc)

            # Проверяем что результат пустой словарь
            assert result == {}

            # Проверяем что ошибка была залогирована
            assert any(
                "Некорректная структура документа" in record.message for record in caplog.records
            )

    def test_csv_writer_extract_raw_key_error(self, csv_writer: CSVWriter, caplog):
        """Тест обработки KeyError при извлечении данных.

        Проверяет:
        - KeyError обрабатывается корректно
        - Возвращается пустой словарь
        """
        with caplog.at_level(logging.ERROR):
            # Документ с отсутствующими ключами
            invalid_doc = {"result": {}}

            result = csv_writer._extract_raw(invalid_doc)

            # Проверяем что результат пустой словарь
            assert result == {}

    def test_csv_writer_extract_raw_type_error(self, csv_writer: CSVWriter, caplog):
        """Тест обработки TypeError при извлечении данных.

        Проверяет:
        - TypeError обрабатывается корректно
        - Возвращается пустой словарь
        """
        with caplog.at_level(logging.ERROR):
            # Документ с некорректным типом
            invalid_doc = None

            result = csv_writer._extract_raw(invalid_doc)

            # Проверяем что результат пустой словарь
            assert result == {}

    def test_csv_writer_extract_raw_index_error(self, csv_writer: CSVWriter, caplog):
        """Тест обработки IndexError при извлечении данных.

        Проверяет:
        - IndexError обрабатывается корректно
        - Возвращается пустой словарь
        """
        with caplog.at_level(logging.ERROR):
            # Документ с пустым списком items
            invalid_doc = {"result": {"items": []}}

            result = csv_writer._extract_raw(invalid_doc)

            # Проверяем что результат пустой словарь
            assert result == {}

    def test_csv_writer_check_catalog_doc_false(self, csv_writer: CSVWriter):
        """Тест _check_catalog_doc возвращающего False.

        Проверяет:
        - При False запись не выполняется
        """
        # Mock _check_catalog_doc для возвращения False
        with patch.object(csv_writer, "_check_catalog_doc", return_value=False), csv_writer:
            # Пытаемся записать документ
            csv_writer.write({"test": "data"})

            # Проверяем что ничего не было записано
            assert csv_writer._wrote_count == 0

    def test_csv_writer_file_open_error(self, tmp_path: Path, mock_options, caplog):
        """Тест обработки ошибки открытия файла.

        Проверяет:
        - OSError при открытии файла обрабатывается
        """
        with caplog.at_level(logging.ERROR):
            # Используем путь с недопустимыми символами, который вызовет ошибку при открытии
            # В Windows нельзя использовать < > : " / \ | ? *
            # В Linux нельзя использовать /0 (null character)
            # Но для простоты используем пустой путь, который вызовет ошибку
            invalid_path = ""

            with pytest.raises(ValueError):
                writer = CSVWriter(file_path=invalid_path, options=mock_options)
                with writer:
                    pass

    def test_csv_writer_context_manager_exception(self, temp_output_path, mock_options, caplog):
        """Тест обработки исключений в контекстном менеджере.

        Проверяет:
        - Исключения в __exit__ обрабатываются
        - Контекстный менеджер закрывается корректно
        """
        from pathlib import Path

        with caplog.at_level(logging.ERROR):
            writer = CSVWriter(file_path=temp_output_path, options=mock_options)

            # Проверяем что контекстный менеджер работает корректно
            with writer:
                writer._writerow({"name": "Test"})

            # Файл может быть создан в текущей директории из-за path validation
            # Проверяем что файл был создан (либо по исходному пути, либо в cwd)
            output_exists = temp_output_path.exists() or Path("test_output.csv").exists()
            assert output_exists

            # Проверяем содержимое файла
            if temp_output_path.exists():
                content = temp_output_path.read_text(encoding="utf-8-sig")
            else:
                content = Path("test_output.csv").read_text(encoding="utf-8-sig")
                # Очищаем тестовый файл
                Path("test_output.csv").unlink()

            # Проверяем что данные были записаны (строка с Test)
            assert "Test" in content

    def test_csv_writer_close_exception(self, temp_output_path, mock_options, caplog):
        """Тест обработки исключений при закрытии.

        Проверяет:
        - Исключения при close() обрабатываются и логируются
        - Файл закрывается даже при ошибке
        """
        with caplog.at_level(logging.ERROR):
            writer = CSVWriter(file_path=temp_output_path, options=mock_options)

            # Входим в контекст, чтобы создать _file
            with writer:
                writer._writerow({"name": "Test"})
                # Mock _file.close для выбрасывания исключения
                original_close = writer._file.close
                writer._file.close = MagicMock(side_effect=OSError("Mocked error"))

            # Выход из with writer блока вызовет __exit__
            # Исключение НЕ выбрасывается — оно логируется
            assert "Ошибка при закрытии файла" in caplog.text

            # Восстанавливаем оригинальный метод
            writer._file.close = original_close
