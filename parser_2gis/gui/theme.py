"""
Современная тема для GUI Parser 2GIS.

Вдохновлена стилями Linear, Vercel и Raycast:
- Минималистичный дизайн
- Чистые цвета
- Современная типографика
- Скругленные углы
- Легкие тени
"""

from __future__ import annotations

# =============================================================================
# ЦВЕТОВАЯ ПАЛИТРА
# =============================================================================

# Основные цвета
COLOR_WHITE = '#FFFFFF'
COLOR_BLACK = '#000000'

# Фоновые цвета
COLOR_BACKGROUND = '#FFFFFF'  # Основной фон - белый
COLOR_BACKGROUND_SECONDARY = '#F7F7F7'  # Вторичный фон (светло-серый)
COLOR_BACKGROUND_TERTIARY = '#EFEFEF'  # Третичный фон (для hover)
COLOR_SURFACE = '#FFFFFF'  # Поверхности (карточки, панели)
COLOR_SURFACE_RAISED = '#FFFFFF'  # Приподнятые поверхности (с тенью)

# Цвета акцентов (мята/зеленый)
COLOR_ACCENT_LIGHT = '#E6F7E6'  # Светлый акцентный фон
COLOR_ACCENT_MEDIUM = '#D0F0C0'  # Средний акцент (фоновые блоки)
COLOR_ACCENT = '#34C759'  # Основной акцентный (кнопки, активные элементы)
COLOR_ACCENT_HOVER = '#2DB84F'  # Акцент при наведении
COLOR_ACCENT_ACTIVE = '#25A345'  # Акцент при нажатии
COLOR_ACCENT_SUBTLE = '#E8F5E9'  # Очень светлый акцент для фонов

# Цвета текста
COLOR_TEXT_PRIMARY = '#1A1A1A'  # Основной текст (темно-серый, почти черный)
COLOR_TEXT_SECONDARY = '#666666'  # Вторичный текст (описания, подсказки)
COLOR_TEXT_TERTIARY = '#999999'  # Третичный текст (неактивные элементы)
COLOR_TEXT_DISABLED = '#BDBDBD'  # Неактивный текст
COLOR_TEXT_INVERSE = '#FFFFFF'  # Текст на темном фоне

# Цвета границ
COLOR_BORDER = '#E0E0E0'  # Основная граница
COLOR_BORDER_LIGHT = '#F0F0F0'  # Светлая граница
COLOR_BORDER_FOCUS = '#34C759'  # Граница при фокусе

# Цвета состояний
COLOR_ERROR = '#FF4D4F'  # Ошибки
COLOR_ERROR_BACKGROUND = '#FFF1F0'  # Фон ошибок
COLOR_WARNING = '#FAAD14'  # Предупреждения
COLOR_WARNING_BACKGROUND = '#FFFBE6'  # Фон предупреждений
COLOR_SUCCESS = '#52C41A'  # Успех
COLOR_SUCCESS_BACKGROUND = '#F6FFED'  # Фон успеха
COLOR_INFO = '#1890FF'  # Информация
COLOR_INFO_BACKGROUND = '#E6F7FF'  # Фон информации

# Цвета логирования
COLOR_LOG_CRITICAL = '#FF4D4F'  # Критические ошибки
COLOR_LOG_ERROR = '#FF7875'  # Ошибки
COLOR_LOG_WARNING = '#FFC53D'  # Предупреждения
COLOR_LOG_INFO = '#69C0FF'  # Информация
COLOR_LOG_SUCCESS = '#95DE64'  # Успех
COLOR_LOG_DEBUG = '#B37FEB'  # Отладка

# =============================================================================
# ТИПОГРАФИКА
# =============================================================================

# Шрифты (приоритетный порядок)
FONT_FAMILY_PRIMARY = 'Inter, SF Pro Display, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
FONT_FAMILY_MONO = 'SF Mono, "Cascadia Code", "Fira Code", Consolas, "Courier New", monospace'

# Размеры шрифтов
FONT_SIZE_XS = 10
FONT_SIZE_SM = 11
FONT_SIZE_BASE = 12
FONT_SIZE_MD = 14
FONT_SIZE_LG = 16
FONT_SIZE_XL = 18
FONT_SIZE_2XL = 24
FONT_SIZE_3XL = 32

# Начертания шрифтов
FONT_WEIGHT_NORMAL = 'normal'
FONT_WEIGHT_MEDIUM = '500'
FONT_WEIGHT_SEMIBOLD = '600'
FONT_WEIGHT_BOLD = 'bold'

# Межстрочные интервалы
LINE_HEIGHT_TIGHT = 1.2
LINE_HEIGHT_BASE = 1.5
LINE_HEIGHT_RELAXED = 1.75

# =============================================================================
# РАЗМЕРЫ И ОТСТУПЫ
# =============================================================================

