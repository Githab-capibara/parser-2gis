"""Писатель (пост-процесс конвертер) в XLSX таблицу.

Предоставляет класс XLSXWriter для конвертации CSV в XLSX формат:
- Наследуется от CSVWriter
- Конвертирует CSV в XLSX через xlsxwriter
- Использует constant_memory для работы с большими файлами
"""

from __future__ import annotations

import csv
import os
import shutil

from xlsxwriter.workbook import Workbook

from parser_2gis.logger import logger

from .csv_writer import CSVWriter


class XLSXWriter(CSVWriter):
    """Писатель (пост-процесс конвертер) в XLSX таблицу."""

    def __exit__(self, *exc_info) -> None:
        super().__exit__(*exc_info)

        # Конвертируем CSV в XLSX таблицу
        tmp_xlsx_name = os.path.splitext(self._file_path)[0] + ".converted.xlsx"

        # Используем try/finally для гарантии удаления временного файла при ошибке
        try:
            # constant_memory=True уменьшает потребление RAM при работе с большими файлами
            with Workbook(tmp_xlsx_name, {"constant_memory": True}) as workbook:
                bold = workbook.add_format({"bold": True})  # Формат для заголовка

                worksheet = workbook.add_worksheet()
                with self._open_file(self._file_path, "r") as f_csv:
                    csv_reader = csv.reader(f_csv)
                    for r, row in enumerate(csv_reader):
                        for c, col in enumerate(row):
                            if r == 0:
                                worksheet.write(r, c, col, bold)  # Запись заголовка
                            else:
                                worksheet.write(r, c, col)

            # Замена оригинального файла новым
            shutil.move(tmp_xlsx_name, self._file_path)
        except Exception as e:
            # Удаляем временный файл если он был создан
            if os.path.exists(tmp_xlsx_name):
                os.remove(tmp_xlsx_name)
            logger.error("Ошибка при конвертации в XLSX: %s", e)
            raise
