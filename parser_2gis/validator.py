"""
Модуль для валидации и очистки данных.

Предоставляет функциональность для проверки и очистки данных
перед записью в файлы для повышения качества выходных данных.
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any
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
    errors: list[str]


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
    
    # Паттерн для валидации email-адресов
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    # Паттерн для валидации URL
    URL_PATTERN = re.compile(
        r'^https?://[^\s/$.?#].[^\s]*$'
    )
    
    def validate_phone(self, phone: str) -> ValidationResult:
        """Валидация и форматирование телефонного номера.
        
        Проверяет корректность телефонного номера и форматирует его
        в единый формат: '8 (XXX) XXX-XX-XX'.
        
        Args:
            phone: Телефонный номер для валидации
            
        Returns:
            ValidationResult с отформатированным номером или ошибками
            
        Примечание:
            Поддерживаются номера, начинающиеся с +7 или 8.
            Должны содержать ровно 11 цифр.
        """
        errors = []
        
        # Удаляем все кроме цифр и +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Проверяем, что номер начинается с +7 или 8
        if cleaned.startswith('+7'):
            cleaned = '8' + cleaned[2:]
        elif not cleaned.startswith('8'):
            errors.append("Номер должен начинаться с +7 или 8")
            return ValidationResult(False, None, errors)
        
        # Проверяем длину (11 цифр для России)
        if len(cleaned) != 11:
            errors.append(f"Некорректная длина номера: {len(cleaned)} (ожидалось 11)")
            return ValidationResult(False, None, errors)
        
        # Форматируем номер
        formatted = self._format_phone(cleaned)
        
        return ValidationResult(True, formatted, [])
    
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
        """
        email = email.strip().lower()
        
        if not email:
            return ValidationResult(False, None, ["Email пустой"])
        
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
        text = re.sub(r'\s+', ' ', text)
        
        # Удаляем спецсимволы (кроме русского, английского, цифр и основных знаков)
        text = re.sub(r'[^\w\s\-–—(),.;:!?а-яА-ЯёЁa-zA-Z0-9]', '', text)
        
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
        
        # Валидация телефонов
        for key in list(validated.keys()):
            if key.startswith('phone_') and validated[key]:
                result = self.validate_phone(validated[key])
                if result.is_valid:
                    validated[key] = result.value
                else:
                    validated[key] = None
        
        # Валидация email
        for key in list(validated.keys()):
            if key.startswith('email_') and validated[key]:
                result = self.validate_email(validated[key])
                if result.is_valid:
                    validated[key] = result.value
                else:
                    validated[key] = None
        
        # Валидация URL
        for key in list(validated.keys()):
            if key.startswith('website_') and validated[key]:
                result = self.validate_url(validated[key])
                if result.is_valid:
                    validated[key] = result.value
                else:
                    validated[key] = None
        
        # Очистка текстовых полей
        text_fields = ['name', 'description', 'address']
        for field in text_fields:
            if validated.get(field):
                validated[field] = self.clean_text(validated[field])
        
        return validated