# Скругления углов (px)
RADIUS_SM = 4
RADIUS_MD = 8
RADIUS_LG = 12
RADIUS_XL = 16
RADIUS_FULL = 9999

# Отступы (px)
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 20
SPACING_2XL = 24
SPACING_3XL = 32

# Размеры элементов
ELEMENT_HEIGHT_SM = 28
ELEMENT_HEIGHT_MD = 36
ELEMENT_HEIGHT_LG = 44
ELEMENT_HEIGHT_XL = 52

# Толщины границ
BORDER_WIDTH_THIN = 1
BORDER_WIDTH_BASE = 2
BORDER_WIDTH_THICK = 3

# =============================================================================
# ТЕНИ (CSS-style для справки)
# =============================================================================

# Легкая тень (для карточек)
# box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04), 0 2px 4px rgba(0, 0, 0, 0.04)
SHADOW_SM = '0 1px 2px rgba(0, 0, 0, 0.04)'

# Средняя тень (для приподнятых элементов)
# box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06), 0 4px 8px rgba(0, 0, 0, 0.06)
SHADOW_MD = '0 2px 4px rgba(0, 0, 0, 0.06)'

# Большая тень (для модальных окон)
# box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 8px 24px rgba(0, 0, 0, 0.08)
SHADOW_LG = '0 4px 12px rgba(0, 0, 0, 0.08)'

# Тень при наведении
# box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12), 0 8px 32px rgba(0, 0, 0, 0.12)
SHADOW_HOVER = '0 4px 16px rgba(0, 0, 0, 0.12)'

# =============================================================================
# АНИМАЦИИ
# =============================================================================

# Длительности анимаций (мс)
ANIMATION_DURATION_FAST = 100
ANIMATION_DURATION_BASE = 200
ANIMATION_DURATION_SLOW = 300

# Функции плавности
EASING_LINEAR = 'linear'
EASING_EASE = 'ease'
EASING_EASE_IN_OUT = 'ease-in-out'
EASING_EASE_OUT = 'ease-out'

# =============================================================================
# PY SIMPLEGUI ТЕМА
# =============================================================================

# Современная тема для PySimpleGUI в стиле Linear/Vercel
THEME_MODERN_GREEN = {
    'BACKGROUND': COLOR_BACKGROUND,
    'TEXT': COLOR_TEXT_PRIMARY,
    'INPUT': COLOR_SURFACE,
    'TEXT_INPUT': COLOR_TEXT_PRIMARY,
    'TEXT_ELEMENT_BACKGROUND': COLOR_SURFACE,
    'BUTTON': (COLOR_TEXT_INVERSE, COLOR_ACCENT),
    'BUTTON_HOVER': (COLOR_TEXT_INVERSE, COLOR_ACCENT_HOVER),
    'BUTTON_ACTIVE': (COLOR_TEXT_INVERSE, COLOR_ACCENT_ACTIVE),
    'BUTTON_DISABLED': (COLOR_TEXT_DISABLED, COLOR_BACKGROUND_TERTIARY),
    'BUTTON_CLOSE': (COLOR_TEXT_INVERSE, COLOR_ERROR),
    'BUTTON_EXIT': (COLOR_TEXT_INVERSE, '#DC3545'),
    'BUTTON_SUBMIT': (COLOR_TEXT_INVERSE, COLOR_ACCENT),
    'BUTTON_CANCEL': (COLOR_TEXT_PRIMARY, COLOR_BACKGROUND_SECONDARY),
    'PROGRESS': (COLOR_ACCENT, COLOR_BACKGROUND_SECONDARY),
    'BORDER': COLOR_BORDER,
    'SLIDER_DEPTH': 0,
    'PROGRESS_DEPTH': 0,
    'SCROLL': COLOR_BACKGROUND_TERTIARY,
    'SCROLL_PRESS': COLOR_BORDER,
    'COMBO': COLOR_SURFACE,
    'COMBO_LIST': COLOR_SURFACE,
    'COMBO_RELIEF': 'flat',
    'INPUT_COMBO': COLOR_SURFACE,
    'TREE': COLOR_SURFACE,
    'TREE_HEADER': COLOR_BACKGROUND_SECONDARY,
    'TREE_SELECTED': COLOR_ACCENT_LIGHT,
    'TABLE': COLOR_SURFACE,
    'TABLE_HEADER': COLOR_BACKGROUND_SECONDARY,
    'TABLE_SELECTED': COLOR_ACCENT_LIGHT,
    'HIGHLIGHT': COLOR_ACCENT_LIGHT,
    'HIGHLIGHT_TEXT': COLOR_TEXT_PRIMARY,
    'HOVER': COLOR_BACKGROUND_TERTIARY,
    'HOVER_RELIEF': 'flat',
    'FRAME': COLOR_SURFACE,
    'FRAME_BACK': COLOR_SURFACE,
    'PANE': COLOR_SURFACE,
    'PANE_BACK': COLOR_SURFACE,
    'POPUP_BACKGROUND': COLOR_SURFACE,
    'POPUP_BORDER': COLOR_BORDER,
    'POPUP_TITLE': COLOR_TEXT_PRIMARY,
    'POPUP_TITLE_BACKGROUND': COLOR_SURFACE,
    'TOOLTIP': COLOR_TEXT_PRIMARY,
    'TOOLTIP_BACKGROUND': COLOR_SURFACE,
    'TOOLTIP_BORDER': COLOR_BORDER,
    'DEBUGGER': COLOR_BACKGROUND_SECONDARY,
    'DEBUGGER_SELECTED': COLOR_ACCENT,
    'DEBUGGER_SELECTED_BACKGROUND': COLOR_ACCENT_LIGHT,
    'DEBUGGER_LINE_NUMBERS': COLOR_BACKGROUND_TERTIARY,
    'METER_BACKGROUND': COLOR_BACKGROUND_SECONDARY,
    'METER_COLOR': COLOR_ACCENT,
    'COLOR': COLOR_ACCENT,
    'NAME': 'ModernGreen',
}

