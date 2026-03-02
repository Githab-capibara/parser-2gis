from __future__ import annotations

import json
from typing import Any

from ..common import GUI_ENABLED, running_linux
from ..paths import data_path, image_data
from .error_popup import gui_error_popup
from .theme import (COLOR_ACCENT, COLOR_ACCENT_LIGHT, COLOR_BACKGROUND,
                    COLOR_BACKGROUND_SECONDARY, COLOR_BORDER, COLOR_TEXT_PRIMARY,
                    COLOR_TEXT_SECONDARY, COLOR_WHITE, FONT_SIZE_BASE, FONT_SIZE_LG,
                    FONT_SIZE_MD, FONT_SIZE_SM, FONT_SIZE_XL, SPACING_LG, SPACING_MD,
                    SPACING_SM, SPACING_XS, apply_theme, get_font)
from .utils import (ensure_gui_enabled, generate_event_handler,
                    invoke_widget_hook, setup_text_widget)

if GUI_ENABLED:
    import tkinter as tk
    import PySimpleGUI as sg
    from .widgets.sg import RubricsTree
    from .widgets.tk import CustomEntry


def filtered_rubrics(rubrics: dict[str, Any],
                     is_russian: bool = True) -> dict[str, Any]:
    """Фильтрует рубрики на русские/не русские узлы.

    Args:
        rubrics: Загруженный словарь рубрик.
        is_russian: Критерий фильтрации.

    Returns:
        Отфильтрованный словарь рубрик.
    """
    # Фильтрация узлов
    if is_russian:
        # Рубрики для России
        rubrics = {k: v for k, v in rubrics.items() if v.get('isRussian', True)}
    else:
        # Рубрики для нерусских стран
        rubrics = {k: v for k, v in rubrics.items() if v.get('isNonRussian', True)}

    # Исправление ссылок
    for node in rubrics.values():
        node['children'] = [x for x in node['children'] if x in rubrics]

    return rubrics


def create_search_widget(column_element: sg.Element, containing_frame: tk.Frame,
                         toplevel_form: sg.Window) -> tk.Widget:
    """Callback для `custom_widget_hook`, который создаёт и
    возвращает виджет поиска."""
    search_widget = CustomEntry(column_element.TKColFrame, width=60)
    search_widget.pack(side='top', fill='both', expand=True)
    setup_text_widget(search_widget, toplevel_form.TKroot, menu_clear=False)

    search_widget.configure(background=COLOR_WHITE,
                            font=('TkDefaultFont', FONT_SIZE_BASE),
                            highlightthickness=1,
                            highlightbackground=COLOR_BORDER,
                            highlightcolor=COLOR_ACCENT,
                            foreground=COLOR_TEXT_PRIMARY,
                            padx=SPACING_MD,
                            pady=SPACING_SM)

    return search_widget


