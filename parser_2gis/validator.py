"""
Модуль для валидации и очистки данных.

Предоставляет функциональность для проверки и очистки данных
перед записью в файлы для повышения качества выходных данных.

ИСПРАВЛЕНИЕ 6: Этот модуль теперь использует функции из validation.py
как единственный источник истины для валидации URL, email и телефона.
DataValidator выступает как wrapper для обратной совместимости.

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
from typing import Any, Dict, List, Optional

from .logger import logger
from .validation import (
    ValidationResult as BaseValidationResult,
    validate_email as _validate_email_from_validation,
    validate_phone as _validate_phone_from_validation,
    validate_url as _validate_url_from_validation,
)


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


def _convert_base_result_to_local(base_result: BaseValidationResult) -> ValidationResult:
    """
    Конвертирует ValidationResult из validation.py в локальный формат.

    Args:
        base_result: Результат из validation.py.

    Returns:
        Локальный ValidationResult с полями is_valid, value, errors.

    Примечание:
        BaseValidationResult имеет поля: is_valid, value, error (одна ошибка)
        Локальный ValidationResult имеет поля: is_valid, value, errors (список ошибок)
    """
    errors = []
    if base_result.error:
        errors.append(base_result.error)

    return ValidationResult(is_valid=base_result.is_valid, value=base_result.value, errors=errors)


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

    Примечание:
        Для валидации URL, email и телефона используются функции из
        validation.py как единственный источник истины. Это устраняет
        дублирование кода и обеспечивает консистентность валидации.
    """

    # Constants for phone number validation
    INTERNATIONAL_PHONE_MIN_LENGTH = 10  # FIX #1: Remove duplicate validation patterns
    INTERNATIONAL_PHONE_MAX_LENGTH = 15

    # Note: EMAIL_PATTERN and URL_PATTERN are removed as validation
    # is delegated to validation.py for consistency

    def validate_phone(self, phone: str) -> ValidationResult:
        """Валидация и форматирование телефонного номера.

        Использует функцию validate_phone из validation.py как единственный
        источник истины для валидации телефонов.

        Поддерживает номера с добавочными (extension):
        - Форматы: "доб. 1234", "ext. 1234", "ext 1234", "доб.1234"
        - Возвращает номер в формате: "8 (XXX) XXX-XX-XX доб. 1234"

        - Добавлена нормализация Unicode через unicodedata.normalize("NFKC")
        - Добавлен маппинг арабских/персидских цифр на латинские
        - Поддержка fullwidth символов и смешанных систем счисления

        Args:
            phone: Телефонный номер для валидации

        Returns:
            ValidationResult с отформатированным номером или ошибками

        Примечание:
            Поддерживаются российские номера (+7/8) и международные.
            Российские номера должны содержать 11 цифр.
            Международные номера должны содержать 10-15 цифр.
        """
        # Используем функцию из validation.py
        base_result = _validate_phone_from_validation(phone)
        return _convert_base_result_to_local(base_result)

    def validate_email(self, email: str, check_mx: bool = False) -> ValidationResult:
        """Валидация email-адреса.

        Использует функцию validate_email из validation.py как основной
        источник валидации формата email.

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
            Проверка MX записей выполняется локально если check_mx=True.
        """
        # Быстрая проверка на None и пустую строку
        if not email or not email.strip():
            return ValidationResult(False, None, ["Email пустой"])

        # Нормализация email
        email = email.strip().lower()

        # Проверка максимальной длины (RFC 5321)
        if len(email) > 254:
            return ValidationResult(
                False, None, ["Email превышает максимальную длину (254 символа)"]
            )

        # Используем функцию из validation.py для проверки формата
        base_result = _validate_email_from_validation(email)

        # Если базовая валидация не прошла - возвращаем ошибку
        if not base_result.is_valid:
            return _convert_base_result_to_local(base_result)

        # Опциональная проверка MX записей домена
        if check_mx:
            mx_valid = self._check_mx_records(email)
            if not mx_valid:
                return ValidationResult(False, None, ["Домен email не имеет MX записей"])

        return ValidationResult(True, email, [])

    def validate_url(self, url: str) -> ValidationResult:
        """Валидация URL.

        Использует функцию validate_url из validation.py как единственный
        источник истины для валидации URL.

        Args:
            url: URL для валидации

        Returns:
            ValidationResult с URL или ошибками

        Примечание:
            URL должен начинаться с http:// или https://
            validation.py также проверяет на localhost и private IP адреса
        """
        # Используем функцию из validation.py
        base_result = _validate_url_from_validation(url)
        return _convert_base_result_to_local(base_result)

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
        from typing import Callable

        field_prefixes: Dict[str, Callable[[str], ValidationResult]] = {
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

    # =========================================================================
    # ПРИВАТНЫЕ МЕТОДЫ (СОХРАНЕНЫ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ)
    # =========================================================================

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
