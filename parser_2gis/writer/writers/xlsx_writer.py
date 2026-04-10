"""Писатель (пост-процесс конвертер) в XLSX таблицу.

Предоставляет класс XLSXWriter для конвертации CSV в XLSX формат:
- Наследуется от FileWriter (базовый класс)
- Конвертирует CSV в XLSX через xlsxwriter
- Использует constant_memory для работы с большими файлами
"""

from __future__ import annotations

import csv
import os
import shutil
from typing import Any

from xlsxwriter.workbook import Workbook

from parser_2gis.logger import logger

from .file_writer import FileWriter


class XLSXWriter(FileWriter):
    """Писатель (пост-процесс конвертер) в XLSX таблицу.

    Наследуется напрямую от FileWriter, а не от CSVWriter,
    так как XLSX и CSV — разные форматы и не должны быть в иерархии наследования.

    Ограничения формата XLSX:
    - Максимальное количество строк: 1 048 576
    - Максимальное количество колонок: 16 384 (XFD)
    - Максимальная длина строки: 32 767 символов
    - Максимальный размер файла: 2 GB

    Примечание:
        XLSXWriter работает как пост-процесс конвертер из CSV.
        Метод write() не используется напрямую - конвертация происходит
        при закрытии файла через __exit__().

        constant_memory=True используется для работы с большими файлами,
        записывая данные напрямую на диск вместо хранения в памяти.
    """

    def write(self, records: dict[str, Any]) -> None:
        """Записывает данные в XLSX формат.

        #154: Метод является заглушкой — XLSXWriter работает как пост-процесс конвертер.
        Конвертация CSV в XLSX происходит при закрытии файла через __exit__().

        Args:
            records: Данные каталога (игнорируются).

        Примечание:
            Этот метод вызывается базовым классом, но не используется напрямую.
            Все данные записываются через CSV writer, а затем конвертируются в XLSX.
        """
        # #154: Заглушка вместо NotImplementedError — данные записываются через CSV,
        # а конвертация происходит в __exit__()

    def __exit__(self, *exc_info: Any) -> None:
        """Закрывает файл и выполняет конвертацию CSV в XLSX.

        ISSUE-173: Добавлено описание constant_memory=True.

        Примечание:
            constant_memory=True (Workbook с опцией {"constant_memory": True}):
            - Записывает данные напрямую на диск вместо хранения в памяти
            - Позволяет обрабатывать файлы больше доступной RAM
            - Уменьшает потребление памяти при работе с большими файлами
            - Может незначительно снизить производительность записи

        """
        # Закрываем файл если он открыт
        if hasattr(self, "_file") and not self._file.closed:
            self._file.close()

        # Конвертируем CSV в XLSX таблицу
        tmp_xlsx_name = os.path.splitext(self._file_path)[0] + ".converted.xlsx"

        # Используем try/finally для гарантии удаления временного файла при ошибке
        try:
            # constant_memory=True уменьшает потребление RAM при работе с большими файлами
            # Записывает данные напрямую на диск вместо хранения в памяти
            with Workbook(tmp_xlsx_name, {"constant_memory": True}) as workbook:
                bold = workbook.add_format({"bold": True})  # Формат для заголовка

                worksheet = workbook.add_worksheet()
                try:
                    with self._open_file(self._file_path, "r") as f_csv:
                        csv_reader = csv.reader(f_csv)
                        for r, row in enumerate(csv_reader):
                            for c, col in enumerate(row):
                                if r == 0:
                                    worksheet.write(r, c, col, bold)  # Запись заголовка
                                else:
                                    worksheet.write(r, c, col)
                except csv.Error as csv_error:
                    logger.error("Ошибка парсинга CSV при конвертации в XLSX: %s", csv_error)
                    raise

            # Замена оригинального файла новым
            # #158: Проверка существования временного файла перед перемещением
            if os.path.exists(tmp_xlsx_name):
                shutil.move(tmp_xlsx_name, self._file_path)
            else:
                logger.warning("Временный файл XLSX не создан: %s", tmp_xlsx_name)
        except (OSError, csv.Error, ValueError, RuntimeError) as e:
            # Удаляем временный файл если он был создан
            if os.path.exists(tmp_xlsx_name):
                os.remove(tmp_xlsx_name)
            logger.error("Ошибка при конвертации в XLSX: %s", e)
            raise
