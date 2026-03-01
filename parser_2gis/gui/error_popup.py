from __future__ import annotations

import textwrap

from ..common import GUI_ENABLED, running_linux
from ..paths import image_data
from .theme import (COLOR_ACCENT, COLOR_BACKGROUND, COLOR_ERROR,
                    COLOR_ERROR_BACKGROUND, COLOR_TEXT_PRIMARY,
                    COLOR_TEXT_SECONDARY, COLOR_WHITE, FONT_SIZE_BASE,
                    FONT_SIZE_LG, FONT_SIZE_MD, FONT_SIZE_XL, SPACING_LG,
                    SPACING_MD, SPACING_SM, apply_theme, get_font)
from .utils import ensure_gui_enabled

if GUI_ENABLED:
    import PySimpleGUI as sg


@ensure_gui_enabled
def gui_error_popup(error_msg: str) -> None:
    """Run error modal window.

    Args:
        error_msg: Error message.
    """
    # Применяем современную тему
    apply_theme('modern')

    # Set icon
    sg.set_global_icon(image_data('icon', 'png'))

    # Adjust error message width
    error_msg = '\n'.join(
        textwrap.wrap(error_msg, width=70, replace_whitespace=False, break_on_hyphens=False)
    )

    # Window layout - современный дизайн
    layout = [
        # Иконка ошибки и заголовок
        [
            sg.Column([
                [
                    sg.Text('⚠️', font=('Segoe UI Emoji', 36), 
                            background_color=COLOR_ERROR_BACKGROUND, 
                            pad=(SPACING_MD, SPACING_MD)),
                ],
            ], element_justification='center', size=(60, 60), 
               background_color=COLOR_ERROR_BACKGROUND),
            sg.Column([
                [
                    sg.Text('Ошибка', font=get_font(FONT_SIZE_XL, 'bold'), 
                            text_color=COLOR_TEXT_PRIMARY, pad=(SPACING_MD, SPACING_SM)),
                    sg.Text(error_msg, font=get_font(FONT_SIZE_BASE), 
                            text_color=COLOR_TEXT_SECONDARY, pad=(0, SPACING_MD), 
                            justification='left'),
                ],
            ], expand_x=True, background_color=COLOR_ERROR_BACKGROUND, 
               pad=(SPACING_SM, SPACING_MD)),
        ],
        
        # Кнопка закрытия
        [
            sg.Column([
                [
                    sg.Button('Закрыть', key='-BTN_CLOSE-', size=(12, 1),
                              button_color=(COLOR_WHITE, COLOR_ERROR),
                              border_width=0, font=get_font(FONT_SIZE_BASE, 'bold'),
                              focus=True, bind_return_key=True, 
                              pad=(SPACING_MD, SPACING_LG)),
                ],
            ], expand_x=True, element_justification='center', 
               background_color=COLOR_BACKGROUND),
        ],
    ]

    window_title = 'Error' if running_linux() else 'Ошибка'
    window = sg.Window(window_title, layout, auto_size_text=True, finalize=True,
                       font=get_font(FONT_SIZE_BASE), modal=True, keep_on_top=True,
                       background_color=COLOR_ERROR_BACKGROUND,
                       no_titlebar=False, resizable=False)

    while True:
        event, _ = window.Read()

        # Close window
        if event in (None, '-BTN_CLOSE-'):
            break

    window.close()
    del window
