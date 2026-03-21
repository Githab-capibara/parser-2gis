#!/usr/bin/env python3
"""
Тесты для проверки унификации валидации URL.

Проверяет корректность работы функции validate_url из validation.py.
Тесты покрывают исправления унификации валидации URL.

Тесты:
1. test_validate_url_imported_in_main - Тест что validate_url импортирована в main.py
2. test_validate_url_dns_timeout - Тест таймаута DNS запросов (5 секунд)
3. test_validate_url_private_ip_blocked - Тест блокировки приватных IP адресов
"""

import socket
from typing import Any
from unittest.mock import patch

import pytest


class TestValidateUrlImportInMain:
    """Тесты для проверки импорта validate_url в main.py."""

    def test_validate_url_imported_in_main(self) -> None:
        """
        Тест 4.1: Проверка что validate_url импортирована в main.py.

        Импортирует main.py напрямую и проверяет что validate_url доступна.
        Проверяет что используется единая функция валидации из validation.py.
        """
        # Импортируем main модуль напрямую
        from parser_2gis.main import validate_url as main_validate_url
        from parser_2gis.validation import validate_url

        # Проверяем что это та же функция что и в validation.py
        assert main_validate_url is validate_url, (
            "main.validate_url должна ссылаться на validation.validate_url"
        )

    def test_validate_url_function_exists(self) -> None:
        """
        Проверка что функция validate_url существует в validation.py.

        Note:
            Функция должна быть доступна для импорта из validation.py
        """
        from parser_2gis.validation import validate_url

        # Проверяем что функция существует
        assert validate_url is not None
        assert callable(validate_url)

    def test_validate_url_exported_in_all(self) -> None:
        """
        Проверка что validate_url экспортируется в __all__.

        Note:
            Функция должна быть в списке экспортируемых символов
        """
        from parser_2gis import validation

        # Проверяем что validate_url в __all__
        assert "__all__" in dir(validation)
        assert "validate_url" in validation.__all__


class TestValidateUrlDnsTimeout:
    """Тесты для проверки таймаута DNS запросов."""

    def test_validate_url_dns_timeout(self) -> None:
        """
        Тест 4.2: Проверка таймаута DNS запросов (5 секунд).

        Мокирует socket.getaddrinfo для имитации медленного DNS запроса.
        Проверяет что таймаут установлен в 5 секунд.

        Note:
            Таймаут DNS запросов: 5 секунд
        """
        from parser_2gis.validation import validate_url

        # Сохраняем оригинальный таймаут
        original_timeout = socket.getdefaulttimeout()

        try:
            # Мокируем getaddrinfo для имитации медленного запроса
            def slow_getaddrinfo(*args: Any, **kwargs: Any) -> None:
                # Проверяем что таймаут установлен в 5 секунд
                current_timeout = socket.getdefaulttimeout()
                assert current_timeout == 5, f"Ожидался таймаут 5 сек, получено {current_timeout}"
                raise socket.gaierror("Mocked DNS timeout")

            with patch.object(socket, "getaddrinfo", side_effect=slow_getaddrinfo):
                # Вызываем валидацию URL с доменом
                result = validate_url("https://example.com/path")

                # Проверяем что функция не упала несмотря на ошибку DNS
                # (это нормально - домен может не разрешаться)
                assert result is not None

        finally:
            # Восстанавливаем оригинальный таймаут
            socket.setdefaulttimeout(original_timeout)

    def test_validate_url_dns_timeout_restored(self) -> None:
        """
        Проверка что таймаут DNS восстанавливается после валидации.

        Note:
            После валидации таймаут должен быть восстановлен
        """
        from parser_2gis.validation import validate_url

        # Устанавливаем тестовый таймаут
        test_timeout = 10.0
        socket.setdefaulttimeout(test_timeout)

        try:
            # Вызываем валидацию
            validate_url("https://example.com/path")

            # Проверяем что таймаут восстановлен
            current_timeout = socket.getdefaulttimeout()
            assert current_timeout == test_timeout, (
                f"Таймаут не восстановлен: ожидалось {test_timeout}, получено {current_timeout}"
            )

        finally:
            # Сбрасываем таймаут
            socket.setdefaulttimeout(None)

    def test_validate_url_with_successful_dns(self) -> None:
        """
        Проверка валидации URL с успешным DNS запросом.

        Note:
            Проверяет что валидация работает корректно при успешном DNS
        """
        from parser_2gis.validation import validate_url

        # Мокируем успешный DNS запрос
        mock_addr_info = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]

        with patch.object(socket, "getaddrinfo", return_value=mock_addr_info):
            result = validate_url("https://example.com/path")

            # Проверяем что URL валиден
            assert result.is_valid
            assert result.value == "https://example.com/path"


