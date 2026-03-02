from __future__ import annotations

import csv
import os
import re
import shutil
from contextlib import ExitStack
from typing import Any, Callable

from pydantic import ValidationError

from ...common import report_from_validation_error
from ...logger import logger
from ..models import CatalogItem
from .file_writer import FileWriter


class CSVWriter(FileWriter):
    """Писатель в CSV-таблицу."""
    @property
    def _type_names(self) -> dict[str, str]:
        return {
            'parking': 'Парковка',
            'street': 'Улица',
            'road': 'Дорога',
            'crossroad': 'Перекрёсток',
            'station': 'Остановка',
        }

    @property
    def _complex_mapping(self) -> dict[str, Any]:
        # Сложное маппирование означает, что его содержимое может содержать несколько сущностей,
        # связанных пользовательскими настройками.
        # Например: phone -> phone_1, phone_2, ..., phone_n
        return {
            'phone': 'Телефон', 'email': 'E-mail', 'website': 'Веб-сайт', 'instagram': 'Instagram',
            'twitter': 'Twitter', 'facebook': 'Facebook', 'vkontakte': 'ВКонтакте', 'whatsapp': 'WhatsApp',
            'viber': 'Viber', 'telegram': 'Telegram', 'youtube': 'YouTube', 'skype': 'Skype'
        }

    @property
    def _data_mapping(self) -> dict[str, Any]:
        data_mapping = {
            'name': 'Наименование', 'description': 'Описание', 'rubrics': 'Рубрики',
            'address': 'Адрес', 'address_comment': 'Комментарий к адресу',
            'postcode': 'Почтовый индекс', 'living_area': 'Микрорайон', 'district': 'Район', 'city': 'Город',
            'district_area': 'Округ', 'region': 'Регион', 'country': 'Страна', 'schedule': 'Часы работы',
            'timezone': 'Часовой пояс', 'general_rating': 'Рейтинг', 'general_review_count': 'Количество отзывов'
        }

        # Расширяем сложное маппирование
        for k, v in self._complex_mapping.items():
            for n in range(1, self._options.csv.columns_per_entity + 1):
                data_mapping[f'{k}_{n}'] = f'{v} {n}'

        if not self._options.csv.add_rubrics:
            data_mapping.pop('rubrics', None)

        return {
            **data_mapping,
            **{
                'point_lat': 'Широта',
                'point_lon': 'Долгота',
                'url': '2GIS URL',
                'type': 'Тип',
            }
        }

    def _writerow(self, row: dict[str, Any]) -> None:
        """Записывает `row` в CSV."""
        if self._options.verbose:
            logger.info('Парсинг [%d] > %s', self._wrote_count + 1, row['name'])

        try:
            self._writer.writerow(row)
        except Exception as e:
            logger.error('Ошибка во время записи: %s', e)

    def __enter__(self) -> CSVWriter:
        super().__enter__()
        self._writer = csv.DictWriter(self._file, self._data_mapping.keys())
        self._writer.writerow(self._data_mapping)  # Запись заголовка
        self._wrote_count = 0
        return self

    def __exit__(self, *exc_info) -> None:
        super().__exit__(*exc_info)
        if self._options.csv.remove_empty_columns:
            logger.info('Удаление пустых колонок CSV.')
            self._remove_empty_columns()
        if self._options.csv.remove_duplicates:
            logger.info('Удаление повторяющихся записей CSV.')
            self._remove_duplicates()

    def _remove_empty_columns(self) -> None:
        """Постобработка: Удаление пустых колонок."""
        complex_columns = self._complex_mapping.keys()
        complex_columns_count = {c: 0 for c in self._data_mapping.keys() if
                                 re.match('|'.join(fr'^{x}_\d+$' for x in complex_columns), c)}

        # Поиск пустых колонок
        with self._open_file(self._file_path, 'r') as f_csv:
            csv_reader = csv.DictReader(f_csv, self._data_mapping.keys())  # type: ignore
            next(csv_reader, None)  # Пропуск заголовка
            for row in csv.DictReader(f_csv, self._data_mapping.keys()):  # type: ignore
                for column_name in complex_columns_count.keys():
                    if row[column_name] != '':
                        complex_columns_count[column_name] += 1

        # Генерация нового маппинга данных
        new_data_mapping: dict[str, Any] = {}
        for k, v in self._data_mapping.items():
            if k in complex_columns_count:
                if complex_columns_count[k] > 0:
                    new_data_mapping[k] = v
            else:
                new_data_mapping[k] = v

        # Переименование одиночной сложной колонки - удаление суффиксов с цифрами
        for column in complex_columns:
            if f'{column}_1' in new_data_mapping and f'{column}_2' not in new_data_mapping:
                new_data_mapping[f'{column}_1'] = re.sub(r'\s+\d+$', '', new_data_mapping[f'{column}_1'])

        # Заполнение нового csv
        tmp_csv_name = os.path.splitext(self._file_path)[0] + '.removed-columns.csv'

        # Используем ExitStack для гарантии закрытия всех файлов даже при exception
        with ExitStack() as stack:
            f_tmp_csv = stack.enter_context(self._open_file(tmp_csv_name, 'w'))
            f_csv = stack.enter_context(self._open_file(self._file_path, 'r'))
            csv_writer = csv.DictWriter(f_tmp_csv, new_data_mapping.keys())  # type: ignore
            csv_reader = csv.DictReader(f_csv, self._data_mapping.keys())  # type: ignore
            csv_writer.writerow(new_data_mapping)  # Запись нового заголовка
            next(csv_reader, None)  # Пропуск заголовка

            for row in csv_reader:
                new_row = {k: v for k, v in row.items() if k in new_data_mapping}
                csv_writer.writerow(new_row)

        # Замена оригинального файла новым
        shutil.move(tmp_csv_name, self._file_path)

    def _remove_duplicates(self) -> None:
        """Постобработка: Удаление дубликатов."""
        tmp_csv_name = os.path.splitext(self._file_path)[0] + '.deduplicated.csv'
        
        # Используем ExitStack для гарантии закрытия файлов
        with ExitStack() as stack:
            f_tmp_csv = stack.enter_context(self._open_file(tmp_csv_name, 'w'))
            f_csv = stack.enter_context(self._open_file(self._file_path, 'r'))
            seen_records = set()
            for line in f_csv:
                # Нормализуем строку: удаляем завершающие пробелы и newlines для корректного сравнения
                normalized_line = line.rstrip('\r\n')
                if normalized_line in seen_records:
                    continue

                seen_records.add(normalized_line)
                f_tmp_csv.write(line)

        # Замена оригинального файла новым
        shutil.move(tmp_csv_name, self._file_path)

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

    def _extract_raw(self, catalog_doc: Any) -> dict[str, Any]:
        """Извлекает данные из JSON-документа Catalog Item API.

        Args:
            catalog_doc: JSON-документ Catalog Item API.

        Returns:
            Словарь для строки CSV.
        """
        data: dict[str, Any] = {k: None for k in self._data_mapping.keys()}

        item = catalog_doc['result']['items'][0]

        try:
            catalog_item = CatalogItem(**item)
        except ValidationError as e:
            errors = []
            errors_report = report_from_validation_error(e, item)
            for path, description in errors_report.items():
                arg = description['invalid_value']
                error_msg = description['error_message']
                errors.append(f'[*] Поле: {path}, значение: {arg}, ошибка: {error_msg}')

            # Безопасность: не раскрываем полную структуру документа API
            error_str = 'Ошибка парсинга:\n' + '\n'.join(errors)
            error_str += f'\nДокумент каталога (тип: {item.get("type", "неизвестно")}, ID: {item.get("id", "неизвестно")})'
            logger.error(error_str)

            return {}

        # Наименование и описание объекта
        if catalog_item.name_ex:
            data['name'] = catalog_item.name_ex.primary
            data['description'] = catalog_item.name_ex.extension
        elif catalog_item.name:
            data['name'] = catalog_item.name
        elif catalog_item.type in self._type_names:
            data['name'] = self._type_names[catalog_item.type]

        # Тип объекта
        data['type'] = catalog_item.type

        # Адрес объекта
        data['address'] = catalog_item.address_name

        # Рейтинг и отзывы
        if catalog_item.reviews:
            data['general_rating'] = catalog_item.reviews.general_rating
            data['general_review_count'] = catalog_item.reviews.general_review_count

        # Географические координаты объекта
        if catalog_item.point:
            data['point_lat'] = catalog_item.point.lat  # Широта объекта
            data['point_lon'] = catalog_item.point.lon  # Долгота объекта

        # Дополнительный комментарий к адресу
        data['address_comment'] = catalog_item.address_comment

        # Почтовый индекс
        if catalog_item.address:
            data['postcode'] = catalog_item.address.postcode

        # Часовой пояс объекта
        if catalog_item.timezone is not None:
            data['timezone'] = catalog_item.timezone

        # Административно-территориальные детали (страна, регион, округ и т.д.)
        for div in catalog_item.adm_div:
            for t in ('country', 'region', 'district_area', 'city', 'district', 'living_area'):
                if div.type == t:
                    data[t] = div.name

        # URL объекта на сайте 2GIS
        data['url'] = catalog_item.url

        # Контактные данные (телефоны, email, сайты, соцсети)
        for contact_group in catalog_item.contact_groups:
            def append_contact(contact_type: str, priority_fields: list[str],
                               formatter: Callable[[str], str] | None = None) -> None:
                """Добавляет контакт в `data`.

                Args:
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

                    data_name = f'{contact_type}_{i}'
                    if data_name in data:
                        data[data_name] = formatter(contact_value) if formatter else contact_value

                        # Добавляем комментарий к контакту при наличии
                        if self._options.csv.add_comments and contact.comment:
                            data[data_name] += ' (%s)' % contact.comment

            # Интернет-адреса (веб-сайты, соцсети)
            for t in ['website', 'vkontakte', 'whatsapp', 'viber', 'telegram',
                      'instagram', 'facebook', 'twitter', 'youtube', 'skype']:
                append_contact(t, ['url'])

            # Удаляем параметры из URL WhatsApp
            for field in data:
                if field.startswith('whatsapp') and data[field]:
                    data[field] = data[field].split('?')[0]

            # Текстовые значения (email, skype и т.д.)
            for t in ['email', 'skype']:
                append_contact(t, ['value'])

            # Телефоны (поле `value` иногда содержит нерелевантные данные,
            # поэтому предпочитаем парсить поле `text`.
            # Если в контакте нет `text` - используем атрибут `value`)
            append_contact('phone', ['text', 'value'],
                           formatter=lambda x: re.sub(r'^\+7', '8', re.sub(r'[^0-9+]', '', x)))

        # Режим работы объекта
        if catalog_item.schedule:
            data['schedule'] = catalog_item.schedule.to_str(self._options.csv.join_char,
                                                            self._options.csv.add_comments)

        # Рубрики (категории) объекта
        if self._options.csv.add_rubrics:
            data['rubrics'] = self._options.csv.join_char.join(x.name for x in catalog_item.rubrics)

        return data
