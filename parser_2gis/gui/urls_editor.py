from __future__ import annotations

from typing import TYPE_CHECKING

from ..common import GUI_ENABLED
from .theme import (COLOR_ACCENT, COLOR_BACKGROUND, COLOR_BACKGROUND_SECONDARY,
                    COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
                    COLOR_WHITE, FONT_SIZE_BASE, FONT_SIZE_LG, FONT_SIZE_MD,
                    FONT_SIZE_XL, SPACING_LG, SPACING_MD, SPACING_SM, SPACING_XS,
                    apply_theme, get_font)
from .urls_generator import gui_urls_generator
from .utils import ensure_gui_enabled, invoke_widget_hook, setup_text_widget

if TYPE_CHECKING:
    import tkinter as tk

if GUI_ENABLED:
    import PySimpleGUI as sg
    from .widgets.tk import LineNumberedText


def create_text_widget(column_element: sg.Element, containing_frame: tk.Frame,
                       toplevel_form: sg.Window) -> tk.Widget:
    """Callback для `custom_widget_hook`, который создаёт и
    возвращает виджет текста с номерами строк."""
    # Создаём и настраиваем виджет текста с номерами строк
    urls_widget = LineNumberedText(column_element.TKColFrame)
    urls_widget.pack(side='top', fill='both', expand=True)
    urls_widget.text.configure(background=COLOR_WHITE,
                               font=('Consolas', FONT_SIZE_BASE),
                               foreground=COLOR_TEXT_PRIMARY,
                               highlightthickness=1,
                               highlightbackground=COLOR_BORDER,
                               selectbackground=COLOR_ACCENT,
                               selectforeground=COLOR_WHITE,
                               insertbackground=COLOR_TEXT_PRIMARY,
                               padx=SPACING_MD,
                               pady=SPACING_MD)

    setup_text_widget(urls_widget.text, toplevel_form.TKroot)
    return urls_widget


@ensure_gui_enabled
def gui_urls_editor(urls: list[str]) -> list[str] | None:
    """Запускает редактор URL.

    Args:
        urls: Текущие установленные URL.

    Returns:
        Список URL или `None` при отмене.
    """
    # Применяем современную тему
    apply_theme('modern')

    # Стили для элементов
    button_style = {'button_color': (COLOR_WHITE, COLOR_ACCENT),
                    'border_width': 0,
                    'font': get_font(FONT_SIZE_BASE),
                    'pad': (SPACING_SM, SPACING_XS)}
    
    button_secondary_style = {'button_color': (COLOR_TEXT_PRIMARY, COLOR_BACKGROUND_SECONDARY),
                              'border_width': 0,
                              'font': get_font(FONT_SIZE_BASE),
                              'pad': (SPACING_SM, SPACING_XS)}

    # Window layout - современный дизайн
    layout = [
        # Заголовок
        [
            sg.Column([
                [
                    sg.Text('Редактор ссылок', font=get_font(FONT_SIZE_XL, 'bold'), 
                            text_color=COLOR_TEXT_PRIMARY, pad=(SPACING_LG, SPACING_MD)),
                ],
            ], background_color=COLOR_BACKGROUND, pad=0),
        ],
        
        # Подсказка
        [
            sg.Column([
                [
                    sg.Text('Введите URL для парсинга (каждая ссылка с новой строки)', 
                            font=get_font(FONT_SIZE_SM), 
                            text_color=COLOR_TEXT_SECONDARY, 
                            pad=(SPACING_MD, SPACING_XS)),
                ],
            ], background_color=COLOR_BACKGROUND_SECONDARY, expand_x=True),
        ],
        
        # Текстовое поле для URL
        [
            sg.Column([[]], key='-COL_URLS-', size=(0, 0,), 
                      expand_x=True, expand_y=True,
                      background_color=COLOR_BACKGROUND,
                      pad=SPACING_MD),
        ],
        
        # Кнопки управления
        [
            sg.Column([
                [
                    sg.Button('✅ OK', size=(10, 1), key='-BTN_OK-',
                              **button_style),
                    sg.Button('🛠 Генерировать', size=(14, 1), key='-BTN_BUILD-',
                              **button_style),
                    sg.Button('🌍 Города', size=(10, 1), key='-BTN_CITIES-',
                              **button_style),
                    sg.Button('✕ Отмена', size=(10, 1), key='-BTN_CANCEL-',
                              **button_secondary_style),
                ],
            ], expand_x=True, element_justification='right',
               background_color=COLOR_BACKGROUND, pad=SPACING_MD),
        ],
    ]

    with invoke_widget_hook(sg.PySimpleGUI, '-COL_URLS-', create_text_widget) as get_widget:
        window = sg.Window('Редактор ссылок', layout=layout, finalize=True, 
                           auto_size_text=True, font=get_font(FONT_SIZE_BASE),
                           modal=True, keep_on_top=True,
                           resizable=True, size=(700, 500), 
                           min_size=(500, 350))

        # Get `LineNumberedText` widget
        urls_widget = get_widget()
        assert urls_widget

    # Insert existing links
    urls_widget.text.insert('insert', '\n'.join(urls))

    # Focus on custom widget
    urls_widget.text.focus_set()

    # Result urls
    ret_urls = None

    # Main loop
    while True:
        event, _ = window.read()
        if event in (None, '-BTN_CANCEL-'):
            break

        elif event == '-BTN_BUILD-':
            urls = gui_urls_generator()
            if urls:
                urls_content = urls_widget.text.get('1.0', 'end')[:-1]
                join_character = '\n' if urls_content and urls_content[-1:] != '\n' else ''
                urls_widget.text.insert('end', join_character + '\n'.join(urls))

        elif event == '-BTN_CITIES-':
            from .city_selector import gui_city_selector
            selected_cities = gui_city_selector()
            if selected_cities:
                # Запрашиваем поисковый запрос
                query = sg.popup_get_text('Введите поисковый запрос:', title='Генерация URL по городам',
                                          default_text='Организации')
                if query:
                    from ..common import generate_city_urls
                    generated_urls = generate_city_urls(selected_cities, query)
                    if generated_urls:
                        urls_content = urls_widget.text.get('1.0', 'end')[:-1]
                        join_character = '\n' if urls_content and urls_content[-1:] != '\n' else ''
                        urls_widget.text.insert('end', join_character + '\n'.join(generated_urls))

        elif event == '-BTN_OK-':
            urls_content = urls_widget.text.get('1.0', 'end')[:-1]
            ret_urls = [x for x in urls_content.splitlines() if x.strip()]
            break

    window.close()
    del window

    return ret_urls
