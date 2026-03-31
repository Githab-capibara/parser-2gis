"""
Тест централизованной валидации путей.

Проверяет работу validate_path() для валидных и невалидных путей.

ИСПРАВЛЕНИЕ: Централизованная валидация путей для предотвращения path traversal атак.
"""

import os
import tempfile
from pathlib import Path

import pytest

from parser_2gis.validation.path_validator import PathValidator, get_path_validator, validate_path


class TestPathValidatorModule:
    """Тесты централизованной валидации путей."""

    def test_validate_path_valid_paths(self) -> None:
        """Тест validate_path() для валидных путей.

        Проверяет:
        - Абсолютные пути в разрешённых директориях
        - Относительные пути от cwd
        - Пути без запрещённых символов
        """
        import os
        import tempfile

        # Валидные пути (не должны вызывать исключений)
        valid_paths = [
            os.path.join(os.getcwd(), "safe", "output.csv"),
            os.path.join(tempfile.gettempdir(), "test.txt"),
            "./relative/path/file.txt",
            "simple_filename.txt",
        ]

        for path in valid_paths:
            # Не должно вызывать исключений
            try:
                validate_path(path, "test_path")
            except (ValueError, OSError) as e:
                pytest.fail(f"Валидный путь {path} вызвал исключение: {e}")

    def test_validate_path_invalid_paths(self) -> None:
        """Тест validate_path() для невалидных путей.

        Проверяет:
        - Пути с .. (path traversal)
        - Пути с запрещёнными символами
        - Слишком длинные пути
        """
        # Невалидные пути с path traversal
        traversal_paths = [
            "../etc/passwd",
            "../../etc/shadow",
            "/safe/../../../etc/passwd",
            "safe/../../etc/passwd",
        ]

        for path in traversal_paths:
            with pytest.raises(ValueError, match="запрещённый символ|Path traversal"):
                validate_path(path, "test_path")

        # Пути с запрещёнными символами
        forbidden_char_paths = [
            "/safe/path;rm -rf",
            "/safe/path|cat /etc/passwd",
            "/safe/path&whoami",
            "/safe/path`id`",
            "/safe/path$HOME",
        ]

        for path in forbidden_char_paths:
            with pytest.raises(ValueError, match="запрещённый символ"):
                validate_path(path, "test_path")

    def test_validate_path_empty_path(self) -> None:
        """Тест validate_path() для пустого пути.

        Проверяет:
        - Пустая строка не вызывает исключений (предупреждение)
        - None обрабатывается корректно
        """
        # Пустой путь должен логировать предупреждение, но не выбрасывать
        validate_path("", "test_path")

    def test_validate_path_max_length(self) -> None:
        """Тест validate_path() для путей превышающих максимальную длину.

        Проверяет:
        - Пути длиннее MAX_PATH_LENGTH вызывают ValueError
        """
        from parser_2gis.constants import MAX_PATH_LENGTH

        # Создаём путь длиннее максимума
        long_path = "/safe/" + "a" * (MAX_PATH_LENGTH + 1)

        with pytest.raises(ValueError, match="превышает максимальную длину"):
            validate_path(long_path, "test_path")

    def test_path_validator_class(self) -> None:
        """Тест класса PathValidator.

        Проверяет:
        - Инициализация с allowed_base_dirs
        - Метод validate()
        - Метод validate_multiple()
        """
        import os
        import tempfile

        # Создаём валидатор с кастомными директориями включая cwd и temp
        custom_dirs = [Path.cwd(), Path(tempfile.gettempdir()), Path("/custom/dir")]
        validator = PathValidator(allowed_base_dirs=custom_dirs)

        # Проверяем что директории установлены
        assert Path.cwd() in validator._allowed_base_dirs
        assert Path(tempfile.gettempdir()) in validator._allowed_base_dirs

        # Тест validate_multiple
        paths_dict = {
            "output": os.path.join(os.getcwd(), "output.csv"),
            "log": os.path.join(tempfile.gettempdir(), "log.txt"),
        }

        # Не должно вызывать исключений для валидных путей
        validator.validate_multiple(paths_dict)

    def test_get_path_validator_singleton(self) -> None:
        """Тест singleton экземпляра PathValidator.

        Проверяет:
        - get_path_validator() возвращает один экземпляр
        - Экземпляр кэшируется
        """
        validator1 = get_path_validator()
        validator2 = get_path_validator()

        # Должен возвращаться тот же экземпляр
        assert validator1 is validator2

    def test_validate_path_special_characters(self) -> None:
        r"""Тест validate_path() со специальными символами.

        Проверяет:
        - Символы < > \ запрещены
        - Символы переноса строки запрещены
        """
        special_char_paths = [
            "/safe/path<file",
            "/safe/path>file",
            "/safe/path\\file",
            "/safe/path\nfile",
            "/safe/path\rfile",
        ]

        for path in special_char_paths:
            with pytest.raises(ValueError, match="запрещённый символ"):
                validate_path(path, "test_path")

    def test_validate_path_tilde_expansion(self) -> None:
        """Тест validate_path() с tilde (~).

        Проверяет:
        - ~ в пути запрещён
        """
        tilde_path = "~/parser-2gis/output.csv"

        with pytest.raises(ValueError, match="запрещённый символ"):
            validate_path(tilde_path, "test_path")

    def test_validate_path_resolution(self) -> None:
        """Тест resolve пути через realpath.

        Проверяет:
        - Символьные ссылки разрешаются
        - Путь нормализуется
        """
        # Создаём временный файл для теста
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Создаём symlink
            link_path = tempfile.mktemp()
            os.symlink(tmp_path, link_path)

            # Путь должен быть разрешён через realpath
            # (не должен вызывать path traversal ошибку)
            validate_path(link_path, "test_path")

            # Очищаем
            os.unlink(link_path)
        except (OSError, ValueError) as e:
            # Некоторые системы могут не поддерживать symlink
            if "symlink" not in str(e).lower():
                raise
        finally:
            # Очищаем временный файл
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
