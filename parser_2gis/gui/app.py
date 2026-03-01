from __future__ import annotations

import queue
import webbrowser
from functools import partial
from typing import TYPE_CHECKING

from ..common import GUI_ENABLED, running_linux, running_windows
from ..logger import logger, setup_cli_logger, setup_gui_logger
from ..paths import image_data, image_path
from ..runner import GUIRunner
from ..version import version
from .error_popup import gui_error_popup
from .settings import gui_settings
from .theme import (COLOR_ACCENT, COLOR_ACCENT_HOVER, COLOR_BACKGROUND,
                    COLOR_BACKGROUND_SECONDARY, COLOR_BORDER, COLOR_ERROR,
                    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_WHITE,
                    ELEMENT_HEIGHT_LG, ELEMENT_HEIGHT_MD, FONT_SIZE_BASE,
                    FONT_SIZE_LG, FONT_SIZE_MD, FONT_SIZE_SM, FONT_SIZE_XL,
                    RADIUS_LG, RADIUS_MD, SPACING_LG, SPACING_MD, SPACING_SM,
                    SPACING_XS, apply_theme, get_font)
from .utils import (ensure_gui_enabled, generate_event_handler,
                    setup_text_widget)

if TYPE_CHECKING:
    from ..config import Configuration

if GUI_ENABLED:
    import tkinter as tk

    import PySimpleGUI as sg


