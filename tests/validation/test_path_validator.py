"""Тесты для PathValidator."""

from pathlib import Path

import pytest

from parser_2gis.validation.path_validator import PathValidator, get_path_validator, validate_path


class TestPathValidatorConstruction:
    """Тесты конструирования PathValidator."""

    def test_default_construction(self):
        """PathValidator создаётся с дефолтными настройками."""
        validator = PathValidator()
        assert validator is not None
        assert len(validator._allowed_base_dirs) > 0

    def test_custom_base_dirs(self):
        """PathValidator с кастомными директориями."""
        custom_dirs = [Path("/custom/path")]
        validator = PathValidator(allowed_base_dirs=custom_dirs)
        assert validator._allowed_base_dirs == custom_dirs


class TestPathValidatorValidate:
    """Тесты метода validate."""

    def test_safe_path_no_error(self, tmp_path):
        """Безопасный путь не выбрасывает ошибок."""
        validator = PathValidator(allowed_base_dirs=[tmp_path])
        safe_path = str(tmp_path / "subdir" / "file.txt")
        validator.validate(safe_path)  # Не должно выбросить исключений

    @pytest.mark.parametrize(
        "forbidden_char", ["..", "~", "$", "`", "|", ";", "&", "\\", "\n", "\r"]
    )
    def test_forbidden_characters_raise_error(self, forbidden_char, tmp_path):
        """Запрещённые символы вызывают ValueError."""
        validator = PathValidator(allowed_base_dirs=[tmp_path])
        bad_path = str(tmp_path / f"file{forbidden_char}name.txt")
        with pytest.raises(ValueError, match="запрещённый символ"):
            validator.validate(bad_path)

    def test_too_long_path_raises_error(self):
        """Слишком длинный путь вызывает ValueError."""
        validator = PathValidator()
        long_path = "a" * (validator._MAX_PATH_LENGTH + 100)
        with pytest.raises(ValueError, match="превышает максимальную длину"):
            validator.validate(long_path)

    def test_empty_path_returns_early(self, tmp_path):
        """Пустой путь возвращается рано без ошибок."""
        validator = PathValidator(allowed_base_dirs=[tmp_path])
        validator.validate("")  # Не должно выбросить исключений


class TestPathValidatorValidateMultiple:
    """Тесты validate_multiple."""

    def test_multiple_safe_paths_no_error(self, tmp_path):
        """Несколько безопасных путей не вызывают ошибок."""
        validator = PathValidator(allowed_base_dirs=[tmp_path])
        paths = {"path1": str(tmp_path / "file1.txt"), "path2": str(tmp_path / "file2.txt")}
        validator.validate_multiple(paths)  # Не должно выбросить исключений


class TestPathValidatorGlobalFunctions:
    """Тесты глобальных функций."""

    def test_get_path_validator_returns_singleton(self):
        """get_path_validator возвращает PathValidator."""
        validator = get_path_validator()
        assert isinstance(validator, PathValidator)

    def test_get_path_validator_returns_same_instance(self):
        """get_path_validator возвращает один и тот же экземпляр."""
        v1 = get_path_validator()
        v2 = get_path_validator()
        assert v1 is v2

    def test_validate_path_wrapper(self, tmp_path):
        """validate_path обёртка работает корректно."""
        # Используем текущую рабочую директорию как разрешённую
        safe_path = str(tmp_path / "safe_file.txt")
        # Должно работать без ошибок для путей внутри cwd
        validate_path(safe_path, "test_path")
