"""Общие компоненты для параллельного парсинга.

ISSUE-044-046, 053: Модули для устранения дублирования кода между:
- parallel_parser.py
- merger.py
- file_merger.py
- strategies.py
- coordinator.py
"""

from .csv_merge_common import generate_temp_merge_path, merge_csv_files_common
from .file_lock import FileLockManager
from .signal_handler_common import MergeSignalHandler

__all__ = [
    "FileLockManager",
    "MergeSignalHandler",
    "generate_temp_merge_path",
    "merge_csv_files_common",
]
