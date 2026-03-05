"""
GUI для выбора категорий для парсинга.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..common import GUI_ENABLED
from ..data.categories_93 import CATEGORIES_93
from .theme import (COLOR_ACCENT, COLOR_BACKGROUND, COLOR_BACKGROUND_SECONDARY,
                    COLOR_TEXT_PRIMARY, COLOR_WHITE, FONT_SIZE_BASE, FONT_SIZE_MD,
                    FONT_SIZE_XL, SPACING_LG, SPACING_MD, SPACING_SM,
                    SPACING_XS, apply_theme, get_font)
from .utils import ensure_gui_enabled

if TYPE_CHECKING:
    pass

if GUI_ENABLED:
    import PySimpleGUI as sg


@ensure_gui_enabled
def gui_category_selector() -> list[dict] | None:
    """
    Запускает селектор категорий для парсинга.

    Returns:
        Список выбранных категорий или None если отменено.
    """
    # Применяем современную тему
    apply_theme('modern')

    # Стили для элементов
    checkbox_style = {'background_color': COLOR_BACKGROUND,
                      'text_color': COLOR_TEXT_PRIMARY,
                      'font': get_font(FONT_SIZE_BASE),
                      'checkbox_color': COLOR_ACCENT,
                      'pad': ((0, SPACING_SM), (SPACING_XS, SPACING_XS))}

    frame_style = {'background_color': COLOR_BACKGROUND,
                   'title_color': COLOR_TEXT_PRIMARY,
                   'font': get_font(FONT_SIZE_MD, 'bold'),
                   'border_width': 1,
                   'pad': (SPACING_MD, SPACING_SM),
                   'relief': 'flat'}

    button_style = {'button_color': (COLOR_WHITE, COLOR_ACCENT),
                    'border_width': 0,
                    'font': get_font(FONT_SIZE_BASE),
                    'pad': (SPACING_SM, SPACING_XS)}

    button_secondary_style = {'button_color': (COLOR_TEXT_PRIMARY, COLOR_BACKGROUND_SECONDARY),
                              'border_width': 0,
                              'font': get_font(FONT_SIZE_BASE),
                              'pad': (SPACING_SM, SPACING_XS)}

    # Группируем категории по разделам
    categories_groups = {
        'Общественное питание (1-15)': list(range(0, 15)),
        'Гостиницы (16-20)': list(range(15, 20)),
        'Досуг и развлечения (21-34)': list(range(20, 34)),
        'Магазины (35-42)': list(range(34, 42)),
        'Красота и здоровье (43-47)': list(range(42, 47)),
        'Спорт и фитнес (48-50)': list(range(47, 50)),
        'Медицина (51-54)': list(range(50, 54)),
        'Финансы и услуги (55-61)': list(range(54, 61)),
        'Бытовые услуги (62-65)': list(range(61, 65)),
        'Авто (66-70)': list(range(65, 70)),
        'Образование (71-77)': list(range(70, 77)),
        'Госучреждения (78-84)': list(range(77, 84)),
        'Религия (85-87)': list(range(84, 87)),
        'Прочее (88-93)': list(range(87, 93)),
    }

    # Создаём чекбоксы для каждой группы
    group_checkboxes = {}
    category_checkboxes = {}

    for group_name, indices in categories_groups.items():
        layout = []
        for idx in indices:
            cat = CATEGORIES_93[idx]
            cb = sg.Checkbox(
                cat['name'],
                key=f'-CAT_{idx}-',
                metadata=cat,
                **checkbox_style
            )
            layout.append([cb])
            category_checkboxes[idx] = cb

        group_checkboxes[group_name] = sg.Column(
            layout,
            scrollable=True,
            vertical_scroll_only=True,
            expand_x=True,
            expand_y=True,
            visible=False,
            background_color=COLOR_BACKGROUND
        )

    # Получаем размеры экрана
    _, screen_height = sg.Window.get_screen_size()

    # Макет окна
    layout = [
        # Заголовок
        [
            sg.Column([
                [
                    sg.Text('Выбор категорий', font=get_font(FONT_SIZE_XL, 'bold'),
                            text_color=COLOR_TEXT_PRIMARY, pad=(SPACING_LG, SPACING_MD)),
                ],
            ], background_color=COLOR_BACKGROUND, pad=0),
        ],

        # Выбор группы
        [
            sg.Frame('Группа категорий', layout=[
                [
                    sg.Column([
                        [
                            sg.Text('Выберите группу', font=get_font(FONT_SIZE_MD),
                                    text_color=COLOR_TEXT_PRIMARY, pad=(0, SPACING_XS)),
                            sg.Combo(
                                key='-GROUP-',
                                values=list(categories_groups.keys()),
                                readonly=True,
                                enable_events=True,
                                font=get_font(FONT_SIZE_BASE),
                                background_color=COLOR_WHITE,
                                size=(35, 1)
                            ),
                        ],
                    ], expand_x=True, pad=SPACING_MD),
                ],
            ], **frame_style, expand_x=True),
        ],

        # Категории
        [
            sg.Frame('Категории', layout=[
                [
                    sg.Column(
                        list(group_checkboxes.values()),
                        expand_x=True,
                        expand_y=True,
                        background_color=COLOR_BACKGROUND
                    ),
                ],
            ], **frame_style, size=(None, int(screen_height / 3)),
               expand_x=True, expand_y=True),
        ],

        # Кнопки управления
        [
            sg.Column([
                [
                    sg.Button('✅ OK', size=(10, 1), key='-BTN_OK-', **button_style),
                    sg.Button('🗀 Выделить всё', size=(14, 1), key='-BTN_SELECT_ALL-', **button_secondary_style),
                    sg.Button('🗅 Снять выделение', size=(18, 1), key='-BTN_DESELECT_ALL-', **button_secondary_style),
                    sg.Button('🗋 Инвертировать', size=(14, 1), key='-BTN_INVERT-', **button_secondary_style),
                ],
            ], expand_x=True, element_justification='right',
               background_color=COLOR_BACKGROUND, pad=SPACING_MD),
        ],
    ]

    window = sg.Window(
        'Выбор категорий',
        layout=layout,
        auto_size_text=True,
        finalize=True,
        font=get_font(FONT_SIZE_BASE),
        modal=True,
        keep_on_top=True,
        resizable=True,
        size=(700, 550),
        min_size=(600, 450)
    )

    # Устанавливаем первую группу видимой
    first_group = list(categories_groups.keys())[0]
    for group_name, column_element in group_checkboxes.items():
        column_element.update(visible=(group_name == first_group))

    # Результат
    ret_categories = None

    # Главный цикл
    while True:
        event, values = window.read()

        if event in (None, '-BTN_CANCEL-'):
            break

        elif event == '-GROUP-':
            # Показываем выбранную группу
            selected_group = values['-GROUP-']
            for group_name, column_element in group_checkboxes.items():
                column_element.update(visible=(group_name == selected_group))

        elif event == '-BTN_SELECT_ALL-':
            selected_group = values['-GROUP-']
            indices = categories_groups[selected_group]
            for idx in indices:
                window[f'-CAT_{idx}-'].update(True)

        elif event == '-BTN_DESELECT_ALL-':
            selected_group = values['-GROUP-']
            indices = categories_groups[selected_group]
            for idx in indices:
                window[f'-CAT_{idx}-'].update(False)

        elif event == '-BTN_INVERT-':
            selected_group = values['-GROUP-']
            indices = categories_groups[selected_group]
            for idx in indices:
                current = window[f'-CAT_{idx}-'].get()
                window[f'-CAT_{idx}-'].update(not current)

        elif event == '-BTN_OK-':
            # Собираем все выбранные категории
            ret_categories = []
            for idx, checkbox in category_checkboxes.items():
                if checkbox.get():
                    ret_categories.append(checkbox.metadata)

            if not ret_categories:
                sg.popup_error(
                    'Необходимо выбрать категории!\n\nВыберите хотя бы одну категорию для парсинга.',
                    font=get_font(FONT_SIZE_BASE),
                    background_color=COLOR_BACKGROUND,
                    text_color=COLOR_TEXT_PRIMARY,
                    button_color=(COLOR_WHITE, COLOR_ACCENT)
                )
                continue

            break

    window.close()
    del window

    return ret_categories