@ensure_gui_enabled
def gui_rubric_selector(is_russian: bool = True) -> dict[str, Any] | None:
    """Запускает выбор рубрики.

    Запускает форму, которая может помочь пользователю указать рубрику.

    Args:
        is_russian: Рубрики для России или нет.

    Returns:
        Словарь, представляющий выбранную рубрику,
        или `None`, если ничего не выбрано.
    """
    # Применяем современную тему
    apply_theme('modern')

    # Находим и загружаем список рубрик
    rubric_path = data_path() / 'rubrics.json'
    if not rubric_path.is_file():
        raise FileNotFoundError(f'Файл {rubric_path} не найден')

    try:
        with open(rubric_path, 'r', encoding='utf-8') as f:
            rubrics = filtered_rubrics(json.load(f), is_russian=is_russian)
    except json.JSONDecodeError as e:
        gui_error_popup(f'Файл {rubric_path.name} повреждён:\n{e}')
        return None

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
                    sg.Text('Выбор рубрики', font=get_font(FONT_SIZE_XL, 'bold'), 
                            text_color=COLOR_TEXT_PRIMARY, pad=(SPACING_LG, SPACING_MD)),
                ],
            ], background_color=COLOR_BACKGROUND, pad=0),
        ],
        
        # Поле поиска
        [
            sg.Frame('Поиск рубрики', layout=[
                [
                    sg.Column([[]], pad=((SPACING_MD, SPACING_MD), (SPACING_SM, SPACING_SM)),
                              key='-COL_SEARCH-', expand_x=True),
                ],
            ], background_color=COLOR_BACKGROUND, border_width=1, relief='flat',
               title_font=get_font(FONT_SIZE_MD, 'bold'),
               title_color=COLOR_TEXT_PRIMARY,
               pad=(SPACING_MD, SPACING_SM)),
        ],
        
        # Дерево рубрик
        [
            sg.Frame('Дерево рубрик', layout=[
                [
                    RubricsTree(rubrics=rubrics,
                                image_parent=image_data('rubric_folder'),
                                image_item=image_data('rubric_item'),
                                headings=[], auto_size_columns=True,
                                select_mode=sg.TABLE_SELECT_MODE_BROWSE,
                                num_rows=25, col0_width=80,
                                key='-TREE-',
                                enable_events=True,
                                expand_x=True, expand_y=True,
                                background_color=COLOR_WHITE,
                                header_background_color=COLOR_BACKGROUND_SECONDARY,
                                header_text_color=COLOR_TEXT_PRIMARY,
                                text_color=COLOR_TEXT_PRIMARY,
                                selected_background_color=COLOR_ACCENT_LIGHT,
                                selected_text_color=COLOR_TEXT_PRIMARY,
                                border_width=1),
                ],
            ], background_color=COLOR_BACKGROUND, border_width=1, relief='flat',
               title_font=get_font(FONT_SIZE_MD, 'bold'),
               title_color=COLOR_TEXT_PRIMARY,
               expand_x=True, expand_y=True,
               pad=(SPACING_MD, SPACING_SM)),
        ],
        
        # Строка статуса
        [
            sg.Column([
                [
                    sg.StatusBar('', size=(0, 1), key='-STATUS-', 
                                 background_color=COLOR_BACKGROUND_SECONDARY,
                                 text_color=COLOR_TEXT_SECONDARY,
                                 font=get_font(FONT_SIZE_SM),
                                 pad=(SPACING_MD, SPACING_SM)),
                ],
            ], expand_x=True, background_color=COLOR_BACKGROUND),
        ],
        
        # Кнопки управления
        [
            sg.Column([
                [
                    sg.Button('✅ OK', size=(10, 1), key='-BTN_OK-', 
                              **button_style),
                    sg.Button('✕ Отмена', size=(10, 1), key='-BTN_CANCEL-', 
                              **button_secondary_style),
                    sg.Button('🔽 Развернуть всё', size=(16, 1), key='-BTN_EXPAND_ALL-', 
                              **button_secondary_style),
                    sg.Button('🔼 Свернуть всё', size=(15, 1), key='-BTN_COLLAPSE_ALL-', 
                              **button_secondary_style),
                ],
            ], expand_x=True, element_justification='right', 
               background_color=COLOR_BACKGROUND, pad=SPACING_MD),
        ],
    ]

    window_title = 'Select rubric' if running_linux() else 'Выбор рубрики'
    window = sg.Window(window_title, layout=layout, finalize=True, 
                       auto_size_text=True, font=get_font(FONT_SIZE_BASE),
                       modal=True, keep_on_top=True,
                       resizable=True, size=(700, 550), 
                       min_size=(550, 400))

    with invoke_widget_hook(sg.PySimpleGUI, '-COL_SEARCH-', create_search_widget) as get_widget:
        # Get search widget
        search_widget = get_widget()
        assert search_widget

    # On Linux\MacOS created window could be behind its parent
    window.bring_to_front()

    # Focus on custom widget
    search_widget.focus_set()

    # Hide tree header
    window['-TREE-'].widget.configure(show='tree')

    # Return rubric
    ret_rubric = None

    # Main loop
    while True:
        event, values = window.read()

        if event in (None, '-BTN_CANCEL-'):
            ret_rubric = None
            break

        elif event == '-BTN_OK-':
            if not ret_rubric:
                gui_error_popup('Рубрика не выбрана!\n\nВыберите рубрику из дерева или используйте поиск.')
                continue
            break

        # Update status bar
        elif event == '-TREE-':
            tree_values = values['-TREE-']
            if tree_values:
                node = rubrics[tree_values[0]]
                is_leaf = not bool(node['children'])
                if is_leaf:
                    ret_rubric = rubrics[tree_values[0]]
                    window['-STATUS-'].update(f'📁 Выбрано: {ret_rubric["label"]}')
                else:
                    ret_rubric = None
                    window['-STATUS-'].update('')

        elif event == '-BTN_EXPAND_ALL-':
            window['-TREE-'].expand()

        elif event == '-BTN_COLLAPSE_ALL-':
            window['-TREE-'].expand(expand=False)

    window.close()
    del window

    return ret_rubric
