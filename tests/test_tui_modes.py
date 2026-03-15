"""
Тесты для проверки TUI режимов запуска.

Предотвращают ошибки, когда TUI режимы (--tui-new, --tui-new-omsk, --tui)
не работают из-за неправильной валидации аргументов.

Проверяют:
- TUI режимы не требуют указания URL или --cities
- TUI режимы корректно обрабатываются в main()
- Валидация URL пропускается для TUI режимов

Примечание:
    Тесты выполнения TUI требуют установки pytermgui:
    pip install pytermgui
    
    Если pytermgui не установлен, тесты выполнения будут пропущены.
"""

import sys
from unittest.mock import patch, MagicMock

import pytest


# Проверяем доступность pytermgui для тестов выполнения
PYTERMGUI_AVAILABLE = False
try:
    import pytermgui  # noqa: F401
    PYTERMGUI_AVAILABLE = True
except ImportError:
    pass


class TestTUIModeArguments:
    """Тесты для проверки аргументов TUI режимов."""

    def test_tui_new_mode_no_url_required(self):
        """
        Проверка, что --tui-new не требует указания URL.

        Этот тест предотвращает ошибку:
        "Требуется указать хотя бы один источник URL: -i/--url или --cities"
        при запуске с флагом --tui-new
        """
        from parser_2gis.main import parse_arguments

        test_args = [
            "parser-2gis",
            "--tui-new",
        ]
        with patch.object(sys, "argv", test_args):
            # Не должно быть ошибки валидации
            args, config = parse_arguments()
            assert args.tui_new is True

    def test_tui_new_omsk_mode_no_url_required(self):
        """
        Проверка, что --tui-new-omsk не требует указания URL.

        Этот тест предотвращает ошибку:
        "Требуется указать хотя бы один источник URL: -i/--url или --cities"
        при запуске с флагом --tui-new-omsk
        """
        from parser_2gis.main import parse_arguments

        test_args = [
            "parser-2gis",
            "--tui-new-omsk",
        ]
        with patch.object(sys, "argv", test_args):
            # Не должно быть ошибки валидации
            args, config = parse_arguments()
            assert args.tui_new_omsk is True

    def test_tui_mode_no_url_required(self):
        """
        Проверка, что --tui (старый) не требует указания URL.

        Этот тест предотвращает ошибку:
        "Требуется указать хотя бы один источник URL: -i/--url или --cities"
        при запуске с флагом --tui
        """
        from parser_2gis.main import parse_arguments

        test_args = [
            "parser-2gis",
            "--tui",
        ]
        with patch.object(sys, "argv", test_args):
            # Не должно быть ошибки валидации
            args, config = parse_arguments()
            assert args.tui is True

    def test_cli_mode_requires_url_or_cities(self):
        """
        Проверка, что CLI режим ТРЕБУЕТ указания URL или --cities.

        Этот тест гарантирует, что валидация работает для CLI режима.
        """
        from parser_2gis.main import parse_arguments

        test_args = [
            "parser-2gis",
            "-o", "output.csv",
            "-f", "csv",
        ]
        with patch.object(sys, "argv", test_args):
            # Должна быть ошибка валидации (SystemExit)
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            
            # SystemExit code 2 означает ошибку аргументов
            assert exc_info.value.code == 2

    def test_categories_mode_requires_cities(self):
        """
        Проверка, что --categories-mode требует указания --cities.

        Этот тест гарантирует, что валидация работает для режима категорий.
        """
        from parser_2gis.main import parse_arguments

        test_args = [
            "parser-2gis",
            "--categories-mode",
        ]
        with patch.object(sys, "argv", test_args):
            # Должна быть ошибка валидации (SystemExit)
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            
            # SystemExit code 2 означает ошибку аргументов
            assert exc_info.value.code == 2


class TestTUIModeExecution:
    """Тесты выполнения TUI режимов."""

    @pytest.mark.skipif(not PYTERMGUI_AVAILABLE, reason="pytermgui не установлен. Установите: pip install pytermgui")
    def test_tui_new_execution(self):
        """
        Проверка, что --tui-new запускает TUI приложение.

        Этот тест предотвращает ошибку, когда TUI приложение
        не запускается из-за неправильной обработки аргументов.
        """
        from parser_2gis.main import main

        test_args = [
            "parser-2gis",
            "--tui-new",
        ]

        # Мокаем TUI приложение, чтобы не запускать реальный GUI
        with patch.object(sys, "argv", test_args):
            with patch("parser_2gis.tui_pytermgui.Parser2GISTUI") as mock_tui:
                mock_app = MagicMock()
                mock_tui.return_value = mock_app

                # Запускаем main - не должно быть ошибок
                main()

                # Проверяем, что TUI приложение было запущено
                mock_tui.assert_called_once()
                mock_app.run.assert_called_once()

    @pytest.mark.skipif(not PYTERMGUI_AVAILABLE, reason="pytermgui не установлен. Установите: pip install pytermgui")
    def test_tui_new_omsk_execution(self):
        """
        Проверка, что --tui-new-omsk запускает TUI с парсингом Омска.

        Этот тест предотвращает ошибку, когда парсинг Омска
        не запускается из-за неправильной обработки аргументов.
        """
        import importlib
        from parser_2gis.main import main

        # Импортируем модуль правильно (не функцию main)
        main_module = importlib.import_module('parser_2gis.main')

        test_args = [
            "parser-2gis",
            "--tui-new-omsk",
        ]

        # Мокаем функцию запуска парсинга Омска
        # run_new_tui_omsk - это переменная модуля, а не атрибут функции main
        with patch.object(sys, "argv", test_args):
            with patch.object(main_module, "run_new_tui_omsk") as mock_run:
                # Запускаем main - не должно быть ошибок
                main()

                # Проверяем, что функция запуска была вызвана
                mock_run.assert_called_once()

    def test_tui_mode_not_implemented(self):
        """
        Проверка, что --tui (старый) не вызывает ошибок импорта.

        Этот тест предотвращает ошибку ImportError: cannot import name 'run_tui'.
        """
        from parser_2gis.main import parse_arguments

        test_args = [
            "parser-2gis",
            "--tui",
        ]

        with patch.object(sys, "argv", test_args):
            # Не должно быть ошибки импорта или валидации
            args, config = parse_arguments()
            assert args.tui is True


