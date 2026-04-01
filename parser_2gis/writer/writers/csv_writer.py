"""Писатель в CSV-таблицу.

Предоставляет класс CSVWriter для записи данных парсинга в CSV формат:
- Базовая запись CSV
- Интеграция с постобработкой (удаление пустых колонок и дубликатов)
- Пакетная обработка для снижения накладных расходов
"""

from __future__ import annotations

import csv
import re
from functools import cached_property
from typing import TYPE_CHECKING, Any
from collections.abc import Callable

from pydantic import ValidationError

from parser_2gis.logger import logger
from parser_2gis.utils import report_from_validation_error
from parser_2gis.writer.models import CatalogItem

from .csv_deduplicator import CSVDeduplicator
from .csv_post_processor import CSVPostProcessor
from .file_writer import FileWriter

if TYPE_CHECKING:
    from parser_2gis.writer.models.contact_group import ContactGroup

# Константа для заголовка колонки URL
CSV_URL_HEADER = "2GIS URL"

# D014: Таблица санитизации для CSV данных
_CSV_SANITIZE_TABLE = {
    '"': '""',  # Экранирование кавычек для CSV
    "\n": " ",  # Замена новых строк на пробелы
    "\r": "",  # Удаление carriage return
    "\t": " ",  # Замена табов на пробелы
}


def _sanitize_csv_value(value: str) -> str:
    """D014: Санитизирует значение для CSV.

    Args:
        value: Исходное строковое значение.

    Returns:
        Санитизированное значение безопасное для CSV.

    """
    if not isinstance(value, str):
        return value

    # Экранируем специальные символы CSV
    for char, replacement in _CSV_SANITIZE_TABLE.items():
        value = value.replace(char, replacement)

    return value


def _append_contact(
    data: dict[str, Any],
    contact_group: ContactGroup,
    contact_type: str,
    priority_fields: list[str],
    formatter: Callable[[str], str] | None,
    add_comments: bool,
) -> None:
    """Добавляет контакт в data.

    Args:
        data: Словарь данных для записи в CSV.
        contact_group: Группа контактов.
        contact_type: Тип контакта (см. Contact в catalog_item.py)
        priority_fields: Поля контакта для добавления, сортированные по приоритету
        formatter: Форматировщик значения поля
        add_comments: Добавлять ли комментарии к контактам

    """
    contacts = [x for x in contact_group.contacts if x.type == contact_type]
    for i, contact in enumerate(contacts, 1):
        contact_value = None

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
            data[data_name] += " (%s)" % contact.comment


