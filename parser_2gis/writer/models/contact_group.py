"""Модель контактной информации организации.

Предоставляет классы для представления контактов:
- Contact - отдельный контакт (email, website, phone и т.д.)
- ContactGroup - группа контактов с расписанием и комментарием
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from .schedule import Schedule


class Contact(BaseModel):
    """Модель контактной информации.

    Атрибуты:
        type: Тип контакта. Возможные значения: `email`, `website`, `phone`, `fax`, `icq`, `jabber`,
               `skype`, `vkontakte`, `twitter`, `instagram`, `facebook`, `pobox`, `youtube`,
               `odnoklassniki`, `googleplus`, `linkedin`, `pinterest`, `whatsapp`, `telegram`, `viber`.
        value: Техническое значение контакта (например "Телефон в международном формате").
        text: Значение контакта для вывода на экран (например "e-mail Иванова").
        url: Ссылка на сайт или социальную сеть.
        print_text: Значение контакта для вывода на принтер (например "e-mail Иванова").
        comment: Уточняющая информация о контакте (например "для деловой переписки").
    """

    # Тип контакта.
    # Возможные значения:
    # * `email` — электронная почта
    # * `website` — сайт, протокол http
    # * `phone` — телефон
    # * `fax` — факс
    # * `icq` — аккаунт в ICQ
    # * `jabber` — Jabber
    # * `skype` — Skype
    # * `vkontakte` — ВКонтакте
    # * `twitter` — Twitter
    # * `instagram` — Instagram
    # * `facebook` — Facebook
    # * `pobox` — P.O.Box (абонентский ящик)
    # * `youtube` — Youtube
    # * `odnoklassniki` — ok.ru
    # * `googleplus` — Google +
    # * `linkedin` — Linkedin
    # * `pinterest` — Pinterest
    # * `whatsapp` — Whatsapp
    # * `telegram` — Telegram
    # * `viber` — Viber
    type: str

    # Техническое значение контакта (например "Телефон в международном формате")
    value: str

    # Значение контакта для вывода на экран (например "e-mail Иванова")
    text: str | None = None

    # Ссылка на сайт или социальную сеть
    url: str | None = None

    # Значение контакта для вывода на принтер (например "e-mail Иванова")
    print_text: str | None = None

    # Уточняющая информация о контакте (например "для деловой переписки")
    comment: str | None = None


class ContactGroup(BaseModel):
    """Модель группы контактов организации.

    Атрибуты:
        contacts: Список контактов.
        schedule: Расписание группы контактов.
        comment: Комментарий к группе контактов (например "Многокональный телефон").
        name: Имя группы контактов (например "Сервисный центр").
    """

    # Список контактов
    contacts: list[Contact] = []

    # Расписание группы контактов
    schedule: Schedule | None = None

    # Комментарий к группе контактов (например "Многокональный телефон")
    comment: str | None = None

    # Имя группы контактов (например "Сервисный центр")
    name: str | None = None
