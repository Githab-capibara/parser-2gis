"""
Модуль для интеллектуального определения окончания поисковой выдачи.

Этот модуль предоставляет функции для определения того, что достигнут конец
результатов поиска на странице 2GIS, что позволяет избежать бесконечного
цикла и сэкономить время парсинга.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ..logger import logger

if TYPE_CHECKING:
    from ..chrome import ChromeRemote


class EndOfResultsDetector:
    """
    Детектор окончания поисковой выдачи.

    Анализирует страницу на наличие паттернов, указывающих на то,
    что все результаты показаны и дальше переходить не нужно.
    """

    # Паттерны текста, указывающие на окончание результатов
    END_PATTERNS = [
        r"показан[ыо].*вс[её].*организаци[ияй]",
        r"нет.*дополнительн[ыхих].*результат[ова]",
        r"вы.*просмотрели.*вс[её].*вариант[ыов]",
        r"конец.*результат[ова]",
        r"больше.*ничего.*не.*нашл[ио]",
    ]

    # Паттерны DOM-элементов, указывающих на окончание
    DOM_END_SELECTORS = [
        lambda node: node.local_name == "div"
        and any(
            pattern in node.text.lower() for pattern in ["конец", "нет результатов"]
        ),
        lambda node: node.local_name == "p"
        and "ничего не найдено" in node.text.lower(),
    ]

    def __init__(self, chrome_remote: "ChromeRemote") -> None:
        """
        Инициализирует детектор.

        Args:
            chrome_remote: Объект ChromeRemote для доступа к DOM.
        """
        self._chrome_remote = chrome_remote
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.END_PATTERNS
        ]

    def is_end_of_results(self) -> bool:
        """
        Проверяет, достигнут ли конец результатов поиска.

        Returns:
            True если достигнут конец, False если есть ещё результаты.
        """
        try:
            # Получаем DOM страницы
            dom_tree = self._chrome_remote.get_document()

            # Проверяем текстовые паттерны на всей странице
            page_text = dom_tree.text.lower()
            for pattern in self._compiled_patterns:
                if pattern.search(page_text):
                    logger.debug("Обнаружен паттерн окончания: %s", pattern.pattern)
                    return True

            # Проверяем DOM-элементы
            nodes = dom_tree.search(
                lambda node: bool(node.text) and len(node.text) < 500
            )
            for selector in self.DOM_END_SELECTORS:
                for node in nodes:
                    try:
                        if selector(node):
                            logger.debug("Обнаружен DOM-элемент окончания")
                            return True
                    except Exception as e:
                        logger.debug("Ошибка при проверке DOM-элемента: %s", e)
                        continue

            return False

        except Exception as e:
            logger.warning("Ошибка при проверке окончания результатов: %s", e)
            return False

    def has_pagination(self) -> bool:
        """
        Проверяет, есть ли на странице элементы пагинации.

        Returns:
            True если есть пагинация, False если нет.
        """
        try:
            dom_tree = self._chrome_remote.get_document()

            # Ищем ссылки на страницы
            page_links = dom_tree.search(
                lambda x: x.local_name == "a"
                and "href" in x.attributes
                and "/page/" in x.attributes.get("href", "")
            )

            # Если есть хотя бы одна ссылка на страницу кроме первой
            has_pages = len(page_links) > 0

            if has_pages:
                logger.debug("Обнаружена пагинация (%d ссылок)", len(page_links))
            else:
                logger.debug("Пагинация не обнаружена")

            return has_pages

        except Exception as e:
            logger.warning("Ошибка при проверке пагинации: %s", e)
            return False