@ensure_gui_enabled
def gui_app(urls: list[str], output_path: str, format: str, config: Configuration) -> None:
    """Run GUI.

    Args:
        url: 2GIS URLs with results to be collected.
        output_path: Path to the result file.
        format: `csv`, `xlsx` or `json` format.
        config: User configuration.
    """
    # Применяем современную тему
    apply_theme('modern')

    # Set icon
    sg.set_global_icon(image_data('icon', 'png'))

    # Setup main CLI logger
    setup_cli_logger(config.log)

    # Result format
    default_result_format = format if format else 'csv'
    result_filetype = {'csv': [('CSV Table', '*.csv')],
                       'xlsx': [('Microsoft Excel Spreadsheet', '*.xlsx')],
                       'json': [('JSON', '*.json')]}

    # If urls wasn't passed then let it be an empty list
    if urls is None:
        urls = []

    # Современные стили для элементов
    button_style = {'button_color': (COLOR_WHITE, COLOR_ACCENT),
                    'border_width': 0,
                    'pad': (SPACING_SM, SPACING_SM)}
    
    input_style = {'background_color': COLOR_WHITE,
                   'text_color': COLOR_TEXT_PRIMARY,
                   'font': get_font(FONT_SIZE_BASE)}
    
    frame_style = {'background_color': COLOR_BACKGROUND,
                   'title_color': COLOR_TEXT_PRIMARY,
                   'font': get_font(FONT_SIZE_MD, 'bold'),
                   'border_width': 1,
                   'border_color': COLOR_BORDER,
                   'pad': (SPACING_MD, SPACING_MD),
                   'element_padding': (SPACING_MD, SPACING_SM)}

    # Window layout - современный дизайн с боковой панелью
    layout = [
        # Верхняя панель с заголовком и настройками
        [
            sg.Column([
                [
                    sg.Text('Парсер 2GIS', font=get_font(FONT_SIZE_XL, 'bold'), 
                            text_color=COLOR_TEXT_PRIMARY, pad=(SPACING_LG, SPACING_MD)),
                    sg.Text(f'v{version}', font=get_font(FONT_SIZE_SM), 
                            text_color=COLOR_TEXT_SECONDARY, pad=(0, SPACING_MD)),
                ],
            ], background_color=COLOR_BACKGROUND, pad=0),
            sg.Column([
                [
                    sg.Button('', image_data=image_data('settings'), key='-BTN_SETTINGS-', 
                              tooltip=f'Настройки: {config.path}', 
                              button_color=(COLOR_TEXT_SECONDARY, COLOR_BACKGROUND),
                              border_width=0, pad=(SPACING_SM, SPACING_MD)),
                ],
            ], element_justification='right', background_color=COLOR_BACKGROUND, pad=0),
        ],
        
        # Основная рабочая область
        [
            sg.Frame('Параметры парсинга', expand_x=True, layout=[
                [
                    sg.Column([
                        [
                            sg.Text('URL для парсинга', font=get_font(FONT_SIZE_MD), 
                                    text_color=COLOR_TEXT_SECONDARY, pad=(0, SPACING_XS)),
                        ],
                        [
                            sg.Input(key='-IN_URL-', use_readonly_for_disable=True, expand_x=True,
                                     font=get_font(FONT_SIZE_BASE), background_color=COLOR_WHITE),
                            sg.Button('Редактор', key='-BTN_URLS-', size=(10, 1), 
                                      button_color=(COLOR_WHITE, COLOR_ACCENT), border_width=0),
                        ],
                    ], expand_x=True, pad=SPACING_LG),
                ],
            ], **frame_style, relief='flat', title_location='top'),
        ],
        
        # Настройки результата
        [
            sg.Frame('Результат', expand_x=True, layout=[
                [
                    sg.Column([
                        [
                            sg.Text('Формат файла', font=get_font(FONT_SIZE_MD), 
                                    text_color=COLOR_TEXT_SECONDARY, pad=(0, SPACING_XS)),
                        ],
                        [
                            sg.Combo(key='-FILE_FORMAT-', default_value=default_result_format,
                                     values=['csv', 'xlsx', 'json'], readonly=True, enable_events=True,
                                     font=get_font(FONT_SIZE_BASE), background_color=COLOR_WHITE,
                                     size=(10, 1)),
                            sg.Text('Путь к файлу', font=get_font(FONT_SIZE_MD), 
                                    text_color=COLOR_TEXT_SECONDARY, pad=((SPACING_LG, SPACING_XS), 0)),
                        ],
                        [
                            sg.Input(key='-OUTPUT_PATH-', expand_x=True,
                                     default_text='' if output_path is None else output_path,
                                     font=get_font(FONT_SIZE_BASE), background_color=COLOR_WHITE),
                            sg.FileSaveAs(key='-OUTPUT_PATH_BROWSE-', button_text='Обзор', 
                                          size=(8, 1), button_color=(COLOR_WHITE, COLOR_ACCENT),
                                          border_width=0, default_extension=f'.{default_result_format}',
                                          file_types=result_filetype[default_result_format]),
                        ],
                    ], expand_x=True, pad=SPACING_LG),
                ],
            ], **frame_style, relief='flat'),
        ],
        
        # Лог выполнения
        [
            sg.Frame('Лог выполнения', expand_x=True, expand_y=True, layout=[
                [
                    sg.Multiline(key='-LOG-', size=(80, 15), expand_x=True, expand_y=True,
                                 autoscroll=True, reroute_stdout=True, reroute_stderr=True,
                                 echo_stdout_stderr=True, font=get_font(FONT_SIZE_BASE, 'normal'),
                                 background_color=COLOR_BACKGROUND_SECONDARY,
                                 text_color=COLOR_TEXT_PRIMARY,
                                 no_scrollbar=False,
                                 vertical_scroll_only=False),
                ],
            ], **frame_style, relief='flat'),
        ],
        
        # Нижняя панель с логотипом и кнопками управления
        [
            sg.Column([
                [
                    sg.Image(data=image_data('logo'), key='-IMG_LOGO-',
                             enable_events=True, background_color=COLOR_BACKGROUND,
                             tooltip='Открыть GitHub репозиторий'),
                ],
            ], size=(80, 80), pad=(SPACING_LG, SPACING_MD)),
            
            sg.Column([
                [
                    sg.Image(key='-IMG_LOADING-', visible=False, 
                             background_color=COLOR_BACKGROUND),
                ],
            ], expand_x=True, element_justification='center', pad=SPACING_LG),
            
            sg.Column([
                [
                    sg.Button('▶ Запуск', key='-BTN_START-', size=(12, 1), 
                              button_color=(COLOR_WHITE, COLOR_ACCENT),
                              border_width=0, font=get_font(FONT_SIZE_MD, 'bold'),
                              pad=((SPACING_MD, SPACING_SM), SPACING_MD)),
                    sg.Button('⏹ Стоп', key='-BTN_STOP-', size=(10, 1), 
                              button_color=(COLOR_WHITE, '#FF9500'), 
                              border_width=0, font=get_font(FONT_SIZE_MD, 'bold'),
                              visible=False, pad=((SPACING_SM, SPACING_SM), SPACING_MD)),
                    sg.Button('✕ Выход', size=(10, 1), 
                              button_color=(COLOR_WHITE, COLOR_ERROR),
                              border_width=0, font=get_font(FONT_SIZE_MD),
                              key='-BTN_EXIT-', pad=((SPACING_SM, SPACING_LG), SPACING_MD)),
                ],
            ], element_justification='right', pad=0),
        ],
    ]

    # tkinter could encounter encoding problem with cyrillics characters on linux systems (toolbar, topbar),
    # so let the window titles be in English. No big deal, actually.
    window_title = 'Parser 2GIS' if running_linux() else 'Парсер 2GIS'

    # Main window с современными параметрами
    window = sg.Window(
        window_title, 
        layout, 
        auto_size_text=True, 
        finalize=True, 
        font=get_font(FONT_SIZE_BASE),
        margins=(0, 0),
        use_custom_titlebar=False,
        keep_on_top=False,
        resizable=True,
        size=(1000, 700),
        min_size=(800, 500),
    )

    # Setup text widgets
    setup_text_widget(window['-IN_URL-'].widget, window.TKroot, menu_clear=False, set_focus=True)
    setup_text_widget(window['-OUTPUT_PATH-'].widget, window.TKroot, menu_clear=False)
    setup_text_widget(window['-LOG-'].widget, window.TKroot, menu_paste=False, menu_cut=False)

    # Forbid user to edit output console,
    # block any keys except ctl+c, ←, ↑, →, ↓
    def log_key_handler(e: tk.Event) -> str | None:
        if e.char == '\x03' or e.keysym in ('Left', 'Up', 'Right', 'Down'):
            return None

        return 'break'

    window['-LOG-'].widget.bind('<Key>', log_key_handler)
    window['-LOG-'].widget.bind('<<Paste>>', lambda e: 'break')
    window['-LOG-'].widget.bind('<<Cut>>', lambda e: 'break')

    # Enable logging queue to be able to handle log in the mainloop
    log_queue: queue.Queue[tuple[str, str]] = queue.Queue()  # Queue of log messages (log_level, log_message)
    setup_gui_logger(log_queue, config.log)

    # Hand cursor for logo
    window['-IMG_LOGO-'].widget.config(cursor='hand2')

    # Set config settings button hover/click image
    def change_settings_image(image_name: str) -> None:
        window['-BTN_SETTINGS-'].update(image_data=image_data(image_name))  # noqa: F821

    window['-BTN_SETTINGS-'].TKButton.bind(
        '<Button>' if running_windows() else '<Enter>',
        generate_event_handler(partial(change_settings_image, 'settings_inverted')))

    window['-BTN_SETTINGS-'].TKButton.bind(
        '<ButtonRelease>' if running_windows() else '<Leave>',
        generate_event_handler(partial(change_settings_image, 'settings')))

    # Move cursor to the end of the URL input
    window['-IN_URL-'].widget.icursor('end')

    # Parsing thread
    parsing_thread: GUIRunner | None = None

    def parsing_thread_running() -> bool:
        return parsing_thread is not None and parsing_thread.is_alive()

    # Update URL Input element according to `urls` list
    def update_urls_input() -> None:
        urls_length = len(urls) if isinstance(urls, list) else 0
        if urls_length == 0:
            window['-IN_URL-'].update('', disabled=False)  # noqa: F821
        elif urls_length == 1:
            window['-IN_URL-'].update(urls[0], disabled=False)  # noqa: F821
        else:
            def get_plural() -> str:
                last_1d = urls_length % 10
                last_2d = urls_length % 100
                if 11 <= last_2d <= 19:
                    return 'ссылок'
                if last_1d == 1:
                    return 'ссылка'
                elif 2 <= last_1d <= 4:
                    return 'ссылки'
                return 'ссылок'

            window['-IN_URL-'].update(f'<{len(urls)} {get_plural()}>', disabled=True)  # noqa: F821

    update_urls_input()

    # Set log background colors by level - современные цвета
    log_colors = {
        'CRITICAL': COLOR_LOG_CRITICAL,
        'ERROR': COLOR_LOG_ERROR,
        'WARNING': COLOR_LOG_WARNING,
        'INFO': COLOR_LOG_INFO,
        'SUCCESS': COLOR_LOG_SUCCESS,
    }

    # Pre-define log tags с современными цветами
    for level, color in log_colors.items():
        tag = f'Multiline(None,{color},None)'
        window['-LOG-'].tags.add(tag)
        window['-LOG-'].widget.tag_configure(tag, background=color)

    # Keep selection tag priority on top
    window['-LOG-'].widget.tag_raise('sel')

    # Main loop
    while True:
        event, values = window.Read(timeout=50)

        # App exit
        if event in (None, '-BTN_EXIT-'):
            if parsing_thread_running():
                assert parsing_thread
                parsing_thread.stop()
                parsing_thread.join()

            break

        # Run settings
        elif event == '-BTN_SETTINGS-':
            gui_settings(config)

        # Run URLs Editor
        elif event == '-BTN_URLS-':
            # Sync urls with input element
            if not window['-IN_URL-'].Disabled:
                urls = [values['-IN_URL-']]

            ret_urls = gui_urls_editor(urls)
            if ret_urls is not None:
                urls = ret_urls
                update_urls_input()

        # Select output file format
        elif event == '-FILE_FORMAT-':
            file_format = values['-FILE_FORMAT-']
            if file_format in result_filetype:
                window['-OUTPUT_PATH_BROWSE-'].FileTypes = result_filetype[file_format]
                window['-OUTPUT_PATH_BROWSE-'].DefaultExtension = f'.{file_format}'

        # Click logo
        elif event == '-IMG_LOGO-':
            webbrowser.open('https://github.com/interlark/parser-2gis')

        # Click stop
        elif event == '-BTN_STOP-':
            if parsing_thread_running():
                logger.warn('Парсинг остановлен пользователем.')
                assert parsing_thread
                parsing_thread.stop()

                # Disable button until the thread fully stops
                window['-BTN_STOP-'].update(disabled=True)

        # Click start
        elif event == '-BTN_START-':
            # Check output file path
            if not values['-OUTPUT_PATH-']:
                gui_error_popup('Отсутствует путь результирующего файла!\n\nУкажите файл для сохранения результатов парсинга.')
                continue

            # Check output file path
            if not values['-IN_URL-']:
                gui_error_popup('Отсутствует URL!\n\nВведите URL для парсинга или используйте редактор ссылок.')
                continue

            # Check result format
            if values['-FILE_FORMAT-'] not in ('csv', 'xlsx', 'json'):
                gui_error_popup('Формат результирующего файла должен быть csv, xlsx или json!')
                continue

            # Check if result format match output file extension
            if values['-OUTPUT_PATH-'].split('.')[-1].lower() != values['-FILE_FORMAT-']:
                gui_error_popup(f'Расширение результирующего файла должно быть *.{values["-FILE_FORMAT-"]}!')
                continue

            # Sync urls with input element
            if not window['-IN_URL-'].Disabled:
                urls = [values['-IN_URL-']]

            # Run parser
            if not parsing_thread_running():
                parsing_thread = GUIRunner(urls, values['-OUTPUT_PATH-'], values['-FILE_FORMAT-'], config)
                parsing_thread.start()

                # Activate stop button if it's been disabled
                window['-BTN_STOP-'].update(disabled=False)

        # Poll log queue
        while True:
            try:
                log_level, log_msg = log_queue.get(block=False)
            except queue.Empty:
                break
            else:
                # Print message to log
                window['-LOG-'].update(log_msg, append=True,
                                       background_color_for_value=log_colors.get(log_level, None))

        # Swap start/stop buttons
        if parsing_thread_running():
            if window['-BTN_START-'].visible:
                window['-BTN_START-'].update(visible=False)

            if not window['-BTN_STOP-'].visible:
                window['-BTN_STOP-'].update(visible=True)

            if not window['-IMG_LOADING-'].visible:
                window['-IMG_LOADING-'].update(visible=True)

            # Run loading animation
            window['-IMG_LOADING-'].update_animation(image_path('loading'), time_between_frames=50)
        else:
            if not window['-BTN_START-'].visible:
                window['-BTN_START-'].update(visible=True)

            if window['-BTN_STOP-'].visible:
                window['-BTN_STOP-'].update(visible=False)

            if window['-IMG_LOADING-'].visible:
                window['-IMG_LOADING-'].update(visible=False)

    window.close()
    del window
