"""
Модуль для отображения прогресса парсинга в CLI режиме.

Предоставляет функциональность для визуализации прогресса парсинга
с использованием библиотеки tqdm.
"""

import time
from dataclasses import dataclass
from typing import Optional

try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None


@dataclass
class ProgressStats:
    """Статистика прогресса парсинга.

    Содержит информацию о текущем состоянии прогресса парсинга,
    включая количество обработанных страниц и записей.

    Attributes:
        total_pages: Общее количество страниц для обработки
        current_page: Текущее количество обработанных страниц
        total_records: Общее количество записей (опционально)
        current_record: Текущее количество обработанных записей
        started_at: Время начала обработки (timestamp)
        finished_at: Время завершения обработки (timestamp)
    """

    total_pages: int = 0
    current_page: int = 0
    total_records: int = 0
    current_record: int = 0
    started_at: Optional[float] = None
    finished_at: Optional[float] = None


class ProgressManager:
    """Менеджер прогресс-бара для CLI режима.

    Этот класс предоставляет возможность отображения прогресса парсинга
    в командной строке с помощью прогресс-бара. Показывает прогресс
    по страницам и записям, а также ETA (Expected Time of Arrival)
    и скорость обработки.

    Attributes:
        _disable: Флаг отключения прогресс-бара
        _stats: Статистика прогресса
        _page_bar: Прогресс-бар для страниц
        _record_bar: Прогресс-бар для записей

    Пример использования:
        >>> progress = ProgressManager()
        >>> progress.start(total_pages=10, total_records=100)
        >>> for page in range(10):
        ...     # Обработка страницы
        ...     progress.update_page()
        ...     for record in range(10):
        ...         # Обработка записи
        ...         progress.update_record()
        >>> progress.finish()
    """

    def __init__(self, disable: bool = False):
        """Инициализация менеджера прогресса.

        Args:
            disable: Отключить прогресс-бар (по умолчанию False)

        Raises:
            ImportError: Если tqdm не установлен и disable=False
        """
        if not TQDM_AVAILABLE and not disable:
            raise ImportError(
                "Для работы прогресс-бара требуется библиотека tqdm. "
                "Установите её: pip install tqdm"
            )

        self._disable = disable
        self._stats = ProgressStats()
        self._page_bar: Optional[tqdm] = None
        self._record_bar: Optional[tqdm] = None

    def start(self, total_pages: int, total_records: Optional[int] = None) -> None:
        """Запуск прогресс-бара.

        Инициализирует прогресс-бары для отображения прогресса
        по страницам и записям (если указано).

        Args:
            total_pages: Общее количество страниц для обработки
            total_records: Общее количество записей (опционально)
        """
        self._stats.total_pages = total_pages
        self._stats.total_records = total_records or 0
        self._stats.started_at = time.time()

        if self._disable:
            return

        # Создаем прогресс-бар для страниц
        self._page_bar = tqdm(
            total=total_pages,
            desc="Страницы",
            unit="стр",
            colour="blue",
            disable=self._disable,
        )

        # Создаем прогресс-бар для записей (если указано)
        if total_records:
            self._record_bar = tqdm(
                total=total_records,
                desc="Записи",
                unit="зап",
                colour="green",
                disable=self._disable,
            )

    def update_page(self, n: int = 1) -> None:
        """Обновление прогресса по страницам.

        Увеличивает счетчик обработанных страниц на указанное значение.

        Args:
            n: Количество обработанных страниц (по умолчанию 1)
        """
        self._stats.current_page += n

        if self._page_bar:
            self._page_bar.update(n)

    def update_record(self, n: int = 1) -> None:
        """Обновление прогресса по записям.

        Увеличивает счетчик обработанных записей на указанное значение.

        Args:
            n: Количество обработанных записей (по умолчанию 1)
        """
        self._stats.current_record += n

        if self._record_bar:
            self._record_bar.update(n)

    def finish(self) -> None:
        """Завершение прогресс-бара.

        Закрывает все прогресс-бары и выводит итоговую статистику,
        включая общее время работы и скорость обработки.
        """
        self._stats.finished_at = time.time()

        # Закрываем прогресс-бары
        if self._page_bar:
            self._page_bar.close()

        if self._record_bar:
            self._record_bar.close()

        # Выводим итоговую статистику
        if not self._disable:
            # Рассчитываем прошедшее время с защитой от None
            started = self._stats.started_at if self._stats.started_at is not None else 0
            elapsed = self._stats.finished_at - started if self._stats.finished_at else 0

            # Рассчитываем скорость обработки
            records_per_sec = self._stats.current_record / elapsed if elapsed > 0 else 0

            # Выводим результаты
            print(
                f"\n✅ Завершено за {elapsed:.1f} сек ({records_per_sec:.1f} записей/сек)"
            )

    def get_stats(self) -> ProgressStats:
        """Получение текущей статистики прогресса.

        Returns:
            Объект ProgressStats с текущей статистикой
        """
        return self._stats

    def reset(self) -> None:
        """Сброс прогресс-бара.

        Сбрасывает всю статистику и закрывает прогресс-бары.
        Полезно для повторного использования того же менеджера.
        """
        if self._page_bar:
            self._page_bar.close()

        if self._record_bar:
            self._record_bar.close()

        self._stats = ProgressStats()
        self._page_bar = None
        self._record_bar = None

    @property
    def is_started(self) -> bool:
        """Проверка, запущен ли прогресс-бар.

        Returns:
            True, если прогресс-бар запущен, иначе False
        """
        return self._stats.started_at is not None

    @property
    def is_finished(self) -> bool:
        """Проверка, завершен ли прогресс-бар.

        Returns:
            True, если прогресс-бар завершен, иначе False
        """
        return self._stats.finished_at is not None
