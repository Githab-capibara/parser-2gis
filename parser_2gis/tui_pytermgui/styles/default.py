"""
Стили по умолчанию для TUI Parser2GIS.
"""


def get_default_styles() -> str:
    """
    Возвращает YAML строку со стилями по умолчанию.

    Returns:
        YAML строка с конфигурацией стилей
    """
    return """
aliases:
    primary: "#00FFFF"
    secondary: "#00FF00"
    accent: "#FFD700"
    error: "#FF0000"
    warning: "#FFFF00"
    info: "#00BFFF"
    dim: "#666666"
    background: "#1A1A1A"
    surface: "#2D2D2D"
    text: "#FFFFFF"

config:
    Label:
        styles:
            value: "@text"

    InputField:
        styles:
            prompt: "@primary bold"
            cursor: "@accent"
            text: "@text"

    Button:
        styles:
            label: "@secondary bold"
            border: "@primary"
            background: "@surface"
        meta:
            corner: "╭─"

    Window:
        styles:
            border: "@primary"
            corner: "@primary"
            title: "@primary bold"
        meta:
            corner: "╭─"
"""
