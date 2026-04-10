"""
Тест автоматического выбора порта операционной системой.

Проверяет что функция free_port() использует port=0 для автоматического
выделения порта ОС и что выбранный порт действительно свободен.

ИСПРАВЛЕНИЕ: Порт выбирается автоматически операционной системой через bind(..., 0).
"""

import socket
from unittest.mock import patch

import pytest

from parser_2gis.chrome.utils import free_port


class TestPortSelectionOS:
    """Тесты автоматического выбора порта операционной системой."""

    def test_free_port_uses_port_zero(self) -> None:
        """Тест что free_port() использует port=0 для выделения ОС.

        Проверяет:
        - bind вызывается с портом 0
        - ОС автоматически выделяет свободный порт
        """
        captured_bind_args = []

        original_bind = socket.socket.bind

        def mock_bind(sock: socket.socket, address: tuple) -> None:
            captured_bind_args.append(address)
            return original_bind(sock, address)

        with patch.object(socket.socket, "bind", mock_bind):
            free_port()

            # Проверяем что bind был вызван с портом 0
            assert len(captured_bind_args) >= 1
            host, port_used = captured_bind_args[0]
            assert port_used == 0, f"Ожидается порт 0 для автовыделения, получен {port_used}"
            assert host == "127.0.0.1"

    def test_free_port_returns_valid_port(self) -> None:
        """Тест что free_port() возвращает валидный номер порта.

        Проверяет:
        - Порт в допустимом диапазоне (1024-65535)
        - Порт является целым числом
        """
        port = free_port()

        assert isinstance(port, int), f"Порт должен быть int, получен {type(port)}"
        assert 1024 <= port <= 65535, f"Порт {port} вне допустимого диапазона"

    def test_free_port_is_really_free(self) -> None:
        """Тест что выбранный порт действительно свободен.

        Проверяет:
        - После вызова free_port() порт доступен для bind
        - Сокет можно успешно привязать к порту
        """
        port = free_port()

        # Пробуем привязаться к тому же порту
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Устанавливаем SO_REUSEADDR как в free_port
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Это должно работать если порт свободен
            test_socket.bind(("127.0.0.1", port))
            # Если дошли сюда - порт свободен
        except OSError as e:
            pytest.fail(f"Порт {port} не свободен: {e}")
        finally:
            test_socket.close()

    def test_free_port_sets_reuseaddr_option(self) -> None:
        """Тест что free_port() устанавливает SO_REUSEADDR.

        Проверяет:
        - Опция SO_REUSEADDR устанавливается перед bind
        - Это предотвращает проблемы с занятостью порта
        """
        captured_setsockopt_calls = []

        original_setsockopt = socket.socket.setsockopt

        def mock_setsockopt(
            sock: socket.socket, level: int, optname: int, value: int | None = None
        ) -> None:
            captured_setsockopt_calls.append((level, optname, value))
            return original_setsockopt(sock, level, optname, value)

        with patch.object(socket.socket, "setsockopt", mock_setsockopt):
            free_port()

            # Проверяем что SO_REUSEADDR был установлен
            sol_socket = socket.SOL_SOCKET
            so_reuseaddr = socket.SO_REUSEADDR

            reuseaddr_calls = [
                call
                for call in captured_setsockopt_calls
                if call[0] == sol_socket and call[1] == so_reuseaddr
            ]
            assert len(reuseaddr_calls) >= 1, "SO_REUSEADDR не был установлен"
            # Проверяем что значение равно 1
            assert reuseaddr_calls[0][2] == 1, "SO_REUSEADDR должен быть равен 1"

    def test_free_port_closes_socket(self) -> None:
        """Тест что free_port() закрывает сокет после использования.

        Проверяет:
        - Сокет закрывается в контекстном менеджере
        - Ресурсы освобождаются корректно
        """
        close_called = False

        original_close = socket.socket.close

        def mock_close(sock: socket.socket) -> None:
            nonlocal close_called
            close_called = True
            return original_close(sock)

        with patch.object(socket.socket, "close", mock_close):
            free_port()

        assert close_called, "Сокет не был закрыт после получения порта"

    def test_multiple_free_port_calls_return_different_ports(self) -> None:
        """Тест что множественные вызовы free_port() возвращают разные порты.

        Проверяет:
        - Каждый вызов возвращает уникальный порт
        - Порты не пересекаются
        """
        ports = set()
        num_calls = 5

        for _ in range(num_calls):
            port = free_port()
            ports.add(port)

        # Все порты должны быть уникальными
        assert len(ports) == num_calls, (
            f"Ожидалось {num_calls} уникальных портов, получено {len(ports)}"
        )
