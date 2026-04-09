"""Общие CSS стили для TUI экранов.

ISSUE-049: Вынесено из category_selector.py и city_selector.py для устранения
дублирования CSS стилей в Textual экранах.

Пример использования:
    >>> from parser_2gis.tui_textual.common_styles import COMMON_CSS
    >>> class MyScreen(Screen):
    ...     CSS = COMMON_CSS
"""

from __future__ import annotations

# =============================================================================
# ОБЩИЕ CSS КОНСТАНТЫ
# =============================================================================

# Цвета
CSS_COLOR_DARK = "#333"
CSS_COLOR_LIGHT = "#666"

# Размеры
CONTAINER_MAX_WIDTH = 90
CONTAINER_MIN_WIDTH = 60
CONTAINER_HEIGHT_PERCENT = 80

HEADER_HEIGHT = 3
COUNTER_PANEL_HEIGHT = 3

BUTTON_MIN_WIDTH = 12
PADDING_HORIZONTAL = 2
PADDING_VERTICAL = 1

MARGIN_VERTICAL = 1

# =============================================================================
# ОБЩИЕ CSS СТИЛИ
# =============================================================================

COMMON_CSS = f"""
/* Общие стили для всех экранов TUI */

/* Главный контейнер */
#category-selector-container,
#city-selector-container,
#parsing-screen-container,
#settings-container {{
    width: 100%;
    max-width: {CONTAINER_MAX_WIDTH};
    min-width: {CONTAINER_MIN_WIDTH};
    height: {CONTAINER_HEIGHT_PERCENT}%;
    background: $surface-darken-2;
    border: solid $primary;
    padding: {PADDING_VERTICAL} {PADDING_HORIZONTAL};
    align: center middle;
}}

/* Заголовок — используется во всех экранах */
.header {{
    width: 100%;
    height: {HEADER_HEIGHT};
    content-align: center middle;
    text-style: bold;
    color: $accent;
}}

/* Панель поиска */
.search-panel {{
    width: 100%;
    height: auto;
    margin: {MARGIN_VERTICAL} 0;
}}

/* Поле поиска */
.search-input {{
    width: 100%;
}}

/* Панель счётчика */
.counter-panel {{
    width: 100%;
    height: {COUNTER_PANEL_HEIGHT};
    content-align: left middle;
    margin: {MARGIN_VERTICAL} 0;
    background: $surface-darken-3;
}}

/* Контейнер списка */
.category-list-container,
.city-list-container {{
    width: 100%;
    height: 1fr;
    border: solid $secondary;
}}

/* Ряд кнопок */
.button-row {{
    width: 100%;
    height: auto;
    align: center middle;
    margin-top: {MARGIN_VERTICAL};
}}

/* Кнопки в ряду */
.button-row Button {{
    margin: 0 {MARGIN_VERTICAL};
    min-width: {BUTTON_MIN_WIDTH};
}}
"""

# =============================================================================
# ОТДЕЛЬНЫЕ CSS КЛАССЫ ДЛЯ ИСПОЛЬЗОВАНИЯ В ЭКРАНАХ
# =============================================================================

# Стили заголовка
HEADER_CSS = """
.header {
    width: 100%;
    height: 3;
    content-align: center middle;
    text-style: bold;
    color: $accent;
}
"""

# Стили контейнера
CONTAINER_CSS = f"""
#main-container {{
    width: 100%;
    max-width: {CONTAINER_MAX_WIDTH};
    min-width: {CONTAINER_MIN_WIDTH};
    height: {CONTAINER_HEIGHT_PERCENT}%;
    background: $surface-darken-2;
    border: solid $primary;
    padding: {PADDING_VERTICAL} {PADDING_HORIZONTAL};
    align: center middle;
}}
"""

# Стили кнопок
BUTTON_ROW_CSS = f"""
.button-row {{
    width: 100%;
    height: auto;
    align: center middle;
    margin-top: {MARGIN_VERTICAL};
}}

.button-row Button {{
    margin: 0 {MARGIN_VERTICAL};
    min-width: {BUTTON_MIN_WIDTH};
}}
"""