class TestValidateUrlPrivateIpBlocked:
    """Тесты для проверки блокировки приватных IP адресов."""

    def test_validate_url_private_ip_blocked(self) -> None:
        """
        Тест 4.3: Проверка блокировки приватных IP адресов.

        Проверяет что URL с приватными IP адресами блокируются.

        Note:
            Приватные диапазоны: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
        """
        from parser_2gis.validation import validate_url

        # Тестируем приватные IP адреса
        private_ips = [
            "http://192.168.1.1/path",
            "http://10.0.0.1/path",
            "http://172.16.0.1/path",
            "http://172.31.255.255/path",
        ]

        for ip_url in private_ips:
            result = validate_url(ip_url)
            assert result.is_valid is False, f"URL {ip_url} должен быть заблокирован"
            assert "private IP" in result.error.lower() or "private" in result.error.lower(), (
                f"Ошибка должна упоминать private IP: {result.error}"
            )

    def test_validate_url_localhost_blocked(self) -> None:
        """
        Проверка блокировки localhost.

        Note:
            localhost и 127.0.0.1 должны быть заблокированы
        """
        from parser_2gis.validation import validate_url

        # Тестируем localhost
        localhost_urls = [
            "http://localhost/path",
            "http://127.0.0.1/path",
            "http://localhost:8080/path",
            "https://127.0.0.1:443/path",
        ]

        for url in localhost_urls:
            result = validate_url(url)
            assert result.is_valid is False, f"URL {url} должен быть заблокирован"
            assert "localhost" in result.error.lower(), (
                f"Ошибка должна упоминать localhost: {result.error}"
            )

    def test_validate_url_loopback_blocked(self) -> None:
        """
        Проверка блокировки loopback адресов.

        Note:
            Loopback адреса должны быть заблокированы
        """
        from parser_2gis.validation import validate_url

        # Тестируем loopback
        result = validate_url("http://127.0.0.1/path")
        assert result.is_valid is False
        assert "loopback" in result.error.lower() or "localhost" in result.error.lower()

    def test_validate_url_link_local_blocked(self) -> None:
        """
        Проверка блокировки link-local адресов.

        Note:
            Link-local адреса (169.254.0.0/16) должны быть заблокированы
        """
        from parser_2gis.validation import validate_url

        # Тестируем link-local
        result = validate_url("http://169.254.1.1/path")
        assert result.is_valid is False

    def test_validate_url_public_ip_allowed(self) -> None:
        """
        Проверка что публичные IP адреса разрешены.

        Note:
            Публичные IP адреса должны проходить валидацию
        """
        from parser_2gis.validation import validate_url

        # Мокируем DNS запрос для публичного IP
        mock_addr_info = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]

        with patch.object(socket, "getaddrinfo", return_value=mock_addr_info):
            # Тестируем публичный URL
            result = validate_url("https://example.com/path")
            assert result.is_valid is True, f"URL должен быть валиден: {result.error}"

    def test_validate_url_private_dns_resolution_blocked(self) -> None:
        """
        Проверка блокировки доменов которые разрешаются в private IP.

        Note:
            Домены которые разрешаются в private IP должны быть заблокированы
        """
        from parser_2gis.validation import validate_url

        # Мокируем DNS запрос который возвращает private IP
        mock_addr_info = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0))]

        with patch.object(socket, "getaddrinfo", return_value=mock_addr_info):
            result = validate_url("https://internal.example.com/path")
            assert result.is_valid is False, (
                "Домен разрешающийся в private IP должен быть заблокирован"
            )
            assert "private" in result.error.lower(), (
                f"Ошибка должна упоминать private IP: {result.error}"
            )


class TestValidateUrlEdgeCases:
    """Тесты для проверки граничных случаев валидации URL."""

    def test_validate_url_invalid_scheme(self) -> None:
        """
        Проверка что URL с некорректной схемой блокируются.

        Note:
            Только http и https разрешены
        """
        from parser_2gis.validation import validate_url

        invalid_urls = [
            "ftp://example.com/path",
            "file://example.com/path",
            "mailto://example.com",
            "example.com/path",  # Без схемы
        ]

        for url in invalid_urls:
            result = validate_url(url)
            assert result.is_valid is False, f"URL {url} должен быть невалиден"

    def test_validate_url_missing_hostname(self) -> None:
        """
        Проверка что URL без hostname блокируются.

        Note:
            URL должен содержать домен
        """
        from parser_2gis.validation import validate_url

        result = validate_url("http:///path")
        assert result.is_valid is False
        assert "домен" in result.error.lower()

    def test_validate_url_valid_https(self) -> None:
        """
        Проверка что валидные HTTPS URL проходят валидацию.

        Note:
            HTTPS URL должны проходить валидацию
        """
        from parser_2gis.validation import validate_url

        result = validate_url("https://2gis.ru/moscow/search/Кафе")
        assert result.is_valid is True

    def test_validate_url_valid_http(self) -> None:
        """
        Проверка что валидные HTTP URL проходят валидацию.

        Note:
            HTTP URL должны проходить валидацию
        """
        from parser_2gis.validation import validate_url

        result = validate_url("http://example.com/path")
        assert result.is_valid is True


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
