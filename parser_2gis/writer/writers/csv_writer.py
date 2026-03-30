"""Писатель в CSV-таблицу.

Предоставляет класс CSVWriter для записи данных парсинга в CSV формат:
- Базовая запись CSV
- Интеграция с постобработкой (удаление пустых колонок и дубликатов)
- Пакетная обработка для снижения накладных расходов
"""

from __future__ import annotations

import csv
import re
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from pydantic import ValidationError

from parser_2gis.logger import logger
from parser_2gis.utils import report_from_validation_error
from parser_2gis.writer.models import CatalogItem

from .csv_deduplicator import CSVDeduplicator
from .csv_post_processor import CSVPostProcessor
from .file_writer import FileWriter

if TYPE_CHECKING:
    from parser_2gis.writer.models.contact_group import ContactGroup


class CSVWriter(FileWriter):
    """Писатель в CSV-таблицу.

    Предназначен для записи данных парсинга в файлы формата CSV.
    Поддерживает постобработку: удаление пустых колонок и дубликатов.
    """

    @property
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

    @property
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

    @property
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
            **{"point_lat": "Широта", "point_lon": "Долгота", "url": "2GIS URL", "type": "Тип"},
        }

    def _writerow(self, row: Dict[str, Any]) -> None:
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
        except IOError as io_error:
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
        super().__exit__(*exc_info)

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

    def write(self, catalog_doc: Any) -> None:
        """Записывает JSON-документ Catalog Item API в CSV-таблицу.

        Args:
            catalog_doc: JSON-документ Catalog Item API.
        """
        if not self._check_catalog_doc(catalog_doc):
            return

        row = self._extract_raw(catalog_doc)
        if row:
            self._writerow(row)
            self._wrote_count += 1

    def _extract_raw(self, catalog_doc: Any) -> Dict[str, Any]:
        """Извлекает данные из JSON-документа Catalog Item API.

        Args:
            catalog_doc: JSON-документ Catalog Item API.

        Returns:
            Словарь для строки CSV или пустой словарь при ошибке.
        """
        data: Dict[str, Any] = {k: None for k in self._data_mapping.keys()}

        # Проверка структуры документа
        try:
            result = catalog_doc.get("result")
            if not result or "items" not in result:
                logger.error("Некорректная структура документа: отсутствует result.items")
                return {}

            items = result.get("items", [])
            if not items:
                logger.error("Пустой список items в документе")
                return {}

            item = items[0]
        except (KeyError, TypeError, IndexError) as e:
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
        for contact_group in catalog_item.contact_groups:

            def append_contact(
                contact_group: "ContactGroup",
                contact_type: str,
                priority_fields: List[str],
                formatter: Optional[Callable[[str], str]] = None,
            ) -> None:
                """Добавляет контакт в `data`.

                Args:
                    contact_group: Группа контактов.
                    contact_type: Тип контакта (см. `Contact` в `catalog_item.py`)
                    priority_fields: Поля контакта для добавления, сортированные по приоритету
                    formatter: Форматировщик значения поля
                """
                contacts = [x for x in contact_group.contacts if x.type == contact_type]
                for i, contact in enumerate(contacts, 1):
                    contact_value = None

                    for field in priority_fields:
                        if hasattr(contact, field):
                            contact_value = getattr(contact, field)
                            break

                    # Отсутствующие значения контакта - пропускаем
                    if not contact_value:
                        return

                    data_name = f"{contact_type}_{i}"
                    if data_name in data:
                        data[data_name] = formatter(contact_value) if formatter else contact_value

                        # Добавляем комментарий к контакту при наличии
                        if self._options.csv.add_comments and contact.comment:
                            data[data_name] += " (%s)" % contact.comment

            # Интернет-адреса (веб-сайты, соцсети)
            for t in [
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
            ]:
                append_contact(contact_group, t, ["url"])

            # Удаляем параметры из URL WhatsApp
            for field in data:
                if field.startswith("whatsapp") and data[field]:
                    data[field] = data[field].split("?")[0]

            # Текстовые значения (email, skype и т.д.)
            for t in ["email", "skype"]:
                append_contact(contact_group, t, ["value"])

            # Телефоны (поле `value` иногда содержит нерелевантные данные,
            # поэтому предпочитаем парсить поле `text`.
            # Если в контакте нет `text` - используем атрибут `value`)
            append_contact(
                contact_group,
                "phone",
                ["text", "value"],
                formatter=lambda x: re.sub(r"^\+7", "8", re.sub(r"[^0-9+]", "", x)),
            )

        # Режим работы объекта
        if catalog_item.schedule:
            data["schedule"] = catalog_item.schedule.to_str(
                self._options.csv.join_char, self._options.csv.add_comments
            )

        # Рубрики (категории) объекта
        if self._options.csv.add_rubrics:
            data["rubrics"] = self._options.csv.join_char.join(x.name for x in catalog_item.rubrics)

        return data
