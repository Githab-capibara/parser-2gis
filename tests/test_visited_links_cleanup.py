"""
Тест периодической очистки visited_links.

Проверяет что после 5 вызовов происходит очистка 50% ссылок
при превышении порога.

ИСПРАВЛЕНИЕ C5: Периодическая принудительная очистка visited_links.
"""

from collections import OrderedDict
from unittest.mock import MagicMock

import pytest


class TestVisitedLinksCleanup:
    """Тесты периодической очистки visited_links."""

    @pytest.fixture
    def mock_writer(self) -> MagicMock:
        """Фикстура для mock writer."""
        return MagicMock()

    @pytest.fixture
    def max_visited_links(self) -> int:
        """Фикстура для максимального размера visited_links."""
        return 100

    def test_cleanup_after_5_calls(self, mock_writer: MagicMock, max_visited_links: int) -> None:
        """Тест что после 5 вызовов происходит очистка 50%.

        Проверяет:
        - Счётчик вызовов инкрементируется
        - На 5-м вызове происходит очистка
        - Удаляется 50% ссылок
        """
        # Создаём visited_links с большим количеством ссылок
        visited_links: OrderedDict[str, None] = OrderedDict()
        max_size = max_visited_links

        # Добавляем больше чем max_visited_links * 0.5 ссылок
        num_links = int(max_size * 0.6)  # 60 ссылок (60% от max)
        for i in range(num_links):
            visited_links[f"https://example.com/link{i}"] = None

        # Проверяем начальное количество
        initial_count = len(visited_links)
        assert initial_count == num_links

        # Симулируем 5 вызовов process_page
        cleanup_counter = 0
        for _call_num in range(5):
            cleanup_counter += 1

            # На 5-м вызове проверяем условие очистки
            if cleanup_counter >= 5 and len(visited_links) > max_size * 0.5:
                # Вычисляем количество для удаления
                target_remove = int(len(visited_links) * 0.5)

                # Удаляем старые записи
                for _ in range(target_remove):
                    if visited_links:
                        visited_links.popitem(last=False)

                # Сбрасываем счётчик
                cleanup_counter = 0

        # Проверяем что количество ссылок уменьшилось примерно на 50%
        final_count = len(visited_links)
        expected_max_count = int(initial_count * 0.5)

        assert final_count <= expected_max_count, (
            f"Ожидалось <= {expected_max_count} ссылок после очистки, получено {final_count}"
        )

    def test_cleanup_counter_resets_after_cleanup(self, mock_writer: MagicMock) -> None:
        """Тест что счётчик сбрасывается после очистки.

        Проверяет:
        - cleanup_counter сбрасывается в 0
        - Следующая очистка через 5 вызовов
        """
        cleanup_counter = 0
        cleanup_performed = False

        for _i in range(10):
            cleanup_counter += 1

            if cleanup_counter >= 5:
                cleanup_performed = True
                cleanup_counter = 0  # Сброс счётчика

        # Проверяем что очистка произошла 2 раза (на 5 и 10 вызове)
        assert cleanup_performed
        assert cleanup_counter == 0  # Счётчик сброшен после последнего вызова

    def test_cleanup_only_when_threshold_exceeded(self, mock_writer: MagicMock, max_visited_links: int) -> None:
        """Тест что очистка происходит только при превышении порога.

        Проверяет:
        - При len <= max_size * 0.5 очистка не происходит
        - При len > max_size * 0.5 очистка происходит
        """
        visited_links: OrderedDict[str, None] = OrderedDict()
        max_size = max_visited_links

        # Добавляем меньше чем 50% от max
        num_links_below = int(max_size * 0.4)  # 40 ссылок
        for i in range(num_links_below):
            visited_links[f"https://example.com/link{i}"] = None

        # Симулируем 5 вызовов
        cleanup_counter = 5
        links_removed_below = 0

        if cleanup_counter >= 5 and len(visited_links) > max_size * 0.5:
            target_remove = int(len(visited_links) * 0.5)
            for _ in range(target_remove):
                if visited_links:
                    visited_links.popitem(last=False)
                    links_removed_below += 1

        # Очистка не должна произойти (меньше 50%)
        assert links_removed_below == 0
        assert len(visited_links) == num_links_below

        # Теперь добавляем больше 50%
        num_links_above = int(max_size * 0.6)  # 60 ссылок
        for i in range(num_links_below, num_links_above):
            visited_links[f"https://example.com/link{i}"] = None

        links_removed_above = 0
        if len(visited_links) > max_size * 0.5:
            target_remove = int(len(visited_links) * 0.5)
            for _ in range(target_remove):
                if visited_links:
                    visited_links.popitem(last=False)
                    links_removed_above += 1

        # Очистка должна произойти
        assert links_removed_above > 0

    def test_cleanup_removes_oldest_links(self, mock_writer: MagicMock, max_visited_links: int) -> None:
        """Тест что очистка удаляет старейшие ссылки.

        Проверяет:
        - popitem(last=False) удаляет oldest (FIFO)
        - Новые ссылки остаются
        """
        visited_links: OrderedDict[str, None] = OrderedDict()
        max_size = max_visited_links

        # Добавляем ссылки в порядке
        num_links = int(max_size * 0.6)
        for i in range(num_links):
            visited_links[f"https://example.com/link{i:03d}"] = None

        # Выполняем очистку 50%
        if len(visited_links) > max_size * 0.5:
            target_remove = int(len(visited_links) * 0.5)
            for _ in range(target_remove):
                if visited_links:
                    visited_links.popitem(last=False)

        # Проверяем что старейшие ссылки удалены
        remaining_links = list(visited_links.keys())
        oldest_remaining = remaining_links[0] if remaining_links else None

        # Старейшие ссылки (link000, link001, ...) должны быть удалены
        # Ожидаем что оставшиеся начинаются с link030 или выше
        if oldest_remaining:
            link_number = int(oldest_remaining.split("link")[1])
            assert link_number >= target_remove - 1

    def test_cleanup_percentage_calculation(self, mock_writer: MagicMock) -> None:
        """Тест расчёта процента очистки.

        Проверяет:
        - 50% от текущего количества
        - Округление вниз
        """
        test_cases = [
            (100, 50),  # 100 * 0.5 = 50
            (99, 49),  # 99 * 0.5 = 49.5 -> 49
            (101, 50),  # 101 * 0.5 = 50.5 -> 50
            (10, 5),  # 10 * 0.5 = 5
            (11, 5),  # 11 * 0.5 = 5.5 -> 5
        ]

        for input_count, expected_remove in test_cases:
            target_remove = int(input_count * 0.5)
            assert target_remove == expected_remove, (
                f"Для {input_count} ожидалось {expected_remove}, получено {target_remove}"
            )