# Альтернативная тема с более светлым акцентом
THEME_LIGHT_MINT = {
    'BACKGROUND': COLOR_BACKGROUND,
    'TEXT': COLOR_TEXT_PRIMARY,
    'INPUT': COLOR_SURFACE,
    'TEXT_INPUT': COLOR_TEXT_PRIMARY,
    'TEXT_ELEMENT_BACKGROUND': COLOR_SURFACE,
    'BUTTON': (COLOR_TEXT_INVERSE, '#4CD964'),
    'BUTTON_HOVER': (COLOR_TEXT_INVERSE, '#34C759'),
    'BUTTON_ACTIVE': (COLOR_TEXT_INVERSE, '#2DB84F'),
    'BUTTON_DISABLED': (COLOR_TEXT_DISABLED, COLOR_BACKGROUND_TERTIARY),
    'BUTTON_CLOSE': (COLOR_TEXT_INVERSE, COLOR_ERROR),
    'BUTTON_EXIT': (COLOR_TEXT_INVERSE, '#DC3545'),
    'BUTTON_SUBMIT': (COLOR_TEXT_INVERSE, '#4CD964'),
    'BUTTON_CANCEL': (COLOR_TEXT_PRIMARY, COLOR_BACKGROUND_SECONDARY),
    'PROGRESS': ('#4CD964', COLOR_BACKGROUND_SECONDARY),
    'BORDER': COLOR_BORDER,
    'SLIDER_DEPTH': 0,
    'PROGRESS_DEPTH': 0,
    'SCROLL': COLOR_BACKGROUND_TERTIARY,
    'SCROLL_PRESS': COLOR_BORDER,
    'COMBO': COLOR_SURFACE,
    'COMBO_LIST': COLOR_SURFACE,
    'COMBO_RELIEF': 'flat',
    'INPUT_COMBO': COLOR_SURFACE,
    'TREE': COLOR_SURFACE,
    'TREE_HEADER': COLOR_BACKGROUND_SECONDARY,
    'TREE_SELECTED': '#E8F5E9',
    'TABLE': COLOR_SURFACE,
    'TABLE_HEADER': COLOR_BACKGROUND_SECONDARY,
    'TABLE_SELECTED': '#E8F5E9',
    'HIGHLIGHT': '#E8F5E9',
    'HIGHLIGHT_TEXT': COLOR_TEXT_PRIMARY,
    'HOVER': COLOR_BACKGROUND_TERTIARY,
    'HOVER_RELIEF': 'flat',
    'FRAME': COLOR_SURFACE,
    'FRAME_BACK': COLOR_SURFACE,
    'PANE': COLOR_SURFACE,
    'PANE_BACK': COLOR_SURFACE,
    'POPUP_BACKGROUND': COLOR_SURFACE,
    'POPUP_BORDER': COLOR_BORDER,
    'POPUP_TITLE': COLOR_TEXT_PRIMARY,
    'POPUP_TITLE_BACKGROUND': COLOR_SURFACE,
    'TOOLTIP': COLOR_TEXT_PRIMARY,
    'TOOLTIP_BACKGROUND': COLOR_SURFACE,
    'TOOLTIP_BORDER': COLOR_BORDER,
    'DEBUGGER': COLOR_BACKGROUND_SECONDARY,
    'DEBUGGER_SELECTED': '#4CD964',
    'DEBUGGER_SELECTED_BACKGROUND': '#E8F5E9',
    'DEBUGGER_LINE_NUMBERS': COLOR_BACKGROUND_TERTIARY,
    'METER_BACKGROUND': COLOR_BACKGROUND_SECONDARY,
    'METER_COLOR': '#4CD964',
    'COLOR': '#4CD964',
    'NAME': 'LightMint',
}


