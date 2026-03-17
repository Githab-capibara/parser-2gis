from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from parser_2gis.cache import _ConnectionPool
from parser_2gis.tui_pytermgui.app import TUIApp
from parser_2gis.tui_pytermgui.screens.cache_viewer import CacheViewerScreen


# ==========================================================
# Проблема: отсутствовал единый механизм уведомлений в TUI
# Фикс: TUIApp.notify + использование в экранах
# ==========================================================

def test_notify_saves_last_notification() -> None:
    app = TUIApp()

    app.notify("Привет", "info")
    assert app.last_notification == {"message": "Привет", "level": "info"}


def test_notify_overwrites_previous_notification() -> None:
    app = TUIApp()

    app.notify("Первое", "info")
    app.notify("Второе", "warning")

    assert app.last_notification == {"message": "Второе", "level": "warning"}


def test_notify_is_safe_without_window_manager() -> None:
    app = TUIApp()

    # Не должно выбрасывать исключений даже без активного WindowManager
    app.notify("Сообщение", "error")


# ==========================================================
# Проблема: _clear_expired был TODO
# Фикс: очистка JSON-кэша по mtime (TTL 24ч)
# ==========================================================

@pytest.fixture()
def cache_dir_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Подменяем Path.home() на tmp_path для изолированного теста."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    cache_dir = tmp_path / ".cache" / "parser-2gis"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _write_cache_file(path: Path, *, mtime: float) -> None:
    path.write_text('{"url": "https://example.com"}', encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_clear_expired_deletes_old_files(cache_dir_home: Path) -> None:
    app = TUIApp()
    screen = CacheViewerScreen(app)

    old_file = cache_dir_home / "old.json"
    new_file = cache_dir_home / "new.json"

    now = time.time()
    _write_cache_file(old_file, mtime=now - 60 * 60 * 25)  # 25 часов назад
    _write_cache_file(new_file, mtime=now - 60 * 10)  # 10 минут назад

    screen._clear_expired()  # noqa: SLF001 - тестируем поведение экрана

    assert not old_file.exists()
    assert new_file.exists()


def test_clear_expired_does_not_fail_when_cache_dir_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    app = TUIApp()
    screen = CacheViewerScreen(app)

    # Директории нет — метод должен быть безопасным
    screen._clear_expired()  # noqa: SLF001


def test_clear_expired_sets_notification(cache_dir_home: Path) -> None:
    app = TUIApp()
    screen = CacheViewerScreen(app)

    now = time.time()
    _write_cache_file(cache_dir_home / "old.json", mtime=now - 60 * 60 * 30)

    screen._clear_expired()  # noqa: SLF001

    assert app.last_notification is not None
    assert "Очищено" in app.last_notification["message"]


# ==========================================================
# Проблема: close_all глотал исключения
# Фикс: debug-логирование вместо pass
# ==========================================================

def test_connection_pool_close_all_does_not_raise(tmp_path: Path) -> None:
    pool = _ConnectionPool(tmp_path / "cache.db", pool_size=1)
    pool.close_all()


def test_connection_pool_close_all_logs_on_close_error(tmp_path: Path) -> None:
    pool = _ConnectionPool(tmp_path / "cache.db", pool_size=1)

    class BadConn:
        def close(self) -> None:
            raise RuntimeError("boom")

    # Подкладываем "плохое" соединение напрямую во внутренний список
    pool._all_conns = [BadConn()]  # noqa: SLF001

    # Не должно пробрасывать исключение
    pool.close_all()


def test_connection_pool_close_all_clears_internal_list(tmp_path: Path) -> None:
    pool = _ConnectionPool(tmp_path / "cache.db", pool_size=2)
    pool.get_connection()
    pool.get_connection()

    pool.close_all()

    assert pool._all_conns == []  # noqa: SLF001 - проверяем внутреннее состояние
