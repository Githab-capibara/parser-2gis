"""
Тесты для модуля gui/theme.py.

Проверяют следующие возможности:
- Цветовые константы
- Типографика
- Размеры и отступы
- Тени
- Функции утилит
"""

import pytest

from parser_2gis.gui.theme import (COLOR_ACCENT, COLOR_BACKGROUND,
                                   COLOR_TEXT_PRIMARY, FONT_SIZE_BASE,
                                   RADIUS_MD, SPACING_MD, apply_theme,
                                   get_font, get_radius, get_spacing,
                                   get_theme)


class TestColorConstants:
    """Тесты для цветовых констант."""

    def test_color_white(self):
        """Проверка COLOR_WHITE."""
        from parser_2gis.gui.theme import COLOR_WHITE
        assert COLOR_WHITE == '#FFFFFF'

    def test_color_background(self):
        """Проверка COLOR_BACKGROUND."""
        assert COLOR_BACKGROUND == '#FFFFFF'

    def test_color_accent(self):
        """Проверка COLOR_ACCENT."""
        assert COLOR_ACCENT == '#34C759'

    def test_color_text_primary(self):
        """Проверка COLOR_TEXT_PRIMARY."""
        assert COLOR_TEXT_PRIMARY == '#1A1A1A'

    def test_color_hex_format(self):
        """Проверка формата HEX цветов."""
        colors = [
            COLOR_BACKGROUND,
            COLOR_ACCENT,
            COLOR_TEXT_PRIMARY,
        ]
        for color in colors:
            assert color.startswith('#')
            assert len(color) == 7

    def test_error_colors_exist(self):
        """Проверка существования цветов ошибок."""
        from parser_2gis.gui.theme import (COLOR_ERROR, COLOR_ERROR_BACKGROUND,
                                           COLOR_LOG_ERROR, COLOR_LOG_WARNING)
        assert COLOR_ERROR.startswith('#')
        assert COLOR_ERROR_BACKGROUND.startswith('#')
        assert COLOR_LOG_ERROR.startswith('#')
        assert COLOR_LOG_WARNING.startswith('#')


class TestTypography:
    """Тесты для типографики."""

    def test_font_size_base(self):
        """Проверка FONT_SIZE_BASE."""
        assert FONT_SIZE_BASE == 12

    def test_font_size_range(self):
        """Проверка диапазона размеров шрифтов."""
        from parser_2gis.gui.theme import (FONT_SIZE_2XL, FONT_SIZE_3XL,
                                           FONT_SIZE_LG, FONT_SIZE_MD,
                                           FONT_SIZE_SM, FONT_SIZE_XL, FONT_SIZE_XS)
        sizes = [FONT_SIZE_XS, FONT_SIZE_SM, FONT_SIZE_BASE,
                 FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL,
                 FONT_SIZE_2XL, FONT_SIZE_3XL]
        for i in range(len(sizes) - 1):
            assert sizes[i] <= sizes[i + 1]

    def test_font_weights_exist(self):
        """Проверка существования начертаний шрифтов."""
        from parser_2gis.gui.theme import (FONT_WEIGHT_BOLD, FONT_WEIGHT_MEDIUM,
                                           FONT_WEIGHT_NORMAL, FONT_WEIGHT_SEMIBOLD)
        assert FONT_WEIGHT_NORMAL == 'normal'
        assert FONT_WEIGHT_MEDIUM == '500'
        assert FONT_WEIGHT_SEMIBOLD == '600'
        assert FONT_WEIGHT_BOLD == 'bold'


class TestSpacing:
    """Тесты для отступов."""

    def test_spacing_md(self):
        """Проверка SPACING_MD."""
        assert SPACING_MD == 12

    def test_spacing_increasing(self):
        """Проверка увеличения отступов."""
        from parser_2gis.gui.theme import (SPACING_2XL, SPACING_3XL, SPACING_LG,
                                           SPACING_SM, SPACING_XL, SPACING_XS)
        sizes = [SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG,
                 SPACING_XL, SPACING_2XL, SPACING_3XL]
        for i in range(len(sizes) - 1):
            assert sizes[i] <= sizes[i + 1]


class TestRadius:
    """Тесты для скруглений."""

    def test_radius_md(self):
        """Проверка RADIUS_MD."""
        assert RADIUS_MD == 8

    def test_radius_increasing(self):
        """Проверка увеличения скруглений."""
        from parser_2gis.gui.theme import (RADIUS_LG, RADIUS_SM, RADIUS_XL,
                                           RADIUS_FULL)
        sizes = [RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_XL, RADIUS_FULL]
        for i in range(len(sizes) - 1):
            assert sizes[i] <= sizes[i + 1]


