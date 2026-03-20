"""
Тесты для проверки разбиения сложных функций (function decomposition).

Проверяет что сложные функции были разбиты на более мелкие:
- validate_cached_data: разбита на _validate_numeric_data, _validate_string_data,
                        _validate_dict_data, _validate_list_data
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

from parser_2gis.cache import (
    MAX_DATA_DEPTH,
    MAX_STRING_LENGTH,
    _validate_cached_data,
    _validate_dict_data,
    _validate_list_data,
    _validate_numeric_data,
    _validate_string_data,
)
from parser_2gis.chrome.browser import (
    ChromeBrowser,
    _check_profile_age_and_delete,
    _check_profile_age_by_dir,
    _process_orphaned_profile,
    _safe_remove_profile,
    cleanup_orphaned_profiles,
)


class TestValidateCachedDataDecomposition:
    """Тесты для разбиения функции validate_cached_data."""

    def test_validate_cached_data_decomposed_numeric_valid(self):
        """
        Тест 1.1: Проверка валидации числовых данных.

        Проверяет что функция _validate_numeric_data
        корректно валидирует числовые данные.
        """
        # Проверяем валидные числа
        assert _validate_numeric_data(42) is True
        assert _validate_numeric_data(3.14) is True
        assert _validate_numeric_data(0) is True
        assert _validate_numeric_data(-100) is True
        assert _validate_numeric_data(1e10) is True

    def test_validate_cached_data_decomposed_numeric_invalid(self):
        """
        Тест 1.2: Проверка валидации некорректных числовых данных.

        Проверяет что функция _validate_numeric_data
        отклоняет NaN и Infinity значения.
        """

        # Проверяем некорректные числа
        assert _validate_numeric_data(float("nan")) is False
        assert _validate_numeric_data(float("inf")) is False
        assert _validate_numeric_data(float("-inf")) is False

    def test_validate_cached_data_decomposed_string_valid(self):
        """
        Тест 1.3: Проверка валидации строковых данных.

        Проверяет что функция _validate_string_data
        корректно валидирует строки нормальной длины.
        """
        # Проверяем валидные строки
        assert _validate_string_data("Hello, World!") is True
        assert _validate_string_data("") is True
        assert _validate_string_data("a" * 100) is True
        assert _validate_string_data("a" * MAX_STRING_LENGTH) is True

    def test_validate_cached_data_decomposed_string_invalid(self):
        """
        Тест 1.4: Проверка валидации некорректных строковых данных.

        Проверяет что функция _validate_string_data
        отклоняет строки превышающие максимальную длину.
        """
        # Проверяем некорректные строки (превышение длины)
        too_long_string = "a" * (MAX_STRING_LENGTH + 1)
        assert _validate_string_data(too_long_string) is False

    def test_validate_cached_data_decomposed_dict_valid(self):
        """
        Тест 1.5: Проверка валидации словарей.

        Проверяет что функция _validate_dict_data
        корректно валидирует словари с безопасными данными.
        """
        # Проверяем валидные словари
        valid_dict = {
            "name": "Test",
            "value": 42,
            "nested": {"key": "value"},
            "list": [1, 2, 3],
        }
        assert _validate_dict_data(valid_dict, depth=0) is True

    def test_validate_cached_data_decomposed_dict_invalid_proto(self):
        """
        Тест 1.6: Проверка валидации словарей с опасными ключами.

        Проверяет что функция _validate_dict_data
        отклоняет словари с __proto__ ключами.
        """
        # Проверяем некорректные словари (prototype pollution)
        dangerous_dict = {
            "__proto__": {"isAdmin": True},
            "name": "Test",
        }
        assert _validate_dict_data(dangerous_dict, depth=0) is False

        # Проверяем другие опасные ключи
        dangerous_dict2 = {
            "constructor": {"prototype": {"isAdmin": True}},
        }
        assert _validate_dict_data(dangerous_dict2, depth=0) is False

    def test_validate_cached_data_decomposed_dict_depth_limit(self):
        """
        Тест 1.7: Проверка валидации глубины вложенности словарей.

        Проверяет что функция _validate_dict_data
        отклоняет словари с чрезмерной вложенностью.
        """
        # Создаем глубоко вложенный словарь
        deep_dict = {"level": 0}
        current = deep_dict
        for i in range(MAX_DATA_DEPTH + 5):
            current["nested"] = {"level": i + 1}
            current = current["nested"]

        # Проверяем что глубина превышена
        assert _validate_cached_data(deep_dict) is False

    def test_validate_cached_data_decomposed_list_valid(self):
        """
        Тест 1.8: Проверка валидации списков.

        Проверяет что функция _validate_list_data
        корректно валидирует списки с безопасными данными.
        """
        # Проверяем валидные списки
        valid_list = [1, "two", 3.0, None, True, {"key": "value"}]
        assert _validate_list_data(valid_list, depth=0) is True

    def test_validate_cached_data_decomposed_list_invalid(self):
        """
        Тест 1.9: Проверка валидации некорректных списков.

        Проверяет что функция _validate_list_data
        отклоняет списки с некорректными элементами.
        """
        # Проверяем некорректные списки (с опасными вложениями)
        invalid_list = [
            1,
            {"__proto__": {"isAdmin": True}},
        ]
        assert _validate_list_data(invalid_list, depth=0) is False

    def test_validate_cached_data_decomposed_comprehensive(self):
        """
        Тест 1.10: Комплексная проверка валидации данных кэша.

        Проверяет что функция _validate_cached_data
        корректно использует все подфункции валидации.
        """
        # Проверяем базовые типы
        assert _validate_cached_data(None) is True
        assert _validate_cached_data(True) is True
        assert _validate_cached_data(False) is True
        assert _validate_cached_data(42) is True
        assert _validate_cached_data(3.14) is True
        assert _validate_cached_data("string") is True

        # Проверяем сложные типы
        assert _validate_cached_data({"key": "value"}) is True
        assert _validate_cached_data([1, 2, 3]) is True

        # Проверяем некорректные типы
        class CustomClass:
            pass

        assert _validate_cached_data(CustomClass()) is False
        assert _validate_cached_data(lambda x: x) is False


class TestBrowserInitDecomposition:
    """Тесты для разбиения функции инициализации браузера."""

    def test_browser_init_decomposed_methods_exist(self):
        """
        Тест 2.1: Проверка что методы декомпозиции существуют.

        Проверяет что все методы декомпозиции
        существуют в классе ChromeBrowser.
        """
        # Проверяем что методы существуют
        assert hasattr(ChromeBrowser, "_get_binary_path")
        assert hasattr(ChromeBrowser, "_create_profile_dir")
        assert hasattr(ChromeBrowser, "_build_chrome_cmd")
        assert hasattr(ChromeBrowser, "_launch_chrome_process")

        # Проверяем что методы callable
        assert callable(getattr(ChromeBrowser, "_get_binary_path"))
        assert callable(getattr(ChromeBrowser, "_create_profile_dir"))
        assert callable(getattr(ChromeBrowser, "_build_chrome_cmd"))
        assert callable(getattr(ChromeBrowser, "_launch_chrome_process"))

    def test_browser_init_decomposed_build_chrome_cmd(self):
        """
        Тест 2.2: Проверка функции формирования команды Chrome.

        Проверяет что функция _build_chrome_cmd
        корректно формирует команду запуска.
        """
        # Создаем mock ChromeBrowser
        browser = object.__new__(ChromeBrowser)

        # Mock параметров
        mock_options = MagicMock()
        mock_options.memory_limit = 2048
        mock_options.start_maximized = False
        mock_options.headless = True
        mock_options.disable_images = True
        mock_options.silent_browser = False

        # Формируем команду
        cmd = browser._build_chrome_cmd(
            binary_path="/usr/bin/google-chrome",
            profile_path="/tmp/profile",
            remote_port=9222,
            chrome_options=mock_options,
        )

        # Проверяем что команда содержит ожидаемые аргументы
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
        существуют в классе ChromeBrowser.
        """
        # Проверяем что методы существуют
        assert hasattr(ChromeBrowser, "_terminate_process_graceful")
        assert hasattr(ChromeBrowser, "_terminate_process_forceful")
        assert hasattr(ChromeBrowser, "_cleanup_profile")

        # Проверяем что методы callable
        assert callable(getattr(ChromeBrowser, "_terminate_process_graceful"))
        assert callable(getattr(ChromeBrowser, "_terminate_process_forceful"))
        assert callable(getattr(ChromeBrowser, "_cleanup_profile"))

    def test_browser_close_decomposed_cleanup_profile(self):
        """
        Тест 3.2: Проверка функции очистки профиля.

        Проверяет что функция _cleanup_profile
        корректно удаляет временный профиль.
        """
        # Создаем mock ChromeBrowser
        browser = object.__new__(ChromeBrowser)

        # Mock TemporaryDirectory
        mock_tempdir = MagicMock()
        browser._profile_tempdir = mock_tempdir
        browser._profile_path = "/tmp/profile"

        # Вызываем функцию
        browser._cleanup_profile()

        # Проверяем что cleanup был вызван
        mock_tempdir.cleanup.assert_called_once()


