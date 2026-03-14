"""
Тесты для модуля runner.

Проверяют следующие возможности:
- AbstractRunner
- GUIRunner
- CLIRunner
"""

from unittest.mock import MagicMock

import pytest

from parser_2gis.runner.runner import AbstractRunner


class TestAbstractRunner:
    """Тесты для AbstractRunner."""

    def test_abstract_runner_creation(self):
        """Проверка создания AbstractRunner."""
        # AbstractRunner нельзя создать напрямую
        with pytest.raises(TypeError):
            AbstractRunner([], '', '', MagicMock())

    def test_abstract_runner_requires_subclass(self):
        """Проверка, что требуется подкласс."""
        class ConcreteRunner(AbstractRunner):
            def start(self):
                pass

            def stop(self):
                pass

        config = MagicMock()
        runner = ConcreteRunner(['url1'], 'output.csv', 'csv', config)
        assert runner._urls == ['url1']
        assert runner._output_path == 'output.csv'
        assert runner._format == 'csv'

    def test_abstract_runner_has_start_method(self):
        """Проверка наличия метода start."""
        class ConcreteRunner(AbstractRunner):
            def start(self):
                return 'started'

            def stop(self):
                return 'stopped'

        config = MagicMock()
        runner = ConcreteRunner([], '', '', config)
        assert hasattr(runner, 'start')
        assert runner.start() == 'started'

    def test_abstract_runner_has_stop_method(self):
        """Проверка наличия метода stop."""
        class ConcreteRunner(AbstractRunner):
            def start(self):
                pass

            def stop(self):
                return 'stopped'

        config = MagicMock()
        runner = ConcreteRunner([], '', '', config)
        assert hasattr(runner, 'stop')
        assert runner.stop() == 'stopped'

    def test_abstract_runner_stores_urls(self):
        """Проверка сохранения URL."""
        class ConcreteRunner(AbstractRunner):
            def start(self):
                pass

            def stop(self):
                pass

        urls = ['url1', 'url2', 'url3']
        config = MagicMock()
        runner = ConcreteRunner(urls, '', '', config)
        assert runner._urls == urls

    def test_abstract_runner_stores_output_path(self):
        """Проверка сохранения пути вывода."""
        class ConcreteRunner(AbstractRunner):
            def start(self):
                pass

            def stop(self):
                pass

        config = MagicMock()
        runner = ConcreteRunner([], 'output.csv', '', config)
        assert runner._output_path == 'output.csv'

    def test_abstract_runner_stores_format(self):
        """Проверка сохранения формата."""
        class ConcreteRunner(AbstractRunner):
            def start(self):
                pass

            def stop(self):
                pass

        config = MagicMock()
        runner = ConcreteRunner([], '', 'json', config)
        assert runner._format == 'json'

    def test_abstract_runner_stores_config(self):
        """Проверка сохранения конфигурации."""
        class ConcreteRunner(AbstractRunner):
            def start(self):
                pass

            def stop(self):
                pass

        config = MagicMock()
        runner = ConcreteRunner([], '', '', config)
        assert runner._config is config


class TestGUIRunner:
    """Тесты для GUIRunner."""

    def test_gui_runner_import(self):
        """Проверка импорта GUIRunner."""
        from parser_2gis.runner import GUIRunner
        assert GUIRunner is not None

    def test_gui_runner_is_abstract_runner_subclass(self):
        """Проверка наследования GUIRunner."""
        from parser_2gis.runner import GUIRunner
        assert issubclass(GUIRunner, AbstractRunner)

    def test_gui_runner_creation(self):
        """Проверка создания GUIRunner."""
        from parser_2gis.runner import GUIRunner

        config = MagicMock()
        runner = GUIRunner(['url1'], 'output.csv', 'csv', config)
        assert runner is not None
        assert runner._urls == ['url1']

    def test_gui_runner_has_start(self):
        """Проверка наличия метода start."""
        from parser_2gis.runner import GUIRunner

        config = MagicMock()
        runner = GUIRunner([], '', '', config)
        assert hasattr(runner, 'start')
        assert callable(runner.start)

    def test_gui_runner_has_stop(self):
        """Проверка наличия метода stop."""
        from parser_2gis.runner import GUIRunner

        config = MagicMock()
        runner = GUIRunner([], '', '', config)
        assert hasattr(runner, 'stop')
        assert callable(runner.stop)


class TestCLIRunner:
    """Тесты для CLIRunner."""

    def test_cli_runner_import(self):
        """Проверка импорта CLIRunner."""
        from parser_2gis.runner import CLIRunner
        assert CLIRunner is not None

    def test_cli_runner_is_abstract_runner_subclass(self):
        """Проверка наследования CLIRunner."""
        from parser_2gis.runner import CLIRunner
        assert issubclass(CLIRunner, AbstractRunner)

    def test_cli_runner_creation(self):
        """Проверка создания CLIRunner."""
        from parser_2gis.runner import CLIRunner

        config = MagicMock()
        runner = CLIRunner(['url1'], 'output.csv', 'csv', config)
        assert runner is not None
        assert runner._urls == ['url1']

    def test_cli_runner_has_start(self):
        """Проверка наличия метода start."""
        from parser_2gis.runner import CLIRunner

        config = MagicMock()
        runner = CLIRunner([], '', '', config)
        assert hasattr(runner, 'start')
        assert callable(runner.start)

    def test_cli_runner_has_stop(self):
        """Проверка наличия метода stop."""
        from parser_2gis.runner import CLIRunner

        config = MagicMock()
        runner = CLIRunner([], '', '', config)
        assert hasattr(runner, 'stop')
        assert callable(runner.stop)


class TestRunnerModule:
    """Тесты для модуля runner."""

    def test_runner_module_exports(self):
        """Проверка экспорта модуля."""
        from parser_2gis import runner

        assert hasattr(runner, 'AbstractRunner')
        assert hasattr(runner, 'GUIRunner')
        assert hasattr(runner, 'CLIRunner')

    def test_runner_all(self):
        """Проверка __all__."""
        from parser_2gis.runner import __all__

        assert 'AbstractRunner' in __all__
        assert 'GUIRunner' in __all__
        assert 'CLIRunner' in __all__


class TestRunnerWithMockConfig:
    """Тесты для runner с mock конфигурацией."""

    def test_gui_runner_with_mock_config(self):
        """Проверка GUIRunner с mock конфигурацией."""
        from parser_2gis.runner import GUIRunner

        config = MagicMock()
        config.chrome.headless = True
        config.parser.max_records = 10

        runner = GUIRunner(['url1'], 'output.csv', 'csv', config)
        assert runner._config.chrome.headless is True
        assert runner._config.parser.max_records == 10

    def test_cli_runner_with_mock_config(self):
        """Проверка CLIRunner с mock конфигурацией."""
        from parser_2gis.runner import CLIRunner

        config = MagicMock()
        config.chrome.headless = False
        config.parser.max_records = 50

        runner = CLIRunner(['url1'], 'output.json', 'json', config)
        assert runner._config.chrome.headless is False
        assert runner._config.parser.max_records == 50
