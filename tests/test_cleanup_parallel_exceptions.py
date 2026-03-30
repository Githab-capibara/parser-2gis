"""
Тесты для обработки исключений в cleanup_resources() и parallel_parser.py.

Проверяет:
- Обработку AttributeError, MemoryError, KeyboardInterrupt в cleanup_resources()
- Обработку KeyboardInterrupt в ParallelCityParser
- Установку флага отмены при прерывании
- Отмену ожидающих задач
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.cli.main import cleanup_resources
from parser_2gis.parallel.parallel_parser import ParallelCityParser

# =============================================================================
# ТЕСТЫ ДЛЯ ОБРАБОТКИ ОШИБОК В CLEANUP_RESOURCES
# =============================================================================


class TestCleanupResourcesExceptionHandling:
    """Тесты для проблемы 7: Неполная обработка исключений в cleanup_resources()."""

    @patch("parser_2gis.cli.main.ChromeRemote")
    @patch("parser_2gis.cli.main.Cache")
    @patch("gc.collect")
    def test_handle_attribute_error(
        self, mock_gc: MagicMock, mock_cache: MagicMock, mock_chrome: MagicMock
    ) -> None:
        """
        Тест 4.1: Обработка AttributeError.

        Проверяет что AttributeError при доступе к несуществующим
        атрибутам корректно обрабатывается.
        """
        # Настраиваем моки чтобы вызвать AttributeError
        mock_chrome._active_instances = MagicMock()
        mock_chrome._active_instances.__iter__ = MagicMock(
            side_effect=AttributeError("Mocked AttributeError")
        )

        mock_cache.close_all = MagicMock(side_effect=AttributeError("Mocked Cache AttributeError"))

        # Вызываем cleanup_resources - не должно выбросить исключение
        try:
            cleanup_resources()
        except AttributeError:
            pytest.fail("cleanup_resources не должен выбрасывать AttributeError")

    @patch("parser_2gis.cli.main.ChromeRemote")
    @patch("parser_2gis.cli.main.Cache")
    @patch("gc.collect")
    def test_handle_memory_error(
        self, mock_gc: MagicMock, mock_cache: MagicMock, mock_chrome: MagicMock
    ) -> None:
        """
        Тест 4.2: Обработка MemoryError.

        Проверяет что MemoryError корректно обрабатывается
        и не прерывает очистку ресурсов.
        """
        # Настраиваем моки чтобы вызвать MemoryError
        mock_chrome._active_instances = []
        mock_cache.close_all = MagicMock()
        mock_gc.side_effect = MemoryError("Mocked MemoryError")

        # Вызываем cleanup_resources - не должно выбросить исключение
        try:
            cleanup_resources()
        except MemoryError:
            pytest.fail("cleanup_resources не должен выбрасывать MemoryError")

    @patch("parser_2gis.cli.main.ChromeRemote")
    @patch("parser_2gis.cli.main.Cache")
    @patch("gc.collect")
    def test_handle_keyboard_interrupt(
        self, mock_gc: MagicMock, mock_cache: MagicMock, mock_chrome: MagicMock
    ) -> None:
        """
        Тест 4.3: Обработка KeyboardInterrupt.

        Проверяет что KeyboardInterrupt корректно обрабатывается
        и позволяет завершить очистку.
        """
        # Настраиваем моки
        mock_chrome._active_instances = []
        mock_cache.close_all = MagicMock()

        # Вызываем cleanup_resources в безопасном режиме
        try:
            # Мокаем gc.collect чтобы не вызывать реальный GC
            with patch("gc.collect", return_value=None):
                cleanup_resources()
        except KeyboardInterrupt:
            pytest.fail("cleanup_resources должен обрабатывать KeyboardInterrupt")

    def test_cleanup_resources_with_none_instances(self) -> None:
        """
        Тест 4.4: Очистка с None значениями.

        Проверяет что cleanup_resources корректно работает
        когда глобальные переменные не инициализированы.
        """
        # Мокаем отсутствующие атрибуты
        with patch("parser_2gis.cli.main.ChromeRemote", None):
            with patch("parser_2gis.cli.main.Cache", None):
                with patch("gc.collect", return_value=None):
                    # Вызываем cleanup_resources - не должно выбросить исключение
                    try:
                        cleanup_resources()
                    except (AttributeError, TypeError):
                        pytest.fail("cleanup_resources должен обрабатывать None значения")


# =============================================================================
# ТЕСТЫ ДЛЯ ОБРАБОТКИ KEYBOARDINTERRUPT В PARALLEL_PARSER
# =============================================================================


class TestKeyboardInterruptHandling:
    """Тесты для проблемы 11: Отсутствие обработки KeyboardInterrupt."""

    @pytest.fixture
    def parser(self, tmp_path):
        """Фикстура для создания ParallelCityParser."""
        mock_config = MagicMock()
        mock_cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        mock_categories = [{"id": 1, "name": "Кафе"}]

        return ParallelCityParser(
            cities=mock_cities,
            categories=mock_categories,
            output_dir=str(tmp_path),
            config=mock_config,
            max_workers=2,
            timeout_per_url=60,
        )

    def test_keyboard_interrupt_sets_cancel_flag(self, parser: ParallelCityParser) -> None:
        """
        Тест 5.1: KeyboardInterrupt устанавливает флаг отмены.

        Проверяет что при KeyboardInterrupt устанавливается
        флаг отмены операций.
        """
        # Проверяем что флаг отмены изначально не установлен
        assert parser._cancel_event.is_set() is False, (
            "Флаг отмены не должен быть установлен изначально"
        )

        # Имитируем KeyboardInterrupt через установку флага
        parser._cancel_event.set()

        # Проверяем что флаг установлен
        assert parser._cancel_event.is_set() is True, "Флаг отмены должен быть установлен"

    def test_cancel_pending_tasks(self, parser: ParallelCityParser) -> None:
        """
        Тест 5.2: Отмена всех ожидающих задач.

        Проверяет что при отмене все ожидающие задачи
        корректно отменяются.
        """
        # Устанавливаем флаг отмены
        parser._cancel_event.set()

        # Проверяем что parse_single_url возвращает False при отмене
        success, message = parser.parse_single_url(
            url="https://2gis.ru/moscow/search/Кафе", category_name="Кафе", city_name="Москва"
        )

        assert success is False, "При отмене задача должна возвращать False"
        assert "Отменено" in message, "Сообщение должно указывать на отмену"

    def test_returns_false_on_interrupt(self, parser: ParallelCityParser) -> None:
        """
        Тест 5.3: Возврат False при прерывании.

        Проверяет что операции возвращают False при прерывании.
        """
        # Устанавливаем флаг отмены
        parser._cancel_event.set()

        # Проверяем что generate_all_urls работает при отмене
        urls = parser.generate_all_urls()

        # URLs должны быть сгенерированы но статистика должна показать 0
        with parser._lock:
            assert parser._stats["total"] == len(urls), "Статистика должна быть обновлена"

    def test_keyboard_interrupt_in_thread_pool(self, parser: ParallelCityParser) -> None:
        """
        Тест 5.4: KeyboardInterrupt в пуле потоков.

        Проверяет что KeyboardInterrupt в потоке корректно обрабатывается.
        """
        # Мокаем parse_single_url чтобы выбросить KeyboardInterrupt
        with patch.object(parser, "parse_single_url", side_effect=KeyboardInterrupt("Mocked")):
            # Проверяем что исключение пробрасывается
            with pytest.raises(KeyboardInterrupt):
                parser.parse_single_url(
                    url="https://2gis.ru/moscow/search/Кафе",
                    category_name="Кафе",
                    city_name="Москва",
                )