class TestCleanupOrphanedProfilesDecomposition:
    """Тесты для разбиения функции очистки осиротевших профилей."""

    def test_cleanup_orphaned_profiles_decomposed_functions_exist(self):
        """
        Тест 4.1: Проверка что функции декомпозиции существуют.

        Проверяет что все функции декомпозиции
        существуют в модуле browser.
        """
        # Проверяем что функции существуют
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
        # Создаем тестовую директорию профиля
        profile_dir = tmp_path / "chrome_profile_test"
        profile_dir.mkdir()

        # Вызываем функцию
        current_time = time.time()
        max_age_seconds = 24 * 3600

        result = _process_orphaned_profile(
            item=profile_dir,
            current_time=current_time,
            max_age_seconds=max_age_seconds,
        )

        # Проверяем что профиль не был удалён (слишком молодой)
        assert result is False
        assert profile_dir.exists()

    def test_cleanup_orphaned_profiles_decomposed_full_cleanup(self, tmp_path):
        """
        Тест 4.3: Комплексная проверка функции cleanup_orphaned_profiles.

        Проверяет что функция cleanup_orphaned_profiles
        корректно использует все подфункции.
        """
        # Создаем несколько тестовых профилей
        profile1 = tmp_path / "chrome_profile_old1"
        profile2 = tmp_path / "chrome_profile_old2"
        profile3 = tmp_path / "chrome_profile_new"

        profile1.mkdir()
        profile2.mkdir()
        profile3.mkdir()

        # Устанавливаем старое время модификации для первых двух
        old_time = time.time() - (25 * 3600)  # 25 часов назад
        os.utime(profile1, (old_time, old_time))
        os.utime(profile2, (old_time, old_time))
        # Третий профиль оставляем новым

        # Mock _is_profile_in_use для возврата False
        with patch("parser_2gis.chrome.browser._is_profile_in_use", return_value=False):
            # Вызываем функцию
            deleted_count = cleanup_orphaned_profiles(
                profiles_dir=tmp_path,
                max_age_hours=24,
            )

            # Проверяем что старые профили были удалены
            assert deleted_count >= 2
            assert not profile1.exists()
            assert not profile2.exists()
            # Новый профиль должен остаться
            assert profile3.exists()


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
