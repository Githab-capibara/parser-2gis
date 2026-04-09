"""
Тесты для проверки разбиения сложных функций (function decomposition).

Проверяет что сложные функции были разбиты на более мелкие:
- validate_cached_data: разбита на _check_numeric, _check_string,
                        _check_dict, _check_list (методы класса CacheDataValidator)
- browser_init: разбита на _get_binary_path, _create_profile_dir, _build_chrome_cmd,
                _launch_chrome_process
- browser_close: разбита на _terminate_process_graceful, _terminate_process_forceful,
                 _cleanup_profile
- cleanup_orphaned_profiles: разбита на _process_orphaned_profile,
                             _check_profile_age_and_delete, _check_profile_age_by_dir,
                             _safe_remove_profile
"""

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.cache.validator import CacheDataValidator
from parser_2gis.chrome.browser import (
    _check_profile_age_and_delete,
    _check_profile_age_by_dir,
    _process_orphaned_profile,
    _safe_remove_profile,
    cleanup_orphaned_profiles,
)
from parser_2gis.constants import MAX_DATA_DEPTH, MAX_STRING_LENGTH


class TestValidateCachedDataDecomposition:
    """Тесты для разбиения функции validate_cached_data."""

    @pytest.fixture(autouse=True)
    def setup_validator(self):
        """Создаёт экземпляр CacheDataValidator для всех тестов."""
        self.validator = CacheDataValidator()

    def test_validate_cached_data_decomposed_numeric_valid(self):
        """
        Тест 1.1: Проверка валидации числовых данных.

        Проверяет что метод _check_numeric
        корректно валидирует числовые данные.
        """
        assert self.validator._check_numeric(42) is True
        assert self.validator._check_numeric(3.14) is True
        assert self.validator._check_numeric(0) is True
        assert self.validator._check_numeric(-100) is True
        assert self.validator._check_numeric(1e10) is True

    def test_validate_cached_data_decomposed_numeric_invalid(self):
        """
        Тест 1.2: Проверка валидации некорректных числовых данных.

        Проверяет что метод _check_numeric
        отклоняет NaN и Infinity значения.
        """
        assert self.validator._check_numeric(float("nan")) is False
        assert self.validator._check_numeric(float("inf")) is False
        assert self.validator._check_numeric(float("-inf")) is False

    def test_validate_cached_data_decomposed_string_valid(self):
        """
        Тест 1.3: Проверка валидации строковых данных.

        Проверяет что метод _check_string
        корректно валидирует строки нормальной длины.
        """
        assert self.validator._check_string("Hello, World!") is True
        assert self.validator._check_string("") is True
        assert self.validator._check_string("a" * 100) is True
        assert self.validator._check_string("a" * MAX_STRING_LENGTH) is True

    def test_validate_cached_data_decomposed_string_invalid(self):
        """
        Тест 1.4: Проверка валидации некорректных строковых данных.

        Проверяет что метод _check_string
        отклоняет строки превышающие максимальную длину.
        """
        too_long_string = "a" * (MAX_STRING_LENGTH + 1)
        assert self.validator._check_string(too_long_string) is False

    def test_validate_cached_data_decomposed_dict_valid(self):
        """
        Тест 1.5: Проверка валидации словарей.

        Проверяет что метод _check_dict
        корректно валидирует словари с безопасными данными.
        """
        valid_dict = {"name": "Test", "value": 42, "nested": {"key": "value"}, "list": [1, 2, 3]}
        assert self.validator._check_dict(valid_dict, depth=0) is True

    def test_validate_cached_data_decomposed_dict_invalid_proto(self):
        """
        Тест 1.6: Проверка валидации словарей с опасными ключами.

        Проверяет что метод _check_dict
        отклоняет словари с __proto__ ключами.
        """
        dangerous_dict = {"__proto__": {"isAdmin": True}, "name": "Test"}
        assert self.validator._check_dict(dangerous_dict, depth=0) is False

        dangerous_dict2 = {"constructor": {"prototype": {"isAdmin": True}}}
        assert self.validator._check_dict(dangerous_dict2, depth=0) is False

    def test_validate_cached_data_decomposed_dict_depth_limit(self):
        """
        Тест 1.7: Проверка валидации глубины вложенности словарей.

        Проверяет что метод validate
        отклоняет словари с чрезмерной вложенностью.
        """
        deep_dict = {"level": 0}
        current = deep_dict
        for i in range(MAX_DATA_DEPTH + 5):
            current["nested"] = {"level": i + 1}
            current = current["nested"]

        assert self.validator.validate(deep_dict) is False

    def test_validate_cached_data_decomposed_list_valid(self):
        """
        Тест 1.8: Проверка валидации списков.

        Проверяет что метод _check_list
        корректно валидирует списки с безопасными данными.
        """
        valid_list = [1, "two", 3.0, None, True, {"key": "value"}]
        assert self.validator._check_list(valid_list, depth=0) is True

    def test_validate_cached_data_decomposed_list_invalid(self):
        """
        Тест 1.9: Проверка валидации некорректных списков.

        Проверяет что метод _check_list
        отклоняет списки с некорректными элементами.
        """
        invalid_list = [1, {"__proto__": {"isAdmin": True}}]
        assert self.validator._check_list(invalid_list, depth=0) is False

    def test_validate_cached_data_decomposed_comprehensive(self):
        """
        Тест 1.10: Комплексная проверка валидации данных кэша.

        Проверяет что метод validate
        корректно использует все подметоды валидации.
        """
        assert self.validator.validate(None) is True
        assert self.validator.validate(True) is True
        assert self.validator.validate(False) is True
        assert self.validator.validate(42) is True
        assert self.validator.validate(3.14) is True
        assert self.validator.validate("string") is True

        assert self.validator.validate({"key": "value"}) is True
        assert self.validator.validate([1, 2, 3]) is True

        class CustomClass:
            pass

        assert self.validator.validate(CustomClass()) is False
        assert self.validator.validate(lambda x: x) is False


