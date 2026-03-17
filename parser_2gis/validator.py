"""
Модуль для валидации и очистки данных.

Предоставляет функциональность для проверки и очистки данных
перед записью в файлы для повышения качества выходных данных.

Пример использования модуля:
    >>> from .validator import DataValidator, ValidationResult
    >>> validator = DataValidator()
    >>> # Валидация телефона
    >>> result = validator.validate_phone('+7 (999) 123-45-67')
    >>> print(result.value)
    '8 (999) 123-45-67'
    >>> # Валидация email
    >>> email_result = validator.validate_email('test@example.com')
    >>> print(email_result.is_valid)
    True
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from .logger import logger


@dataclass
class ValidationResult:
    """Результат валидации данных.

    Содержит информацию о результате валидации, включая
    валидированное значение и список ошибок (если есть).

    Attributes:
        is_valid: Флаг, указывающий на успешность валидации.
                  True если валидация прошла успешно, False если есть ошибки.
        value: Валидированное значение (или None при ошибке).
               Содержит очищенное/нормализованное значение.
        errors: Список ошибок валидации (пустой при успехе).
                Каждый элемент - строка с описанием ошибки.

    Пример использования:
        >>> result = ValidationResult(
        ...     is_valid=True,
        ...     value='+7 (999) 123-45-67',
        ...     errors=[]
        ... )
        >>> if result.is_valid:
        ...     print(f"Валидация успешна: {result.value}")
        'Валидация успешна: +7 (999) 123-45-67'
        >>> # Проверка ошибок
        >>> invalid_result = ValidationResult(is_valid=False, value=None, errors=["Неверный формат"])
        >>> print(invalid_result.errors[0])
        'Неверный формат'
    """

    is_valid: bool
    value: Optional[str]
    errors: List[str]


class DataValidator:
    """Валидатор и очиститель данных.

    Этот класс предоставляет методы для валидации и очистки
    различных типов данных (телефоны, email, URL, текст).
    Используется для повышения качества данных перед записью в файлы.

    Поддерживаемые типы валидации:
        - validate_phone: Валидация и нормализация телефонных номеров
        - validate_email: Валидация email-адресов
        - validate_url: Валидация URL
        - validate_text: Валидация и очистка текста

    Пример использования:
        >>> validator = DataValidator()
        >>> # Валидация телефона
        >>> result = validator.validate_phone('+7 (999) 123-45-67')
        >>> if result.is_valid:
        ...     print(result.value)  # '8 (999) 123-45-67'
        >>> # Валидация email
        >>> email_result = validator.validate_email('test@example.com')
        >>> print(email_result.is_valid)
        True
        >>> # Валидация URL
        >>> url_result = validator.validate_url('https://example.com')
        >>> print(url_result.is_valid)
        True
    """

    # Константы для валидации телефонных номеров
    INTERNATIONAL_PHONE_MIN_LENGTH = 10
    INTERNATIONAL_PHONE_MAX_LENGTH = 15

    # Паттерн для валидации email-адресов
    # Улучшенный паттерн с поддержкой IDN (Internationalized Domain Names)
    # Поддерживает Unicode символы в доменной части (например: почта@пример.рф)
    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@"  # Локальная часть
        r"[a-zA-Z0-9\u0080-\uFFFF.-]+\.[a-zA-Z\u0080-\uFFFF]{2,}$"  # Домен с поддержкой IDN
    )

    # Паттерн для валидации URL
    URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")

    def validate_phone(self, phone: str) -> ValidationResult:
        """Валидация и форматирование телефонного номера.

        Проверяет корректность телефонного номера и форматирует его
        в единый формат: '8 (XXX) XXX-XX-XX' для российских номеров
        или международный формат для других стран.

        Args:
            phone: Телефонный номер для валидации

        Returns:
            ValidationResult с отформатированным номером или ошибками

        Примечание:
            Поддерживаются российские номера (+7/8) и международные.
            Российские номера должны содержать 11 цифр.
            Международные номера должны содержать 10-15 цифр.
        """
        # Проверяем на None и пустую строку
        if not phone or not phone.strip():
            return ValidationResult(False, None, ["Номер должен содержать цифры"])

        # Удаляем все кроме цифр и +
        cleaned = re.sub(r"[^\d+]", "", phone)
        digits_only = re.sub(r"\D", "", cleaned)

        if not digits_only:
            return ValidationResult(False, None, ["Номер должен содержать цифры"])

        # Обработка российских номеров (+7 или 8)
        if cleaned.startswith("+8"):
            return ValidationResult(
                False, None, ["Некорректный международный префикс: +8 (должен быть +7 для России)"]
            )

        if cleaned.startswith("+7") or cleaned.startswith("8"):
            # Конвертируем +7 в 8 для внутреннего представления
            if cleaned.startswith("+7"):
                cleaned = "8" + cleaned[2:]

            if len(cleaned) != 11:
                return ValidationResult(
                    False, None, [f"Некорректная длина номера: {len(cleaned)} (ожидалось 11 для России)"]
                )

            return ValidationResult(True, self._format_phone(cleaned), [])

        # Обработка международных номеров
        if cleaned.startswith("+"):
            international_digits = cleaned[1:]

            min_len = self.INTERNATIONAL_PHONE_MIN_LENGTH
            max_len = self.INTERNATIONAL_PHONE_MAX_LENGTH
            if not (min_len <= len(international_digits) <= max_len):
                return ValidationResult(
                    False, None, [
                        f"Некорректная длина международного номера: {len(international_digits)} "
                        f"(ожидалось {self.INTERNATIONAL_PHONE_MIN_LENGTH}-{self.INTERNATIONAL_PHONE_MAX_LENGTH})"
                    ]
                )

            return ValidationResult(True, f"+{international_digits}", [])

        # Номер без префикса - пробуем определить
        if len(digits_only) == 11:
            if digits_only[0] == "8":
                return ValidationResult(True, self._format_phone(digits_only), [])
            # Предполагаем российский номер без префикса
            return ValidationResult(True, self._format_phone("8" + digits_only), [])

        if self.INTERNATIONAL_PHONE_MIN_LENGTH <= len(digits_only) <= self.INTERNATIONAL_PHONE_MAX_LENGTH:
            return ValidationResult(True, f"+{digits_only}", [])

        return ValidationResult(
            False, None, [
                f"Некорректная длина номера: {len(digits_only)} "
                f"(ожидалось {self.INTERNATIONAL_PHONE_MIN_LENGTH}-{self.INTERNATIONAL_PHONE_MAX_LENGTH} цифр)"
            ]
        )

    def _format_phone(self, phone: str) -> str:
        """Форматирование телефонного номера.

        Форматирует номер из 11 цифр в формат '8 (XXX) XXX-XX-XX'.

        Args:
            phone: Телефонный номер (11 цифр)

        Returns:
            Отформатированный телефонный номер
        """
        return f"{phone[0]} ({phone[1:4]}) {phone[4:7]}-{phone[7:9]}-{phone[9:11]}"

    def validate_email(self, email: str, check_mx: bool = False) -> ValidationResult:
        """Валидация email-адреса.

        Проверяет корректность email-адреса по стандартному паттерну.

        Args:
            email: Email-адрес для валидации.
            check_mx: Опциональная проверка MX записей домена (требует dns.resolver).
                     По умолчанию False для производительности.

        Returns:
            ValidationResult с email или ошибками.

        Примечание:
            Email приводится к нижнему регистру и удаляются пробелы.
            Проверка на пустую строку выполняется до обработки для оптимизации.
            Максимальная длина email: 254 символа (RFC 5321).
            Поддерживаются IDN домены (например: почта@пример.рф).
        """
        # Быстрая проверка на None и пустую строку
        if not email or not email.strip():
            return ValidationResult(False, None, ["Email пустой"])

        # Нормализация email
        email = email.strip().lower()

        # Проверка максимальной длины (RFC 5321)
        if len(email) > 254:
            return ValidationResult(False, None, ["Email превышает максимальную длину (254 символа)"])

        # Проверка наличия @ - быстрая предварительная проверка
        if "@" not in email:
            return ValidationResult(False, None, ["Email должен содержать символ @"])

        # Проверка формата email с улучшенным regex (поддержка IDN)
        if not self.EMAIL_PATTERN.match(email):
            return ValidationResult(False, None, ["Некорректный формат email"])

        # Опциональная проверка MX записей домена
        if check_mx:
            mx_valid = self._check_mx_records(email)
            if not mx_valid:
                return ValidationResult(False, None, ["Домен email не имеет MX записей"])

        return ValidationResult(True, email, [])

    def _check_mx_records(self, email: str) -> bool:
        """
        Проверяет наличие MX записей для домена email.

        Args:
            email: Email для проверки.

        Returns:
            True если MX записи существуют, False иначе.

        Примечание:
            Метод требует установленную библиотеку dnspython.
            При отсутствии библиотеки возвращает False (проверка не проходит).
            Это предотвращает ложную валидацию email без реальной проверки DNS.
        """
        try:
            import dns.resolver
        except ImportError:
            # dnspython не установлен - возвращаем False для безопасности
            # Это предотвращает валидацию email без реальной проверки MX записей
            logger.debug("dnspython не установлен, проверка MX записей невозможна")
            return False

        try:
            # Извлекаем домен из email
            domain = email.split("@")[1]

            # Пытаемся получить MX записи
            answers = dns.resolver.resolve(domain, "MX")

            # Проверяем, что есть хотя бы одна запись
            return len(answers) > 0

        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            # Домен не существует или нет MX записей
            logger.debug("Домен %s не имеет MX записей", domain)
            return False
        except Exception as e:
            # Любая другая ошибка - возвращаем False для безопасности
            logger.debug("Ошибка при проверке MX записей для %s: %s", domain, e)
            return False

    def validate_url(self, url: str) -> ValidationResult:
        """Валидация URL.

        Проверяет корректность URL (http или https).

        Args:
            url: URL для валидации

        Returns:
            ValidationResult с URL или ошибками

        Примечание:
            URL должен начинаться с http:// или https://
        """
        url = url.strip()

        if not url:
            return ValidationResult(False, None, ["URL пустой"])

        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ValidationResult(False, None, ["Некорректный формат URL"])

            # Проверяем что схема именно http или https
            if parsed.scheme not in ('http', 'https'):
                error_msg = (f"Неподдерживаемая схема URL: {parsed.scheme} "
                            "(требуется http или https)")
                return ValidationResult(False, None, [error_msg])

            return ValidationResult(True, url, [])
        except (ValueError, TypeError) as e:
            # Ловим только ожидаемые исключения парсинга URL
            return ValidationResult(False, None, [str(e)])

    def clean_text(self, text: str) -> str:
        """Очистка текста от лишних символов.

        Удаляет лишние пробелы и специальные символы,
        сохраняя русский и английский текст, цифры и основные знаки.

        Args:
            text: Текст для очистки

        Returns:
            Очищенный текст

        Примечание:
            Сохраняются: буквы (русский и английский), цифры,
            тире, скобки, запятые, точки, двоеточия,
            вопросительные и восклицательные знаки.
        """
        # Удаляем лишние пробелы
        text = re.sub(r"\s+", " ", text)

        # Удаляем спецсимволы (кроме русского, английского, цифр и основных знаков)
        # \w уже включает буквы и цифры, поэтому явно указываем только кириллицу и дополнительные символы
        text = re.sub(r"[^\w\s\-–—(),.;:!?а-яА-ЯёЁ]", "", text)

        # Обрезаем пробелы по краям
        return text.strip()

    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация записи организации.

        Проводит полную валидацию записи организации, включая
        телефоны, email, URL и текстовые поля.

        Args:
            record: Запись организации для валидации

        Returns:
            Валидированная запись с очищенными данными

        Примечание:
            Некорректные данные заменяются на None.
            Текстовые поля очищаются от лишних символов.
        """
        validated = record.copy()

        # Конфигурация префиксов полей для валидации
        field_prefixes = {
            "phone_": self.validate_phone,
            "email_": self.validate_email,
            "website_": self.validate_url,
        }

        # Валидация полей с префиксами
        for prefix, validator_func in field_prefixes.items():
            for key in list(validated.keys()):
                if key.startswith(prefix) and validated[key]:
                    result = validator_func(validated[key])
                    if result.is_valid:
                        validated[key] = result.value
                    else:
                        validated[key] = None

        # Очистка текстовых полей
        text_fields = ["name", "description", "address"]
        for field in text_fields:
            value = validated.get(field)
            if value:
                validated[field] = self.clean_text(value)

        return validated