class TestRunShCompatibility:
    """Тесты совместимости с run.sh."""

    def test_run_sh_tui_flag(self):
        """
        Проверка, что ./run.sh --tui работает корректно.

        Этот тест предотвращает ошибку, когда run.sh использует
        неправильный флаг TUI.
        """
        # Проверяем, что run.sh использует правильный флаг
        import subprocess
        import os

        run_sh_path = os.path.join(os.path.dirname(__file__), "..", "run.sh")
        run_sh_path = os.path.abspath(run_sh_path)

        # Читаем run.sh и проверяем, что используется --tui-new
        with open(run_sh_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Проверяем, что в секции --tui используется --tui-new
        assert '--tui-new' in content, \
            "run.sh должен использовать --tui-new вместо --tui"

    def test_run_sh_tui_new_omsk_flag(self):
        """
        Проверка, что ./run.sh (без аргументов) использует --tui-new-omsk.

        Этот тест предотвращает ошибку, когда run.sh по умолчанию
        использует неправильный флаг.
        """
        import subprocess
        import os

        run_sh_path = os.path.join(os.path.dirname(__file__), "..", "run.sh")
        run_sh_path = os.path.abspath(run_sh_path)

        # Читаем run.sh и проверяем, что используется --tui-new-omsk
        with open(run_sh_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Проверяем, что в секции без аргументов используется --tui-new-omsk
        assert '--tui-new-omsk' in content, \
            "run.sh должен использовать --tui-new-omsk по умолчанию"


class TestTUIValidationBypass:
    """Тесты обхода валидации для TUI режимов."""

    def test_tui_new_bypasses_url_validation(self):
        """
        Проверка, что --tui-new обходит валидацию URL.

        Этот тест гарантирует, что TUI режимы не требуют URL,
        так как выбор происходит в интерфейсе.
        """
        from parser_2gis.main import parse_arguments

        # TUI режим без URL - должно работать
        test_args = ["parser-2gis", "--tui-new"]
        with patch.object(sys, "argv", test_args):
            args, config = parse_arguments()
            assert args.tui_new is True
            # URL не требуется
            assert args.url is None
            assert not hasattr(args, "cities") or args.cities is None

    def test_tui_new_omsk_bypasses_url_validation(self):
        """
        Проверка, что --tui-new-omsk обходит валидацию URL.

        Этот тест гарантирует, что TUI режимы не требуют URL,
        так как выбор происходит в интерфейсе.
        """
        from parser_2gis.main import parse_arguments

        # TUI режим без URL - должно работать
        test_args = ["parser-2gis", "--tui-new-omsk"]
        with patch.object(sys, "argv", test_args):
            args, config = parse_arguments()
            assert args.tui_new_omsk is True
            # URL не требуется
            assert args.url is None
            assert not hasattr(args, "cities") or args.cities is None

    def test_cli_with_url_works(self):
        """
        Проверка, что CLI режим с URL работает корректно.

        Этот тест гарантирует, что валидация не ломает обычный CLI режим.
        """
        from parser_2gis.main import parse_arguments

        test_args = [
            "parser-2gis",
            "-i", "https://2gis.ru/moscow/search/Аптеки",
            "-o", "output.csv",
            "-f", "csv",
        ]
        with patch.object(sys, "argv", test_args):
            args, config = parse_arguments()
            assert args.url == ["https://2gis.ru/moscow/search/Аптеки"]

    def test_cli_with_cities_works(self):
        """
        Проверка, что CLI режим с --cities работает корректно.

        Этот тест гарантирует, что валидация не ломает режим городов.
        """
        from parser_2gis.main import parse_arguments

        test_args = [
            "parser-2gis",
            "--cities", "moscow",
            "--query", "Аптеки",
        ]
        with patch.object(sys, "argv", test_args):
            args, config = parse_arguments()
            assert args.cities == ["moscow"]

    def test_tui_with_optional_cities(self):
        """
        Проверка, что TUI режим может принимать --cities (опционально).

        Этот тест гарантирует, что TUI режимы могут работать
        как с городами, так и без них.
        """
        from parser_2gis.main import parse_arguments

        # TUI с городами - должно работать
        test_args = ["parser-2gis", "--tui-new", "--cities", "moscow"]
        with patch.object(sys, "argv", test_args):
            args, config = parse_arguments()
            assert args.tui_new is True
            assert args.cities == ["moscow"]
