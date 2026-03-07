from __future__ import annotations

import csv
import hashlib
import os
import re
import shutil
from typing import Any, Callable, Dict, List, Optional, Set

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
        # Сложное отображение означает, что его содержимое может содержать несколько сущностей,
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

        # Расширяем сложное отображение
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

    def _writerow(self, row: Dict[str, Any]) -> None:
        """Записывает `row` в CSV.

        Args:
            row: Словарь с данными для записи.
        """
        if self._options.verbose:
            logger.info('Парсинг [%d] > %s', self._wrote_count + 1, row.get('name', 'N/A'))

        try:
            self._writer.writerow(row)
        except Exception as e:
            logger.error('Ошибка во время записи строки: %s', e)

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
                logger.info('Удаление пустых колонок CSV.')
                self._remove_empty_columns()
            except Exception as e:
                logger.error('Ошибка при удалении пустых колонок: %s', e)
                
        # Постобработка: удаление дубликатов
        if self._options.csv.remove_duplicates:
            try:
                logger.info('Удаление повторяющихся записей CSV.')
                self._remove_duplicates()
            except Exception as e:
                logger.error('Ошибка при удалении дубликатов: %s', e)

    def _remove_empty_columns(self) -> None:
        """Постобработка: Удаление пустых колонок.
        
        Примечание:
            Функция анализирует все строки CSV и удаляет колонки,
            которые не содержат данных (за исключением сложных колонок,
            таких как phone_1, phone_2 и т.д.).
        """
        complex_columns = list(self._complex_mapping.keys())
        
        # Словарь для подсчёта непустых значений в сложных колонках
        complex_columns_count: Dict[str, int] = {
            c: 0 for c in self._data_mapping.keys()
            if re.match("|".join(fr"^{x}_\d+$" for x in complex_columns), c)
        }

        try:
            # Первый проход: подсчёт непустых значений в сложных колонках
            with self._open_file(self._file_path, 'r', encoding='utf-8-sig') as f_csv:
                csv_reader = csv.DictReader(f_csv, self._data_mapping.keys())  # type: ignore
                
                for row in csv_reader:
                    for column_name in complex_columns_count.keys():
                        if row.get(column_name, '') != '':
                            complex_columns_count[column_name] += 1
  +++++++ REPLACE

            logger.debug('Подсчёт заполненности колонок завершён')

        except Exception as e:
            logger.error('Ошибка при чтении CSV для анализа колонок: %s', e)
            raise

        # Генерация нового маппинга данных
        new_data_mapping: Dict[str, Any] = {}
        for k, v in self._data_mapping.items():
            if k in complex_columns_count:
                # Оставляем только заполненные сложные колонки
                if complex_columns_count[k] > 0:
                    new_data_mapping[k] = v
            else:
                new_data_mapping[k] = v

        # Переименование одиночной сложной колонки - удаление суффиксов с цифрами
        for column in complex_columns:
            col_1 = f'{column}_1'
            col_2 = f'{column}_2'
            if col_1 in new_data_mapping and col_2 not in new_data_mapping:
                # Удаляем суффикс " 1" из названия колонки
                new_data_mapping[col_1] = re.sub(r'\s+\d+$', '', new_data_mapping[col_1])

        # Создание временного файла
        file_root, file_ext = os.path.splitext(self._file_path)
        tmp_csv_name = f'{file_root}.removed-columns{file_ext}'

        try:
            # Чтение исходного файла и запись нового
            with self._open_file(self._file_path, 'r') as f_csv, \
                 self._open_file(tmp_csv_name, 'w', newline='') as f_tmp_csv:
                
                csv_writer = csv.DictWriter(f_tmp_csv, new_data_mapping.keys())  # type: ignore
                csv_reader = csv.DictReader(f_csv, self._data_mapping.keys())  # type: ignore
                
                # Запись нового заголовка
                csv_writer.writerow(new_data_mapping)
                
                # Пропуск старого заголовка и запись данных
                for row in csv_reader:
                    new_row = {k: v for k, v in row.items() if k in new_data_mapping}
                    csv_writer.writerow(new_row)

            # Замена оригинального файла новым
            shutil.move(tmp_csv_name, self._file_path)
            logger.info('Удалены пустые колонки из CSV')
            
        except Exception as e:
            logger.error('Ошибка при записи CSV без пустых колонок: %s', e)
            # Удаляем временный файл если он существует
            if os.path.exists(tmp_csv_name):
                try:
                    os.remove(tmp_csv_name)
                except OSError:
                    pass
            raise

    def _remove_duplicates(self) -> None:
        """Постобработка: Удаление дубликатов.

        Примечание:
            Использует хеширование строк для надёжного сравнения.
            Включает улучшенную обработку ошибок и очистку временных файлов.
        """
        file_root, file_ext = os.path.splitext(self._file_path)
        tmp_csv_name = f'{file_root}.deduplicated{file_ext}'
        seen_hashes: Set[str] = set()
        duplicates_count = 0

        # Проверка существования файла
        if not os.path.exists(self._file_path):
            logger.error('Файл CSV не найден: %s', self._file_path)
            return

        try:
            # Чтение исходного файла и запись нового без дубликатов
            with self._open_file(self._file_path, 'r', encoding='utf-8-sig') as f_csv, \
                 self._open_file(tmp_csv_name, 'w', encoding='utf-8', newline='') as f_tmp_csv:
  +++++++ REPLACE
                
                for line_num, line in enumerate(f_csv, 1):
                    try:
                        # Нормализуем строку: удаляем завершающие пробелы и newlines
                        normalized_line = line.rstrip('\r\n')

                        # Вычисляем хеш для надёжного сравнения
                        line_hash = hashlib.md5(
                            normalized_line.encode('utf-8'),
                            usedforsecurity=False  # Оптимизация для Python 3.9+
                        ).hexdigest()

                        if line_hash in seen_hashes:
                            duplicates_count += 1
                            continue

                        seen_hashes.add(line_hash)
                        f_tmp_csv.write(line)
                        
                    except Exception as line_error:
                        logger.warning('Ошибка обработки строки %d: %s', line_num, line_error)
                        # Пропускаем проблемную строку и продолжаем

            if duplicates_count > 0:
                logger.info('Удалено дубликатов: %d', duplicates_count)
            else:
                logger.debug('Дубликаты не найдены')

            # Замена оригинального файла новым
            shutil.move(tmp_csv_name, self._file_path)
            
        except (OSError, IOError) as e:
            logger.error('Ошибка при удалении дубликатов: %s', e)
            # Удаляем временный файл если он существует
            if os.path.exists(tmp_csv_name):
                try:
                    os.remove(tmp_csv_name)
                except OSError:
                    pass
            raise
            
        except KeyboardInterrupt:
            logger.info('Операция удаления дубликатов прервана пользователем')
            # Удаляем временный файл при прерывании
            if os.path.exists(tmp_csv_name):
                try:
                    os.remove(tmp_csv_name)
                except OSError:
                    pass
            raise
            
        except Exception as e:
            logger.error('Непредвиденная ошибка при удалении дубликатов: %s', e)
            # Удаляем временный файл если он существует
            if os.path.exists(tmp_csv_name):
                try:
                    os.remove(tmp_csv_name)
                except OSError:
                    pass
            raise

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
            result = catalog_doc.get('result')
            if not result or 'items' not in result:
                logger.error('Некорректная структура документа: отсутствует result.items')
                return {}
                
            items = result.get('items', [])
            if not items:
                logger.error('Пустой список items в документе')
                return {}
                
            item = items[0]
        except (KeyError, TypeError, IndexError) as e:
            logger.error('Ошибка при извлечении элемента из документа: %s', e)
            return {}

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
            item_type = item.get('type', 'неизвестно')
            item_id = item.get('id', 'неизвестно')
            error_str = 'Ошибка парсинга:\n' + '\n'.join(errors)
            error_str += f'\nДокумент каталога (тип: {item_type}, ID: {item_id})'
            logger.error(error_str)

            # Возвращаем пустой словарь для индикации ошибки
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
            def append_contact(contact_type: str, priority_fields: List[str],
                               formatter: Optional[Callable[[str], str]] = None) -> None:
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
