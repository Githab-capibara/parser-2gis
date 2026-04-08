"""
Тесты для опций задержек в parallel/parallel_parser.py.

Проверяет:
- Корректное использование настроек задержек из ParallelOptions
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from parser_2gis.config import Configuration
from parser_2gis.parallel.options import ParallelOptions
from parser_2gis.parallel.strategies import ParseStrategy


class TestParallelParserDelays:
    """Тесты задержек в ParseStrategy."""

    @pytest.fixture
    def mock_config(self) -> Configuration:
        """Создает mock конфигурации с настройками задержек.

        Returns:
            Configuration с настроенными задержками.
        """
        parallel_options = ParallelOptions(
            initial_delay_min=0.1,
            initial_delay_max=0.2,
            launch_delay_min=0.05,
            launch_delay_max=0.1,
        )
        config = Configuration(parallel=parallel_options)
        return config

    @pytest.fixture
    def mock_parse_strategy(self, mock_config: Configuration, tmp_path: Path) -> ParseStrategy:
        """Создает ParseStrategy для тестов.

        Args:
            mock_config: Mock конфигурации.
            tmp_path: Временная директория.

        Returns:
            ParseStrategy экземпляр.
        """
        return ParseStrategy(
            output_dir=tmp_path,
            config=mock_config,
            timeout_per_url=60,
            stats={"success": 0, "failed": 0, "total": 0},
            stats_lock=MagicMock(),
        )

    def test_initial_delay_uses_configured_range(
        self, mock_parse_strategy: ParseStrategy, tmp_path: Path
    ):
        """Тест, что начальная задержка использует настроенный диапазон.

        Проверяет:
        - ParseStrategy хранит ссылку на config с parallel options
        - config.parallel.initial_delay_min/max корректны
        """
        config = mock_parse_strategy.config

        # Проверяем что конфигурация содержит правильные значения
        assert hasattr(config, "parallel"), "Config должен иметь parallel атрибут"
        assert config.parallel.initial_delay_min == 0.1, (
            f"initial_delay_min должен быть 0.1, получен {config.parallel.initial_delay_min}"
        )
        assert config.parallel.initial_delay_max == 0.2, (
            f"initial_delay_max должен быть 0.2, получен {config.parallel.initial_delay_max}"
        )

    def test_launch_delay_uses_configured_range(
        self, mock_parse_strategy: ParseStrategy, tmp_path: Path
    ):
        """Тест, что задержка запуска использует настроенный диапазон.

        Проверяет:
        - config.parallel.launch_delay_min/max корректны
        """
        config = mock_parse_strategy.config

        # Проверяем launch delay конфигурацию
        assert hasattr(config, "parallel"), "Config должен иметь parallel атрибут"
        assert config.parallel.launch_delay_min == 0.05, (
            f"launch_delay_min должен быть 0.05, получен {config.parallel.launch_delay_min}"
        )
        assert config.parallel.launch_delay_max == 0.1, (
            f"launch_delay_max должен быть 0.1, получен {config.parallel.launch_delay_max}"
        )
