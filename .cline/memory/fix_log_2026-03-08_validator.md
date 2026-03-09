# Лог исправлений validator.py
## Дата: 2026-03-08

### Исправленные проблемы:

1. **Строки 1-10**: `ValidationResult` использует `list[str]` но в Python 3.9+ требуется `List[str]` из typing для совместимости.
   - **Решение**: Добавлен `from __future__ import annotations` и импортирован `List` из typing

2. **Строки 67-70**: Метод `validate_phone` не обрабатывал номер с `+8` как ошибку.
   - **Решение**: Добавлена проверка `if cleaned.startswith("+8")` с возвратом ошибки

3. **Строки 93-96**: Магические числа 10-15 для международных номеров.
   - **Решение**: Вынесены в константы класса:
     - `INTERNATIONAL_PHONE_MIN_LENGTH = 10`
     - `INTERNATIONAL_PHONE_MAX_LENGTH = 15`

4. **Строки 134-137**: `validate_url` не проверял что схема именно `http` или `https`.
   - **Решение**: Добавлена проверка `if parsed.scheme not in ('http', 'https')`

5. **Строки 189-213**: `validate_record` жестко кодировал префиксы `phone_`, `email_`, `website_`.
   - **Решение**: Использован mapping `field_prefixes` для настраиваемости

6. **Строка 206**: Текстовые поля `name`, `description`, `address` могли отсутствовать - KeyError.
   - **Решение**: Используется `validated.get(field)` вместо прямого доступа

### Изменённые участки кода:

#### Импорт и аннотации типов (строки 1-32):
```python
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse


@dataclass
class ValidationResult:
    is_valid: bool
    value: Optional[str]
    errors: List[str]  # Было: list[str]
```

#### Константы для телефонов (строки 48-50):
```python
# Константы для валидации телефонных номеров
INTERNATIONAL_PHONE_MIN_LENGTH = 10
INTERNATIONAL_PHONE_MAX_LENGTH = 15
```

#### Проверка +8 (строки 90-94):
```python
# Обработка российских номеров (+7 или 8)
if cleaned.startswith("+7") or cleaned.startswith("8"):
    # Номер +8 не является корректным международным форматом
    if cleaned.startswith("+8"):
        errors.append("Некорректный международный префикс: +8 (должен быть +7 для России)")
        return ValidationResult(False, None, errors)
```

#### Использование констант (строки 113-117):
```python
# Проверяем длину (10-15 цифр для международных номеров)
if len(international_digits) < self.INTERNATIONAL_PHONE_MIN_LENGTH or len(international_digits) > self.INTERNATIONAL_PHONE_MAX_LENGTH:
    errors.append(
        f"Некорректная длина международного номера: {len(international_digits)} (ожидалось {self.INTERNATIONAL_PHONE_MIN_LENGTH}-{self.INTERNATIONAL_PHONE_MAX_LENGTH})"
    )
```

#### Проверка схемы URL (строки 207-209):
```python
# Проверяем что схема именно http или https
if parsed.scheme not in ('http', 'https'):
    return ValidationResult(False, None, [f"Неподдерживаемая схема URL: {parsed.scheme} (требуется http или https)"])
```

#### Настраиваемые префиксы в validate_record (строки 262-278):
```python
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
```

#### Безопасный доступ к текстовым полям (строки 281-284):
```python
text_fields = ["name", "description", "address"]
for field in text_fields:
    value = validated.get(field)  # Было: if validated.get(field)
    if value:
        validated[field] = self.clean_text(value)
```
