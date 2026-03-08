"""
Модуль для валидации и очистки данных.

Предоставляет функциональность для проверки и очистки данных
перед записью в файлы для повышения качества выходных данных.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse


@dataclass
class ValidationResult:
    """Результат валидации данных.

    Содержит информацию о результате валидации, включая
    валидированное значение и список ошибок (если есть).

    Attributes:
        is_valid: Флаг, указывающий на успешность валидации
        value: Валидированное значение (или None при ошибке)
        errors: Список ошибок валидации (пустой при успехе)
    """

    is_valid: bool
    value: Optional[str]
    errors: List[str]


class DataValidator:
    """Валидатор и очиститель данных.

    Этот класс предоставляет методы для валидации и очистки
    различных типов данных (телефоны, email, URL, текст).
    Используется для повышения качества данных перед записью в файлы.

    Пример использования:
        >>> validator = DataValidator()
        >>> result = validator.validate_phone('+7 (999) 123-45-67')
        >>> if result.is_valid:
        ...     print(result.value)  # '8 (999) 123-45-67'
    """

    # Константы для валидации телефонных номеров
    INTERNATIONAL_PHONE_MIN_LENGTH = 10
    INTERNATIONAL_PHONE_MAX_LENGTH = 15

    # Паттерн для валидации email-адресов
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

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
        errors = []

        # Удаляем все кроме цифр и +
        cleaned = re.sub(r"[^\d+]", "", phone)

        # Проверяем наличие цифр
        digits_only = re.sub(r"\D", "", cleaned)
        if not digits_only:
            errors.append("Номер должен содержать цифры")
            return ValidationResult(False, None, errors)

        # Обработка российских номеров (+7 или 8)
        if cleaned.startswith("+7") or cleaned.startswith("8"):
            # Номер +8 не является корректным международным форматом
            if cleaned.startswith("+8"):
                errors.append("Некорректный международный префикс: +8 (должен быть +7 для России)")
                return ValidationResult(False, None, errors)
            
            if cleaned.startswith("+7"):
                cleaned = "8" + cleaned[2:]

            # Проверяем длину (11 цифр для России)
            if len(cleaned) != 11:
                errors.append(
                    f"Некорректная длина номера: {len(cleaned)} (ожидалось 11 для России)"
                )
                return ValidationResult(False, None, errors)

            # Форматируем российский номер
            formatted = self._format_phone(cleaned)
            return ValidationResult(True, formatted, [])

        # Обработка международных номеров
        elif cleaned.startswith("+"):
            # Международный номер (не Россия)
            international_digits = cleaned[1:]  # Убираем +

            # Проверяем длину (10-15 цифр для международных номеров)
            if len(international_digits) < self.INTERNATIONAL_PHONE_MIN_LENGTH or len(international_digits) > self.INTERNATIONAL_PHONE_MAX_LENGTH:
                errors.append(
                    f"Некорректная длина международного номера: {len(international_digits)} (ожидалось {self.INTERNATIONAL_PHONE_MIN_LENGTH}-{self.INTERNATIONAL_PHONE_MAX_LENGTH})"
                )
                return ValidationResult(False, None, errors)

            # Возвращаем в международном формате
            return ValidationResult(True, f"+{international_digits}", [])

        # Номер без префикса - пробуем определить
        else:
            # Если номер содержит 11 цифр - считаем российским
            if len(digits_only) == 11:
                if digits_only[0] == "8":
                    formatted = self._format_phone(digits_only)
                    return ValidationResult(True, formatted, [])
                else:
                    # Считаем что это номер с кодом города без 8
                    errors.append("Номер должен начинаться с +7, 8 или +[код страны]")
                    return ValidationResult(False, None, errors)
            elif self.INTERNATIONAL_PHONE_MIN_LENGTH <= len(digits_only) <= self.INTERNATIONAL_PHONE_MAX_LENGTH:
                # Международный номер без +
                return ValidationResult(True, f"+{digits_only}", [])
            else:
                errors.append(
                    f"Некорректная длина номера: {len(digits_only)} (ожидалось {self.INTERNATIONAL_PHONE_MIN_LENGTH}-{self.INTERNATIONAL_PHONE_MAX_LENGTH} цифр)"
                )
                return ValidationResult(False, None, errors)

    def _format_phone(self, phone: str) -> str:
        """Форматирование телефонного номера.

        Форматирует номер из 11 цифр в формат '8 (XXX) XXX-XX-XX'.

        Args:
            phone: Телефонный номер (11 цифр)

        Returns:
            Отформатированный телефонный номер
        """
        return f"{phone[0]} ({phone[1:4]}) {phone[4:7]}-{phone[7:9]}-{phone[9:11]}"

    def validate_email(self, email: str) -> ValidationResult:
        """Валидация email-адреса.

        Проверяет корректность email-адреса по стандартному паттерну.

        Args:
            email: Email-адрес для валидации

        Returns:
            ValidationResult с email или ошибками

        Примечание:
            Email приводится к нижнему регистру и удаляются пробелы.
            Проверка на пустую строку выполняется до обработки для оптимизации.
        """
        # Быстрая проверка на пустую строку до обработки
        if not email or not email.strip():
            return ValidationResult(False, None, ["Email пустой"])

        # Нормализация email
        email = email.strip().lower()

        # Проверка формата email
        if not self.EMAIL_PATTERN.match(email):
            return ValidationResult(False, None, ["Некорректный формат email"])

        return ValidationResult(True, email, [])

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
                return ValidationResult(False, None, [f"Неподдерживаемая схема URL: {parsed.scheme} (требуется http или https)"])

            return ValidationResult(True, url, [])
        except Exception as e:
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
        text = re.sub(r"[^\w\s\-–—(),.;:!?а-яА-ЯёЁa-zA-Z0-9]", "", text)

        # Обрезаем пробелы по краям
        text = text.strip()

        return text

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