class TestGetFont:
    """Тесты для функции get_font."""

    def test_get_font_default(self):
        """Проверка get_font по умолчанию."""
        font = get_font()
        assert '12' in font

    def test_get_font_custom_size(self):
        """Проверка get_font с кастомным размером."""
        font = get_font(size=16)
        assert '16' in font

    def test_get_font_custom_weight(self):
        """Проверка get_font с кастомным начертанием."""
        font = get_font(weight='bold')
        assert 'bold' in font

    def test_get_font_returns_string(self):
        """Проверка, что get_font возвращает строку."""
        font = get_font()
        assert isinstance(font, str)


class TestGetSpacing:
    """Тесты для функции get_spacing."""

    def test_get_spacing_default(self):
        """Проверка get_spacing по умолчанию."""
        spacing = get_spacing()
        assert spacing == SPACING_MD

    def test_get_spacing_levels(self):
        """Проверка get_spacing с разными уровнями."""
        assert get_spacing('xs') == 4
        assert get_spacing('sm') == 8
        assert get_spacing('md') == 12
        assert get_spacing('lg') == 16
        assert get_spacing('xl') == 20
        assert get_spacing('2xl') == 24
        assert get_spacing('3xl') == 32

    def test_get_spacing_invalid_level(self):
        """Проверка get_spacing с невалидным уровнем."""
        spacing = get_spacing('invalid')
        assert spacing == SPACING_MD


class TestGetRadius:
    """Тесты для функции get_radius."""

    def test_get_radius_default(self):
        """Проверка get_radius по умолчанию."""
        radius = get_radius()
        assert radius == RADIUS_MD

    def test_get_radius_levels(self):
        """Проверка get_radius с разными уровнями."""
        assert get_radius('sm') == 4
        assert get_radius('md') == 8
        assert get_radius('lg') == 12
        assert get_radius('xl') == 16
        assert get_radius('full') == 9999

    def test_get_radius_invalid_level(self):
        """Проверка get_radius с невалидным уровнем."""
        radius = get_radius('invalid')
        assert radius == RADIUS_MD


class TestGetTheme:
    """Тесты для функции get_theme."""

    def test_get_theme_modern(self):
        """Проверка get_theme для modern."""
        theme = get_theme('modern')
        assert isinstance(theme, dict)
        assert 'BACKGROUND' in theme
        assert 'TEXT' in theme

    def test_get_theme_light(self):
        """Проверка get_theme для light."""
        theme = get_theme('light')
        assert isinstance(theme, dict)
        assert 'BACKGROUND' in theme

    def test_get_theme_mint(self):
        """Проверка get_theme для mint."""
        theme = get_theme('mint')
        assert isinstance(theme, dict)
        assert 'BACKGROUND' in theme

    def test_get_theme_default(self):
        """Проверка get_theme по умолчанию."""
        theme = get_theme()
        assert isinstance(theme, dict)
        assert 'BACKGROUND' in theme

    def test_get_theme_invalid(self):
        """Проверка get_theme с невалидным именем."""
        theme = get_theme('invalid')
        assert isinstance(theme, dict)
        assert 'BACKGROUND' in theme


class TestApplyTheme:
    """Тесты для функции apply_theme."""

    def test_apply_theme_exists(self):
        """Проверка существования apply_theme."""
        assert callable(apply_theme)

    @pytest.mark.skip(reason="Требует PySimpleGUI")
    def test_apply_theme_default(self):
        """Проверка apply_theme по умолчанию."""
        try:
            apply_theme('modern')
            # Если нет ошибок, тест пройден
        except Exception as e:
            pytest.fail(f"apply_theme вызвала исключение: {e}")


class TestThemeStructure:
    """Тесты для структуры темы."""

    def test_theme_has_required_keys(self):
        """Проверка наличия обязательных ключей."""
        theme = get_theme('modern')
        required_keys = [
            'BACKGROUND', 'TEXT', 'INPUT', 'BUTTON',
            'PROGRESS', 'BORDER', 'FRAME', 'POPUP_BACKGROUND'
        ]
        for key in required_keys:
            assert key in theme, f"Отсутствует ключ {key}"

    def test_button_is_tuple(self):
        """Проверка, что BUTTON - кортеж."""
        theme = get_theme('modern')
        assert isinstance(theme['BUTTON'], tuple)
        assert len(theme['BUTTON']) == 2