def get_theme(name: str = 'modern') -> dict:
    """
    Получить тему по имени.

    Args:
        name: Имя темы ('modern', 'light', 'mint').

    Returns:
        Словарь с параметрами темы.
    """
    themes = {
        'modern': THEME_MODERN_GREEN,
        'light': THEME_LIGHT_MINT,
        'mint': THEME_LIGHT_MINT,
    }
    return themes.get(name, THEME_MODERN_GREEN)


def apply_theme(theme_name: str = 'modern') -> None:
    """
    Применить тему к PySimpleGUI.

    Args:
        theme_name: Имя темы для применения.
    """
    import PySimpleGUI as sg

    theme = get_theme(theme_name)
    
    # PySimpleGUI 5.x (ограниченная версия с PyPI) не имеет полноценной поддержки тем
    # Проверяем доступность функций и применяем тему в зависимости от версии
    if hasattr(sg, 'theme_add_new') and hasattr(sg, 'theme'):
        # PySimpleGUI 5.x с полной поддержкой тем (с частного сервера)
        try:
            sg.theme_add_new(theme['NAME'], **theme)
            sg.theme(theme['NAME'])
            return
        except TypeError:
            # theme_add_new не принимает **kwargs, используем LOOK_AND_FEEL_TABLE
            pass
    
    # PySimpleGUI 4.x и совместимые версии
    # Используем только базовые параметры которые поддерживаются всеми версиями
    if hasattr(sg, 'LOOK_AND_FEEL_TABLE'):
        # Упрощённая тема для совместимости
        simple_theme = {
            'BACKGROUND': theme['BACKGROUND'],
            'TEXT': theme['TEXT'],
            'INPUT': theme['INPUT'],
            'TEXT_INPUT': theme['TEXT_INPUT'],
            'BUTTON': theme['BUTTON'],
            'PROGRESS': theme['PROGRESS'],
            'BORDER': 1,  # Используем число вместо цвета
            'SLIDER_DEPTH': 0,
            'PROGRESS_DEPTH': 0,
            'SCROLL': theme['SCROLL'],
            'SCROLL_PRESS': theme.get('SCROLL_PRESS', theme['SCROLL']),
            'COMBO': theme['INPUT'],
            'COMBO_LIST': theme['INPUT'],
            'NAME': theme['NAME'],
        }
        sg.LOOK_AND_FEEL_TABLE[theme['NAME']] = simple_theme
        sg.theme(theme['NAME'])
    elif hasattr(sg, 'set_options'):
        # PySimpleGUI с ограниченной поддержкой тем
        sg.set_options(
            background_color=theme['BACKGROUND'],
            text_color=theme['TEXT'],
            button_color=theme['BUTTON'],
            button_element_background_color=theme['INPUT'],
            text_element_background_color=theme['TEXT_ELEMENT_BACKGROUND'],
            element_background_color=theme['BACKGROUND'],
            input_elements_background_color=theme['INPUT'],
            input_text_color=theme['TEXT_INPUT'],
        )
    # else: PySimpleGUI без поддержки тем - используем значения по умолчанию


# =============================================================================
# УТИЛИТЫ
# =============================================================================

def get_font(size: int = FONT_SIZE_BASE, weight: str = FONT_WEIGHT_NORMAL) -> str:
    """
    Получить строку шрифта для использования в элементах GUI.

    Args:
        size: Размер шрифта.
        weight: Начертание шрифта.

    Returns:
        Строка шрифта в формате "Family Size Weight".
    """
    return f'Inter {size} {weight}'


def get_spacing(level: str = 'md') -> int:
    """
    Получить значение отступа по уровню.

    Args:
        level: Уровень отступа ('xs', 'sm', 'md', 'lg', 'xl', '2xl', '3xl').

    Returns:
        Значение отступа в пикселях.
    """
    spacing_map = {
        'xs': SPACING_XS,
        'sm': SPACING_SM,
        'md': SPACING_MD,
        'lg': SPACING_LG,
        'xl': SPACING_XL,
        '2xl': SPACING_2XL,
        '3xl': SPACING_3XL,
    }
    return spacing_map.get(level, SPACING_MD)


def get_radius(level: str = 'md') -> int:
    """
    Получить значение скругления по уровню.

    Args:
        level: Уровень скругления ('sm', 'md', 'lg', 'xl', 'full').

    Returns:
        Значение скругления в пикселях.
    """
    radius_map = {
        'sm': RADIUS_SM,
        'md': RADIUS_MD,
        'lg': RADIUS_LG,
        'xl': RADIUS_XL,
        'full': RADIUS_FULL,
    }
    return radius_map.get(level, RADIUS_MD)
