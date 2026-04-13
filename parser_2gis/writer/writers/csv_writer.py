"""Писатель в CSV-таблицу.

Предоставляет класс CSVWriter для записи данных парсинга в CSV формат:
- Базовая запись CSV
- Интеграция с постобработкой (удаление пустых колонок и дубликатов)
- Пакетная обработка для снижения накладных расходов

ISSUE-005: Использует стратегии форматирования для соблюдения OCP.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Callable
from functools import cached_property
from typing import TYPE_CHECKING, Any, TypedDict

from pydantic import ValidationError

from parser_2gis.logger import logger
from parser_2gis.utils import report_from_validation_error
from parser_2gis.writer.models import CatalogItem

from .csv_deduplicator import CSVDeduplicator
from .csv_formatter import ContactFormatter, PhoneFormatter, SanitizeFormatter, TypeFormatter
from .csv_post_processor import CSVPostProcessor
from .file_writer import FileWriter

if TYPE_CHECKING:
    from parser_2gis.writer.models.contact_group import ContactGroup
    from parser_2gis.writer.options import WriterOptions

# =============================================================================
# TYPE ALIASES AND TYPEDDICT
# =============================================================================


class CSVRowData(TypedDict, total=False):
    """TypedDict для строки CSV данных.

    P1-4: Замена dict[str, Any] на TypedDict для лучшей типизации.
    """

    name: str
    description: str
    rubrics: str
    address: str
    address_comment: str
    postcode: str
    living_area: str
    district: str
    city: str
    district_area: str
    region: str
    country: str
    schedule: str
    timezone: str
    general_rating: float
    general_review_count: int
    point_lat: float
    point_lon: float
    url: str
    type: str
    # Динамические поля для контактов
    phone_1: str
    phone_2: str
    phone_3: str
    email_1: str
    email_2: str
    website_1: str
    website_2: str
    # И другие динамические поля...


# Константа для заголовка колонки URL
CSV_URL_HEADER = "2GIS URL"


def _append_contact(
    data: dict[str, Any],
    contact_group: ContactGroup,
    contact_type: str,
    priority_fields: list[str],
    formatter: Callable[[str], str] | None,
    *,
    add_comments: bool,
) -> None:
    """Добавляет контакт в data.

    ISSUE-044: Добавлены type hints.

    Args:
        data: Словарь данных для записи в CSV.
        contact_group: Группа контактов.
        contact_type: Тип контакта (см. Contact в catalog_item.py)
        priority_fields: Поля контакта для добавления, сортированные по приоритету
        formatter: Форматировщик значения поля
        add_comments: Добавлять ли комментарии к контактам

    Raises:
        AttributeError: При отсутствии атрибута у контакта.

    """
    contacts = [x for x in contact_group.contacts if x.type == contact_type]
    for i, contact in enumerate(contacts, 1):
        contact_value: str | None = None

        for field in priority_fields:
            if hasattr(contact, field):
                contact_value = getattr(contact, field)
                break

        if not contact_value:
            continue

        data_name = f"{contact_type}_{i}"
        # Добавляем контакт в data (проверка на существование ключа не нужна)
        data[data_name] = formatter(contact_value) if formatter else contact_value
        if add_comments and contact.comment:
            data[data_name] += f" ({contact.comment})"


class CSVWriter(FileWriter):
    """Писатель в CSV-таблицу.

    Предназначен для записи данных парсинга в файлы формата CSV.
    Поддерживает постобработку: удаление пустых колонок и дубликатов.

    ISSUE-005: Использует стратегии форматирования для соблюдения OCP.

    Attributes:
        _phone_formatter: Форматировщик телефонов.
        _sanitize_formatter: Форматировщик санитизации.
        _type_formatter: Форматировщик типов.
        _contact_formatter: Форматировщик контактов.

    """

    def __init__(self, file_path: str, options: WriterOptions) -> None:
        """Инициализирует CSVWriter.

        Args:
            file_path: Путь к выходному файлу.
            options: Опции писателя.

        """
        super().__init__(file_path, options)
        # ISSUE-005: Инициализация стратегий форматирования
        self._phone_formatter = PhoneFormatter()
        self._sanitize_formatter = SanitizeFormatter()
        self._type_formatter = TypeFormatter()
        self._contact_formatter = ContactFormatter()

    @cached_property
    def _type_names(self) -> dict[str, str]:
        """Возвращает отображение типов на русские названия.

        P0-14: Упрощено — возвращаем готовый словарь без делегирования format().

        Returns:
            Словарь с маппингом типов: 'parking' -> 'Парковка' и т.д.

        """
        # P0-14: Возвращаем готовый словарь напрямую из TypeFormatter
        return self._type_formatter.get_type_mapping()

    @cached_property
    def _complex_mapping(self) -> dict[str, Any]:
        """Возвращает отображение сложных полей с несколькими значениями.

        Сложное отображение означает, что его содержимое может содержать несколько сущностей,
        связанных пользовательскими настройками.
        Например: phone -> phone_1, phone_2, ..., phone_n

        Returns:
            Словарь с маппингом полей: 'phone' -> 'Телефон' и т.д.

        """
        # Сложное отображение означает, что его содержимое может содержать несколько сущностей,
        # связанных пользовательскими настройками.
        # Например: phone -> phone_1, phone_2, ..., phone_n
        return {
            "phone": "Телефон",
            "email": "E-mail",
            "website": "Веб-сайт",
            "instagram": "Instagram",
            "twitter": "Twitter",
            "facebook": "Facebook",
            "vkontakte": "ВКонтакте",
            "whatsapp": "WhatsApp",
            "viber": "Viber",
            "telegram": "Telegram",
            "youtube": "YouTube",
            "skype": "Skype",
        }

    @cached_property
    def _data_mapping(self) -> dict[str, Any]:
        """Возвращает полное отображение данных для CSV колонок.

        NOTE: cached_property не инвалидируется при изменении _options.csv.columns_per_entity.
        Если настройка меняется после первого обращения к свойству, кэш не будет обновлён.

        Формирует маппинг между полями данных и названиями колонок в CSV.
        Включает сложные поля (телефоны, email и т.д.) с учётом настройки
        columns_per_entity.

        Returns:
            Словарь с маппингом всех полей для CSV выгрузки.

        """
        data_mapping = {
            "name": "Наименование",
            "description": "Описание",
            "rubrics": "Рубрики",
            "address": "Адрес",
            "address_comment": "Комментарий к адресу",
            "postcode": "Почтовый индекс",
            "living_area": "Микрорайон",
            "district": "Район",
            "city": "Город",
            "district_area": "Округ",
            "region": "Регион",
            "country": "Страна",
            "schedule": "Часы работы",
            "timezone": "Часовой пояс",
            "general_rating": "Рейтинг",
            "general_review_count": "Количество отзывов",
        }

        # Расширяем сложное отображение
        for k, v in self._complex_mapping.items():
            for n in range(1, self._options.csv.columns_per_entity + 1):
                data_mapping[f"{k}_{n}"] = f"{v} {n}"

        if not self._options.csv.add_rubrics:
            data_mapping.pop("rubrics", None)

        return {
            **data_mapping,
            "point_lat": "Широта",
            "point_lon": "Долгота",
            "url": CSV_URL_HEADER,
            "type": "Тип",
        }

    def _writerow(self, row: dict[str, Any]) -> None:
        """Записывает `row` в CSV.

        Args:
            row: Словарь с данными для записи.

        Raises:
            csv.Error: При ошибке записи CSV.
            IOError: При ошибке ввода-вывода.
            UnicodeError: При ошибке кодировки.

        """
        if self._options.verbose:
            logger.info("Парсинг [%d] > %s", self._wrote_count + 1, row.get("name", "N/A"))

        try:
            self._writer.writerow(row)
        except csv.Error as csv_error:
            # Ошибка формата CSV (некорректные данные, экранирование и т.д.)
            logger.error("Ошибка формата CSV при записи строки: %s", csv_error)
            raise
        except OSError as io_error:
            # Ошибка ввода-вывода (диск заполнен, нет прав и т.д.)
            logger.error("Ошибка ввода-вывода при записи строки: %s", io_error)
            raise
        except UnicodeError as unicode_error:
            # Ошибка кодировки (некорректные символы Unicode)
            logger.error("Ошибка кодировки при записи строки: %s", unicode_error)
            raise

    def __enter__(self) -> CSVWriter:
        """Входит в контекстный менеджер, инициализируя CSV writer.

        Записывает заголовок CSV файла и сбрасывает счётчик записей.

        Returns:
            Экземпляр CSVWriter для использования в блоке with.

        """
        super().__enter__()
        self._writer = csv.DictWriter(self._file, self._data_mapping.keys())
        self._writer.writerow(self._data_mapping)  # Запись заголовка
        self._wrote_count = 0
        return self

    def __exit__(self, *exc_info: Any) -> None:  # type: ignore[override]
        """Выходит из контекстного менеджера, выполняя постобработку и закрытие.

        Выполняет:
        1. Flush всех данных на диск
        2. Удаление пустых колонок (если включено в опциях)
        3. Удаление дубликатов (если включено в опциях)
        4. Закрытие файла

        Args:
            *exc_info: Информация об исключении (exc_type, exc_val, exc_tb).

        """
        # H011: Выполняем постобработку ДО закрытия файла
        # Постобработка требует доступа к открытому файлу

        # Сначала flush для записи всех данных на диск
        if hasattr(self, "_file") and self._file is not None:
            try:
                self._file.flush()
            except OSError as flush_error:
                logger.error("Ошибка при flush файла: %s", flush_error)

        # Постобработка: удаление пустых колонок
        if self._options.csv.remove_empty_columns:
            try:
                logger.info("Удаление пустых колонок CSV.")
                post_processor = CSVPostProcessor(
                    file_path=self._file_path,
                    data_mapping=self._data_mapping,
                    complex_mapping=self._complex_mapping,
                    encoding=self._options.encoding,
                )
                post_processor.remove_empty_columns()
            except (OSError, csv.Error, RuntimeError) as e:
                logger.error("Ошибка при удалении пустых колонок: %s", e)
                logger.warning(
                    "Файл %s может содержать пустые колонки. "
                    "Рекомендуется проверить качество данных.",
                    self._file_path,
                )

        # Постобработка: удаление дубликатов
        if self._options.csv.remove_duplicates:
            try:
                logger.info("Удаление повторяющихся записей CSV.")
                deduplicator = CSVDeduplicator(
                    file_path=self._file_path,
                    encoding=self._options.encoding,
                )
                deduplicator.remove_duplicates()
            except (OSError, RuntimeError) as e:
                logger.error("Ошибка при удалении дубликатов: %s", e)
                logger.warning(
                    "Файл %s может содержать дубликаты. Рекомендуется проверить качество данных.",
                    self._file_path,
                )

        # ИСПРАВЛЕНИЕ #10: Гарантированное закрытие файла через finally
        # чтобы файл закрывался даже при ошибке постобработки
        try:
            super().__exit__(*exc_info)
        except (OSError, RuntimeError) as close_error:
            logger.error("Ошибка при закрытии файла: %s", close_error)

    def write(self, records: dict[str, Any]) -> None:  # type: ignore[override]
        """Записывает JSON-документ Catalog Item API в CSV-таблицу.

        Args:
            records: JSON-документ Catalog Item API.

        Raises:
            TypeError: Если records не является словарём.
            ValueError: Если records имеет некорректную структуру.

        """
        # D007: Валидация records перед записью
        if records is None:
            msg = "records не может быть None"
            raise TypeError(msg)
        if not isinstance(records, dict):
            msg = f"records должен быть словарём, получен {type(records).__name__}"
            raise TypeError(msg)

        # Проверка на path traversal в данных
        if "result" in records and isinstance(records.get("result"), dict):
            result = records["result"]
            if "items" in result and isinstance(result.get("items"), list):
                for item in result["items"]:
                    if isinstance(item, dict):
                        # Проверка строковых полей на опасные конструкции
                        for key, value in item.items():
                            # Проверка на потенциальные XSS атаки (regex для обходных конструкций)
                            if isinstance(value, str) and re.search(
                                r"<\s*script|javascript\s*:",
                                value,
                                re.IGNORECASE,
                            ):
                                logger.warning(
                                    "Обнаружена подозрительная конструкция в поле %s: %s",
                                    key,
                                    value[:100],
                                )
                                msg = f"Обнаружена потенциальная XSS атака в поле {key}"
                                raise ValueError(msg)

        if not self._check_catalog_doc(records):
            return

        row = self._extract_raw(records)
        if row:
            self._writerow(row)  # type: ignore[arg-type]
            self._wrote_count += 1

    def write_batch(self, catalog_docs: list[Any]) -> int:
        """Пакетная запись JSON-документов в CSV.

        C017: Оптимизация через пакетную обработку для снижения накладных расходов.
        ISSUE-166: Добавлена валидация входного списка на пустоту.

        Args:
            catalog_docs: Список JSON-документов Catalog Item API.

        Returns:
            Количество успешно записанных документов.

        """
        # ISSUE-166: Валидация пустого списка
        if not catalog_docs:
            logger.debug("write_batch: пустой список документов, пропускаем")
            return 0

        written_count = 0
        batch_rows = []

        for doc in catalog_docs:
            if not self._check_catalog_doc(doc):
                continue

            row = self._extract_raw(doc)
            if row:
                batch_rows.append(row)

        # Пакетная запись всех строк
        for row in batch_rows:
            try:
                self._writerow(row)  # type: ignore[arg-type]
                written_count += 1
            except (OSError, csv.Error, UnicodeError) as write_error:
                logger.error("Ошибка при пакетной записи строки: %s", write_error)
                continue

        self._wrote_count += written_count
        return written_count

    def _validate_and_get_item(self, catalog_doc: dict[str, Any]) -> dict[str, Any] | None:
        """Валидирует структуру документа и возвращает первый item.

        Args:
            catalog_doc: JSON-документ Catalog Item API.

        Returns:
            Словарь item или None при ошибке.
        """
        if not isinstance(catalog_doc, dict):
            logger.error("Некорректная структура документа: не dict")
            return None

        result = catalog_doc.get("result")
        if not result or not isinstance(result, dict):
            logger.error("Некорректная структура документа: отсутствует result.items")
            return None

        items = result.get("items", [])
        if not items:
            logger.error("Пустой список items в документе")
            return None

        return items[0]

    def _parse_catalog_item(self, item: dict[str, Any]) -> CatalogItem | None:
        """Создаёт CatalogItem из словаря с обработкой ошибок валидации.

        Args:
            item: Словарь данных элемента.

        Returns:
            CatalogItem или None при ошибке.
        """
        try:
            return CatalogItem(**item)
        except ValidationError as e:
            errors = []
            errors_report = report_from_validation_error(e, item)
            for path, description in errors_report.items():
                arg = description["invalid_value"]
                error_msg = description["error_message"]
                errors.append(f"[*] Поле: {path}, значение: {arg}, ошибка: {error_msg}")

            item_type = item.get("type", "неизвестно")
            item_id = item.get("id", "неизвестно")
            error_str = "Ошибка парсинга:\n" + "\n".join(errors)
            error_str += f"\nДокумент каталога (тип: {item_type}, ID: {item_id})"
            logger.error(error_str)
            return None

    def _extract_basic_fields(self, data: CSVRowData, catalog_item: CatalogItem) -> None:
        """Извлекает базовые поля: name, type, address, rating, coordinates.

        Args:
            data: Словарь для заполнения.
            catalog_item: Распарсенный элемент каталога.
        """
        if catalog_item.name_ex:
            data["name"] = catalog_item.name_ex.primary
            data["description"] = catalog_item.name_ex.extension  # type: ignore[typeddict-item]
        elif catalog_item.name:
            data["name"] = catalog_item.name
        elif catalog_item.type in self._type_names:
            data["name"] = self._type_names[catalog_item.type]

        data["type"] = catalog_item.type
        data["address"] = catalog_item.address_name  # type: ignore[typeddict-item]

        if catalog_item.reviews:
            data["general_rating"] = catalog_item.reviews.general_rating  # type: ignore[typeddict-item]
            data["general_review_count"] = catalog_item.reviews.general_review_count  # type: ignore[typeddict-item]

        if catalog_item.point:
            data["point_lat"] = catalog_item.point.lat
            data["point_lon"] = catalog_item.point.lon

        data["address_comment"] = catalog_item.address_comment  # type: ignore[typeddict-item]

    def _extract_administrative_fields(self, data: CSVRowData, catalog_item: CatalogItem) -> None:
        """Извлекает административные поля: postcode, timezone, adm_div.

        Args:
            data: Словарь для заполнения.
            catalog_item: Распарсенный элемент каталога.
        """
        if catalog_item.address:
            data["postcode"] = catalog_item.address.postcode  # type: ignore[typeddict-item]

        if catalog_item.timezone is not None:
            data["timezone"] = catalog_item.timezone

        for div in catalog_item.adm_div:
            for t in ("country", "region", "district_area", "city", "district", "living_area"):
                if div.type == t:
                    data[t] = div.name

    def _extract_contact_fields(self, data: CSVRowData, catalog_item: CatalogItem) -> None:
        """Извлекает контактные данные: websites, phones, email, соцсети.

        Args:
            data: Словарь для заполнения.
            catalog_item: Распарсенный элемент каталога.
        """
        contact_groups = catalog_item.contact_groups
        add_comments = self._options.csv.add_comments
        url_fields = (
            "website",
            "vkontakte",
            "whatsapp",
            "viber",
            "telegram",
            "instagram",
            "facebook",
            "twitter",
            "youtube",
            "skype",
        )
        text_fields = ("email", "skype")

        for contact_group in contact_groups:
            for t in url_fields:
                _append_contact(
                    data,  # type: ignore[arg-type]
                    contact_group,
                    t,
                    ["url"],
                    None,
                    add_comments=add_comments,
                )

            for field, value in data.items():
                if field.startswith("whatsapp") and value:
                    data[field] = value.split("?")[0]  # type: ignore[literal-required, attr-defined]

            for t in text_fields:
                _append_contact(
                    data,  # type: ignore[arg-type]
                    contact_group,
                    t,
                    ["value"],
                    None,
                    add_comments=add_comments,
                )

            _append_contact(
                data,  # type: ignore[arg-type]
                contact_group,
                "phone",
                ["text", "value"],
                self._phone_formatter.format,
                add_comments=add_comments,
            )

    def _extract_raw(self, catalog_doc: dict[str, Any]) -> CSVRowData:
        """Извлекает данные из JSON-документа Catalog Item API.

        P1-4, P1-14: Оптимизировано с использованием TypedDict и локальных переменных.
        ISSUE-167: Закэшированы обращения к catalog_doc через локальные переменные.

        Args:
            catalog_doc: JSON-документ Catalog Item API.

        Returns:
            Словарь для строки CSV или пустой словарь при ошибке.

        """
        data: CSVRowData = {}

        item = self._validate_and_get_item(catalog_doc)
        if item is None:
            return {}

        catalog_item = self._parse_catalog_item(item)
        if catalog_item is None:
            return {}

        self._extract_basic_fields(data, catalog_item)
        self._extract_administrative_fields(data, catalog_item)

        data["url"] = catalog_item.url

        self._extract_contact_fields(data, catalog_item)

        if catalog_item.schedule:
            data["schedule"] = catalog_item.schedule.to_str(  # type: ignore[misc]
                self._options.csv.join_char,
                self._options.csv.add_comments,
            )

        if self._options.csv.add_rubrics:
            data["rubrics"] = self._options.csv.join_char.join(x.name for x in catalog_item.rubrics)

        # D014: Санитизация всех строковых значений перед возвратом
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = self._sanitize_formatter.format(value)  # type: ignore[literal-required]

        return data
