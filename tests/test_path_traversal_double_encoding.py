"""
Тесты для исправлений CRITICAL проблем с path traversal.

Проверяет:
- Защиту от path traversal с двойным кодированием
- Валидацию путей с запрещёнными символами
"""

import tempfile
from pathlib import Path
from urllib.parse import quote

import pytest

from parser_2gis.utils.path_utils import validate_path_traversal


class TestPathTraversalDoubleEncoding:
    """Тесты для CRITICAL 5: Защита от path traversal с двойным кодированием."""

    def test_double_encoded_path_traversal_blocked(self) -> None:
        """Тест 1: Блокировка path traversal с двойным кодированием.

        Проверяет:
        - Двойное кодирование %252e%252e%252f блокируется
        - Путь с .. не проходит валидацию
        """
        # Двойное кодирование: %252e = %, 2e = .
        # %252e%252e%252f = %../
        double_encoded = "%252e%252e%252fetc%252fpasswd"

        with pytest.raises(ValueError, match="Path traversal|encoded опасный паттерн"):
            validate_path_traversal(double_encoded)

    def test_single_encoded_path_traversal_blocked(self) -> None:
        """Тест 2: Блокировка path traversal с одинарным кодированием.

        Проверяет:
        - Одинарное кодирование %2e%2e%2f блокируется
        - Путь с .. не проходит валидацию
        """
        # Одинарное кодирование: %2e = .
        # %2e%2e%2f = ../
        single_encoded = "%2e%2e%2fetc%2fpasswd"

        with pytest.raises(ValueError, match="Path traversal|encoded опасный паттерн"):
            validate_path_traversal(single_encoded)

    def test_encoded_dot_dot_slash_blocked(self) -> None:
        """Тест 3: Блокировка %2e%2e%2f (../).

        Проверяет:
        - Кодированный ../ блокируется
        - Валидация декодирует путь перед проверкой
        """
        encoded = quote("../etc/passwd")

        with pytest.raises(ValueError, match="Path traversal|encoded опасный паттерн"):
            validate_path_traversal(encoded)

    def test_encoded_backslash_traversal_blocked(self) -> None:
        """Тест 4: Блокировка path traversal с backslash.

        Проверяет:
        - ..\\ блокируется
        - Backslash в пути не допускается
        """
        traversal_path = "..\\..\\windows\\system32"

        with pytest.raises(ValueError, match="Path traversal|запрещённый символ"):
            validate_path_traversal(traversal_path)

    def test_mixed_encoding_traversal_blocked(self) -> None:
        """Тест 5: Блокировка смешанного кодирования.

        Проверяет:
        - Смешанное кодирование (часть encoded, часть plain) блокируется
        - Комбинации %2e./ блокируются
        """
        mixed = "%2e./etc/passwd"

        with pytest.raises(ValueError, match="Path traversal|encoded опасный паттерн"):
            validate_path_traversal(mixed)

    def test_triple_encoded_traversal_blocked(self) -> None:
        """Тест 6: Блокировка тройного кодирования.

        Проверяет:
        - Тройное кодирование блокируется
        - Многократное кодирование не обходит защиту
        """
        # Тройное кодирование: %25252e = %25. = %.
        triple_encoded = "%25252e%25252e%25252fetc"

        with pytest.raises(ValueError, match="Path traversal|encoded опасный паттерн"):
            validate_path_traversal(triple_encoded)

    def test_unicode_traversal_blocked(self) -> None:
        """Тест 7: Блокировка Unicode path traversal.

        Проверяет:
        - Unicode символы для .. блокируются
        - Кириллические символы не проходят
        """
        # Unicode encoding для ..
        unicode_traversal = "\u002e\u002e/etc/passwd"

        with pytest.raises(ValueError, match="Path traversal"):
            validate_path_traversal(unicode_traversal)

    def test_null_byte_injection_blocked(self) -> None:
        """Тест 8: Блокировка null byte инъекции.

        Проверяет:
        - Null byte (%00) блокируется
        - Инъекции через \x00 не проходят
        """
        null_byte_path = "/tmp/file\x00.txt"

        # Null byte вызывает ValueError при разрешении пути
        with pytest.raises(ValueError):
            validate_path_traversal(null_byte_path)

    def test_valid_path_passes(self) -> None:
        """Тест 9: Валидный путь проходит валидацию.

        Проверяет:
        - Нормальные пути проходят валидацию
        - Абсолютные пути работают
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            valid_path = Path(tmpdir) / "output.json"
            result = validate_path_traversal(str(valid_path))

            assert result.is_absolute()
            assert result.name == "output.json"

    def test_dollar_sign_in_path_blocked(self) -> None:
        """Тест 10: Блокировка $ в пути.

        Проверяет:
        - $ символ блокируется
        - Переменные окружения не расширяются
        """
        dollar_path = "/data/$VAR/file.json"

        with pytest.raises(ValueError, match="запрещённый символ"):
            validate_path_traversal(dollar_path)

    def test_tilde_in_path_blocked(self) -> None:
        """Тест 11: Блокировка ~ в пути.

        Проверяет:
        - ~ символ блокируется
        - Домашняя директория не расширяется
        """
        tilde_path = "~/data/file.json"

        with pytest.raises(ValueError, match="запрещённый символ"):
            validate_path_traversal(tilde_path)

    def test_semicolon_in_path_blocked(self) -> None:
        """Тест 12: Блокировка ; в пути.

        Проверяет:
        - ; символ блокируется
        - Инъекции команд не проходят
        """
        semicolon_path = "/tmp/file;rm -rf /.json"

        with pytest.raises(ValueError, match="запрещённый символ"):
            validate_path_traversal(semicolon_path)

    def test_pipe_in_path_blocked(self) -> None:
        """Тест 13: Блокировка | в пути.

        Проверяет:
        - | символ блокируется
        - Pipe инъекции не проходят
        """
        pipe_path = "/tmp/file|cat /etc/passwd.json"

        with pytest.raises(ValueError, match="запрещённый символ"):
            validate_path_traversal(pipe_path)

    def test_ampersand_in_path_blocked(self) -> None:
        """Тест 14: Блокировка & в пути.

        Проверяет:
        - & символ блокируется
        - Background команды не проходят
        """
        ampersand_path = "/tmp/file&echo hacked.json"

        with pytest.raises(ValueError, match="запрещённый символ"):
            validate_path_traversal(ampersand_path)

    def test_redirect_in_path_blocked(self) -> None:
        """Тест 15: Блокировка > < в пути.

        Проверяет:
        - > и < символы блокируются
        - Redirect инъекции не проходят
        """
        redirect_path = "/tmp/file>output.json"

        with pytest.raises(ValueError, match="запрещённый символ"):
            validate_path_traversal(redirect_path)

    def test_newline_in_path_blocked(self) -> None:
        """Тест 16: Блокировка newline в пути.

        Проверяет:
        - \n и \r блокируются
        - Multi-line инъекции не проходят
        """
        newline_path = "/tmp/file\n/etc/passwd.json"

        with pytest.raises(ValueError, match="запрещённый символ"):
            validate_path_traversal(newline_path)

    def test_backtick_in_path_blocked(self) -> None:
        """Тест 17: Блокировка ` в пути.

        Проверяет:
        - ` символ блокируется
        - Command substitution не проходит
        """
        backtick_path = "/tmp/file`whoami`.json"

        with pytest.raises(ValueError, match="запрещённый символ"):
            validate_path_traversal(backtick_path)

    def test_complex_encoded_traversal(self) -> None:
        """Тест 18: Сложное кодированное path traversal.

        Проверяет:
        - Сложные комбинации кодирования блокируются
        - %252e%2e%2f и подобные блокируются
        """
        complex_encoded = "%252e%2e%2f%252e%2e%2fetc%252fpasswd"

        with pytest.raises(ValueError, match="Path traversal|encoded опасный паттерн"):
            validate_path_traversal(complex_encoded)

    def test_nested_directory_traversal(self) -> None:
        """Тест 19: Вложенный path traversal.

        Проверяет:
        - ../../.. блокируется
        - Глубокая вложенность не обходит защиту
        """
        nested_path = "/tmp/../../../etc/passwd"

        with pytest.raises(ValueError, match="Path traversal"):
            validate_path_traversal(nested_path)

    def test_validate_path_creates_parent_directory(self) -> None:
        """Тест 20: Валидация создаёт родительскую директорию.

        Проверяет:
        - validate_path_traversal создаёт родительскую директорию
        - Путь нормализуется корректно
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "newdir" / "subdir" / "output.json"
            result = validate_path_traversal(str(nested_path))

            assert result.parent.exists(), "Родительская директория должна быть создана"
            assert result.name == "output.json"