class TestBrowserInitDecomposition:
    """Тесты для разбиения функции инициализации браузера."""

    def test_browser_init_decomposed_methods_exist(self):
        """
        Тест 2.1: Проверка что методы декомпозиции существуют.

        Проверяет что все методы декомпозиции
        существуют в классе BrowserLifecycleManager.
        """
        from parser_2gis.chrome.browser import (
            BrowserLifecycleManager,
            BrowserPathResolver,
            ProcessManager,
            ProfileManager,
        )

        assert hasattr(BrowserLifecycleManager, "_build_chrome_cmd")
        assert hasattr(BrowserPathResolver, "resolve_path")
        assert hasattr(ProfileManager, "create_profile")
        assert hasattr(ProcessManager, "launch_process")

        assert callable(BrowserLifecycleManager._build_chrome_cmd)
        assert callable(BrowserPathResolver.resolve_path)
        assert callable(ProfileManager.create_profile)
        assert callable(ProcessManager.launch_process)

    def test_browser_init_decomposed_build_chrome_cmd(self):
        """
        Тест 2.2: Проверка функции формирования команды Chrome.

        Проверяет что функция _build_chrome_cmd
        корректно формирует команду запуска.
        """
        from parser_2gis.chrome.browser import BrowserLifecycleManager

        manager = object.__new__(BrowserLifecycleManager)

        mock_options = MagicMock()
        mock_options.memory_limit = 2048
        mock_options.start_maximized = False
        mock_options.headless = True
        mock_options.disable_images = True
        mock_options.silent_browser = False

        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/google-chrome",
            profile_path="/tmp/profile",
            remote_port=9222,
            chrome_options=mock_options,
        )

        assert isinstance(cmd, list)
        assert len(cmd) > 0
        assert "--headless" in cmd
        assert "--disable-gpu" in cmd
        assert "--remote-debugging-port=9222" in cmd


class TestBrowserCloseDecomposition:
    """Тесты для разбиения функции закрытия браузера."""

    def test_browser_close_decomposed_methods_exist(self):
        """
        Тест 3.1: Проверка что методы декомпозиции существуют.

        Проверяет что все методы декомпозиции
        существуют в классе ProcessManager.
        """
        from parser_2gis.chrome.browser import ProcessManager

        assert hasattr(ProcessManager, "terminate")
        assert hasattr(ProcessManager, "kill")

        assert callable(ProcessManager.terminate)
        assert callable(ProcessManager.kill)

    def test_browser_close_decomposed_cleanup_profile(self):
        """
        Тест 3.2: Проверка функции очистки профиля.

        Проверяет что ProfileManager.cleanup_profile
        корректно удаляет временный профиль.
        """
        from parser_2gis.chrome.browser import ProfileManager

        profile_manager = ProfileManager.__new__(ProfileManager)

        mock_tempdir = MagicMock()
        profile_manager._profile_tempdir = mock_tempdir
        profile_manager._profile_path = "/tmp/profile"

        profile_manager.cleanup_profile()

        mock_tempdir.cleanup.assert_called_once()


class TestCleanupOrphanedProfilesDecomposition:
    """Тесты для разбиения функции очистки осиротевших профилей."""

    def test_cleanup_orphaned_profiles_decomposed_functions_exist(self):
        """
        Тест 4.1: Проверка что функции декомпозиции существуют.

        Проверяет что все функции декомпозиции
        существуют в модуле browser.
        """
        assert callable(_check_profile_age_and_delete)
        assert callable(_check_profile_age_by_dir)
        assert callable(_process_orphaned_profile)
        assert callable(_safe_remove_profile)
        assert callable(cleanup_orphaned_profiles)

    def test_cleanup_orphaned_profiles_decomposed_process_profile(self, tmp_path):
        """
        Тест 4.2: Проверка функции обработки одного профиля.

        Проверяет что функция _process_orphaned_profile
        корректно обрабатывает профиль.
        """
        profile_dir = tmp_path / "chrome_profile_test"
        profile_dir.mkdir()

        current_time = time.time()
        max_age_seconds = 24 * 3600

        result = _process_orphaned_profile(
            item=profile_dir, current_time=current_time, max_age_seconds=max_age_seconds
        )

        assert result is False
        assert profile_dir.exists()

    def test_cleanup_orphaned_profiles_decomposed_full_cleanup(self, tmp_path):
        """
        Тест 4.3: Комплексная проверка функции cleanup_orphaned_profiles.

        Проверяет что функция cleanup_orphaned_profiles
        корректно использует все подфункции.
        """
        profile1 = tmp_path / "chrome_profile_old1"
        profile2 = tmp_path / "chrome_profile_old2"
        profile3 = tmp_path / "chrome_profile_new"

        profile1.mkdir()
        profile2.mkdir()
        profile3.mkdir()

        old_time = time.time() - (25 * 3600)
        os.utime(profile1, (old_time, old_time))
        os.utime(profile2, (old_time, old_time))

        with patch("parser_2gis.chrome.browser._is_profile_in_use", return_value=False):
            deleted_count = cleanup_orphaned_profiles(profiles_dir=tmp_path, max_age_hours=24)

            assert deleted_count >= 2
            assert not profile1.exists()
            assert not profile2.exists()
            assert profile3.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
