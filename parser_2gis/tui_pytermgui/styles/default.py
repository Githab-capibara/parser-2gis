"""
Современные стили для TUI Parser2GIS.

Включает расширенную цветовую палитру, градиенты и темы оформления.
"""


def get_default_styles() -> str:
    """
    Возвращает YAML строку с современными стилями.

    Returns:
        YAML строка с конфигурацией стилей
    """
    return """
# Современная цветовая палитра для Parser2GIS
# Основные цвета в стиле Cyberpunk/Neon

aliases:
    # Основные цвета бренда
    primary: "#00FFFF"
    primary_dark: "#008B8B"
    primary_light: "#E0FFFF"
    
    secondary: "#00FF88"
    secondary_dark: "#008B48"
    secondary_light: "#CCFFDD"
    
    accent: "#FFD700"
    accent_dark: "#B8860B"
    accent_light: "#FFF8DC"
    
    # Функциональные цвета
    success: "#00FF88"
    success_dark: "#006400"
    
    error: "#FF4444"
    error_dark: "#8B0000"
    
    warning: "#FFAA00"
    warning_dark: "#B8860B"
    
    info: "#00BFFF"
    info_dark: "#00688B"
    
    # Неоновые акценты
    neon_pink: "#FF1493"
    neon_purple: "#9400D3"
    neon_blue: "#1E90FF"
    neon_green: "#32CD32"
    neon_orange: "#FF6347"
    
    # Цвета интерфейса
    background: "#0D0D0D"
    background_alt: "#1A1A2E"
    
    surface: "#16213E"
    surface_light: "#1F3460"
    surface_dark: "#0F1623"
    
    panel: "#1B263B"
    panel_light: "#253347"
    
    # Цвета текста
    text: "#EAEAEA"
    text_primary: "#FFFFFF"
    text_secondary: "#B0B0B0"
    text_dim: "#666666"
    text_muted: "#4A4A4A"
    
    # Границы и разделители
    border: "#2D4A7C"
    border_light: "#3D5A8C"
    border_dim: "#1E3A5F"
    
    # Градиенты (симуляция через цвета)
    gradient_start: "#00FFFF"
    gradient_mid: "#00FF88"
    gradient_end: "#FFD700"

# Конфигурация виджетов
config:
    # Поля ввода
    InputField:
        styles:
            prompt: "primary bold"
            cursor: "accent blink"
            text: "text_primary"
            background: "surface_dark"
            border: "border"
    
    # Кнопки
    Button:
        styles:
            label: "primary bold"
            border: "primary"
            background: "surface"
            focus_label: "accent bold"
            focus_border: "accent"
            hover_background: "surface_light"
    
    # Окна
    Window:
        styles:
            border: "primary"
            corner: "primary"
            title: "primary bold"
            background: "background"
            subtitle: "text_dim italic"
    
    # Контейнеры
    Container:
        styles:
            border: "border_dim"
            background: "surface"
            label: "text_secondary"
    
    # Метки
    Label:
        styles:
            text: "text"
            background: "background"
    
    # Списки
    ListView:
        styles:
            highlight: "primary"
            highlight_text: "background"
            selected_border: "accent"
    
    # Чекбоксы
    Checkbox:
        styles:
            checked: "success"
            unchecked: "text_dim"
            label: "text"
    
    # Прогресс-бары
    ProgressBar:
        styles:
            complete: "success"
            incomplete: "text_muted"
            finished: "accent"
    
    # Таблицы
    Table:
        styles:
            header: "primary bold"
            row: "text"
            alt_row: "text_secondary"
            border: "border_dim"
    
    # Разделители
    Divider:
        styles:
            line: "border_dim"
    
    # Спиннеры
    Spinner:
        styles:
            spinner: "accent"
            text: "text_secondary"

# Специальные стили для Parser2GIS
parser2gis:
    # Стили для главного меню
    menu_header:
        styles:
            title: "neon_blue bold"
            subtitle: "text_secondary italic"
            border: "neon_blue"
    
    menu_button:
        styles:
            label: "secondary bold"
            icon: "primary"
            border: "border"
            background: "surface"
            hover_label: "accent bold"
            hover_border: "accent"
    
    # Стили для экрана парсинга
    parsing_header:
        styles:
            title: "neon_green bold"
            border: "neon_green"
    
    parsing_progress:
        styles:
            label: "text_primary"
            bar_complete: "neon_green"
            bar_incomplete: "text_muted"
            percentage: "accent bold"
    
    parsing_stats:
        styles:
            label: "text_secondary"
            value: "text_primary"
            success: "success bold"
            error: "error bold"
            warning: "warning bold"
    
    parsing_log:
        styles:
            info: "info"
            debug: "text_dim"
            warning: "warning"
            error: "error bold"
            critical: "error bold reverse"
            success: "success"
    
    # Стили для экранов выбора
    selector_header:
        styles:
            title: "neon_purple bold"
            border: "neon_purple"
    
    selector_item:
        styles:
            normal: "text"
            selected: "accent bold"
            highlighted: "primary"
            disabled: "text_dim"
    
    # Стили для настроек
    settings_header:
        styles:
            title: "neon_orange bold"
            border: "neon_orange"
    
    settings_field:
        styles:
            label: "text_secondary"
            value: "text_primary"
            valid: "success"
            invalid: "error"
    
    # Стили для экрана "О программе"
    about_header:
        styles:
            title: "neon_pink bold"
            border: "neon_pink"
    
    about_text:
        styles:
            title: "primary bold"
            body: "text"
            link: "info underline"
            version: "accent bold"
"""