class CSVWriter(FileWriter):
    """Писатель в CSV-таблицу.

    Предназначен для записи данных парсинга в файлы формата CSV.
    Поддерживает постобработку: удаление пустых колонок и дубликатов.
    """

    @cached_property
    def _type_names(self) -> dict[str, str]:
        """Возвращает отображение типов на русские названия.

        Returns:
            Словарь с маппингом типов: 'parking' -> 'Парковка' и т.д.

        """
        return {
            "parking": "Парковка",
            "street": "Улица",
            "road": "Дорога",
            "crossroad": "Перекрёсток",
            "station": "Остановка",
        }

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
            **{"point_lat": "Широта", "point_lon": "Долгота", "url": CSV_URL_HEADER, "type": "Тип"},
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
        except Exception as general_error:
            # Общая ошибка
            logger.error("Общая ошибка во время записи строки: %s", general_error)
            raise

    def __enter__(self) -> CSVWriter:
        super().__enter__()
        self._writer = csv.DictWriter(self._file, self._data_mapping.keys())
        self._writer.writerow(self._data_mapping)  # Запись заголовка
        self._wrote_count = 0
        return self

    def __exit__(self, *exc_info: Any) -> None:
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
            except Exception as e:
                logger.error("Ошибка при удалении пустых колонок: %s", e)

        # Постобработка: удаление дубликатов
        if self._options.csv.remove_duplicates:
            try:
                logger.info("Удаление повторяющихся записей CSV.")
                deduplicator = CSVDeduplicator(
                    file_path=self._file_path, encoding=self._options.encoding
                )
                deduplicator.remove_duplicates()
            except Exception as e:
                logger.error("Ошибка при удалении дубликатов: %s", e)

        # Теперь закрываем файл через super().__exit__()
        super().__exit__(*exc_info)

    def write(self, catalog_doc: Any) -> None:
        """Записывает JSON-документ Catalog Item API в CSV-таблицу.

        Args:
            catalog_doc: JSON-документ Catalog Item API.

        Raises:
            TypeError: Если catalog_doc не является словарём.
            ValueError: Если catalog_doc имеет некорректную структуру.

        """
        # D007: Валидация catalog_doc перед записью
        if catalog_doc is None:
            raise TypeError("catalog_doc не может быть None")
        if not isinstance(catalog_doc, dict):
            raise TypeError(
                f"catalog_doc должен быть словарём, получен {type(catalog_doc).__name__}"
            )

        # Проверка на path traversal в данных
        if "result" in catalog_doc and isinstance(catalog_doc.get("result"), dict):
            result = catalog_doc["result"]
            if "items" in result and isinstance(result.get("items"), list):
                for item in result["items"]:
                    if isinstance(item, dict):
                        # Проверка строковых полей на опасные конструкции
                        for key, value in item.items():
                            if isinstance(value, str):
                                # Проверка на потенциальные XSS атаки
                                if "<script" in value.lower() or "javascript:" in value.lower():
                                    logger.warning(
                                        "Обнаружена подозрительная конструкция в поле %s: %s",
                                        key,
                                        value[:100],
                                    )

        if not self._check_catalog_doc(catalog_doc):
            return

        row = self._extract_raw(catalog_doc)
        if row:
            self._writerow(row)
            self._wrote_count += 1

    def write_batch(self, catalog_docs: list[Any]) -> int:
        """Пакетная запись JSON-документов в CSV.

        C017: Оптимизация через пакетную обработку для снижения накладных расходов.

        Args:
            catalog_docs: Список JSON-документов Catalog Item API.

        Returns:
            Количество успешно записанных документов.

        """
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
                self._writerow(row)
                written_count += 1
            except (OSError, csv.Error, UnicodeError) as write_error:
                logger.error("Ошибка при пакетной записи строки: %s", write_error)
                continue

        self._wrote_count += written_count
        return written_count

    def _extract_raw(self, catalog_doc: Any) -> dict[str, Any]:
        """Извлекает данные из JSON-документа Catalog Item API.

        Args:
            catalog_doc: JSON-документ Catalog Item API.

        Returns:
            Словарь для строки CSV или пустой словарь при ошибке.

        """
        data: dict[str, Any] = {}

        # Проверка структуры документа
        try:
            if not isinstance(catalog_doc, dict):
                logger.error("Некорректная структура документа: не dict")
                return {}

            result = catalog_doc.get("result")
            if not result or "items" not in result:
                logger.error("Некорректная структура документа: отсутствует result.items")
                return {}

            items = result.get("items", [])
            if not items:
                logger.error("Пустой список items в документе")
                return {}

            item = items[0]
        except (KeyError, TypeError, IndexError, AttributeError) as e:
            logger.error("Ошибка при извлечении элемента из документа: %s", e)
            return {}

        try:
            catalog_item = CatalogItem(**item)
        except ValidationError as e:
            errors = []
            errors_report = report_from_validation_error(e, item)
            for path, description in errors_report.items():
                arg = description["invalid_value"]
                error_msg = description["error_message"]
                errors.append(f"[*] Поле: {path}, значение: {arg}, ошибка: {error_msg}")

            # Безопасность: не раскрываем полную структуру документа API
            item_type = item.get("type", "неизвестно")
            item_id = item.get("id", "неизвестно")
            error_str = "Ошибка парсинга:\n" + "\n".join(errors)
            error_str += f"\nДокумент каталога (тип: {item_type}, ID: {item_id})"
            logger.error(error_str)

            # Возвращаем пустой словарь для индикации ошибки
            return {}

        # Наименование и описание объекта
        if catalog_item.name_ex:
            data["name"] = catalog_item.name_ex.primary
            data["description"] = catalog_item.name_ex.extension
        elif catalog_item.name:
            data["name"] = catalog_item.name
        elif catalog_item.type in self._type_names:
            data["name"] = self._type_names[catalog_item.type]

        # Тип объекта
        data["type"] = catalog_item.type

        # Адрес объекта
        data["address"] = catalog_item.address_name

        # Рейтинг и отзывы
        if catalog_item.reviews:
            data["general_rating"] = catalog_item.reviews.general_rating
            data["general_review_count"] = catalog_item.reviews.general_review_count

        # Географические координаты объекта
        if catalog_item.point:
            data["point_lat"] = catalog_item.point.lat  # Широта объекта
            data["point_lon"] = catalog_item.point.lon  # Долгота объекта

        # Дополнительный комментарий к адресу
        data["address_comment"] = catalog_item.address_comment

        # Почтовый индекс
        if catalog_item.address:
            data["postcode"] = catalog_item.address.postcode

        # Часовой пояс объекта
        if catalog_item.timezone is not None:
            data["timezone"] = catalog_item.timezone

        # Административно-территориальные детали (страна, регион, округ и т.д.)
        for div in catalog_item.adm_div:
            for t in ("country", "region", "district_area", "city", "district", "living_area"):
                if div.type == t:
                    data[t] = div.name

        # URL объекта на сайте 2GIS
        data["url"] = catalog_item.url

        # Контактные данные (телефоны, email, сайты, соцсети)
        # C011: Оптимизация — предварительное вычисление списков для снижения итераций
        contact_groups = catalog_item.contact_groups
        internet_contacts = [
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
        ]
        text_contacts = ["email", "skype"]

        for contact_group in contact_groups:
            # Интернет-адреса (веб-сайты, соцсети)
            for t in internet_contacts:
                _append_contact(
                    data, contact_group, t, ["url"], None, self._options.csv.add_comments
                )

            # Удаляем параметры из URL WhatsApp
            for field, value in data.items():
                if field.startswith("whatsapp") and value:
                    data[field] = value.split("?")[0]

            # Текстовые значения (email, skype и т.д.)
            for t in text_contacts:
                _append_contact(
                    data, contact_group, t, ["value"], None, self._options.csv.add_comments
                )

            # Телефоны (поле `value` иногда содержит нерелевантные данные,
            # поэтому предпочитаем парсить поле `text`.
            # Если в контакте нет `text` - используем атрибут `value`)
            _append_contact(
                data,
                contact_group,
                "phone",
                ["text", "value"],
                lambda x: re.sub(r"^\+7", "8", re.sub(r"[^0-9+]", "", x)),
                self._options.csv.add_comments,
            )

        # Режим работы объекта
        if catalog_item.schedule:
            data["schedule"] = catalog_item.schedule.to_str(
                self._options.csv.join_char, self._options.csv.add_comments
            )

        # Рубрики (категории) объекта
        if self._options.csv.add_rubrics:
            data["rubrics"] = self._options.csv.join_char.join(x.name for x in catalog_item.rubrics)

        # D014: Санитизация всех строковых значений перед возвратом
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = _sanitize_csv_value(value)

        return data
