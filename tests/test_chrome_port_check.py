"""
Тесты для проверки корректности логики проверки порта Chrome.

Эти тесты выявляют ошибки в логике проверки порта,
которые могут привести к зависанию TUI при запуске парсинга.
"""

import socket

from parser_2gis.chrome.remote import _check_port_available, _check_port_available_internal


class TestPortCheckLogic:
    """Тесты логики проверки порта Chrome."""

    def test_check_port_available_returns_true_when_port_free(self) -> None:
        """Проверяет, что _check_port_available возвращает True, когда порт свободен."""
        # Находим свободный порт
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            free_port = s.getsockname()[1]

        # Проверяем, что порт свободен
        result = _check_port_available(free_port, timeout=0.5, retries=1)
        assert result is True, "Функция должна вернуть True для свободного порта"

    def test_check_port_available_returns_false_when_port_busy(self) -> None:
        """Проверяет, что _check_port_available возвращает False, когда порт занят."""
        # Занимаем порт
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", 0))
            s.listen(1)
            busy_port = s.getsockname()[1]

            # Проверяем, что порт занят
            result = _check_port_available(busy_port, timeout=0.5, retries=1)
            assert result is False, "Функция должна вернуть False для занятого порта"

    def test_port_check_logic_for_chrome_startup(self) -> None:
        """
        Проверяет логику ожидания запуска Chrome.

        Когда Chrome запускается, порт становится занятым.
        Цикл ожидания должен прерваться, когда порт занят (Chrome слушает).
        """
        # Симулируем запуск Chrome: занимаем порт
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", 0))
            s.listen(1)
            chrome_port = s.getsockname()[1]

            # Проверяем логику ожидания запуска Chrome
            # Порт занят = Chrome запустился
            # _check_port_available возвращает False когда порт занят
            # Условие "if not _check_port_available(port)" должно быть True
            port_is_busy = not _check_port_available(chrome_port, timeout=0.5, retries=1)
            assert port_is_busy is True, (
                "Когда Chrome запущен и слушает на порту, условие 'not _check_port_available(port)' должно быть True"
            )

    def test_port_check_logic_for_chrome_not_started(self) -> None:
        """
        Проверяет логику ожидания запуска Chrome, когда Chrome не запустился.

        Когда Chrome не запустился, порт свободен.
        Цикл ожидания должен продолжаться.
        """
        # Находим свободный порт
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            free_port = s.getsockname()[1]

        # Проверяем логику ожидания запуска Chrome
        # Порт свободен = Chrome не запустился
        # _check_port_available возвращает True когда порт свободен
        # Условие "if not _check_port_available(port)" должно быть False
        port_is_busy = not _check_port_available(free_port, timeout=0.5, retries=1)
        assert port_is_busy is False, (
            "Когда Chrome не запущен, условие 'not _check_port_available(port)' должно быть False"
        )

    def test_port_check_logic_for_connect_interface(self) -> None:
        """
        Проверяет логику подключения к Chrome DevTools.

        Когда Chrome запущен и слушает на порту, мы можем подключиться.
        Условие должно позволить подключение.
        """
        # Симулируем запуск Chrome: занимаем порт
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", 0))
            s.listen(1)
            chrome_port = s.getsockname()[1]

            # Проверяем логику подключения к DevTools
            # Порт занят = Chrome слушает, можно подключаться
            # _check_port_available возвращает False когда порт занят
            # Условие "if _check_port_available(port)" должно быть False (не пропускать попытку)
            port_is_free = _check_port_available(chrome_port, timeout=0.5, retries=1)
            assert port_is_free is False, (
                "Когда Chrome запущен и слушает на порту, условие 'if _check_port_available(port)' должно быть False"
            )

    def test_port_check_internal_consistency(self) -> None:
        """Проверяет консистентность между _check_port_available и _check_port_available."""
        # Находим свободный порт
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            free_port = s.getsockname()[1]

        # Обе функции должны вернуть одинаковый результат для свободного порта
        result1 = _check_port_available(free_port, timeout=0.5, retries=1)
        result2 = _check_port_available_internal(free_port, timeout=0.5, retries=1)
        assert result1 == result2, (
            "_check_port_available и _check_port_available_internal должны возвращать одинаковый результат"
        )

    def test_port_check_with_multiple_retries(self) -> None:
        """Проверяет работу функции с несколькими попытками."""
        # Находим свободный порт
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            free_port = s.getsockname()[1]

        # Проверяем с несколькими попытками
        result = _check_port_available(free_port, timeout=0.5, retries=3)
        assert result is True, "Функция должна вернуть True для свободного порта с несколькими попытками"
