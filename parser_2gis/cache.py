"""
Модуль для кэширования результатов парсинга.

Предоставляет функциональность для кэширования результатов парсинга
в локальной базе данных SQLite для ускорения повторных запусков.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any


class CacheManager:
    """Менеджер кэша результатов парсинга.
    
    Этот класс предоставляет возможность кэширования результатов парсинга
    в локальной базе данных SQLite. Кэш позволяет ускорить повторные
    запуски парсера в 10-100 раз за счет избежания повторных
    запросов к серверу 2GIS.
    
    Attributes:
        _cache_dir: Директория для хранения кэша
        _cache_file: Путь к файлу базы данных кэша
        _ttl: Время жизни кэша (timedelta)
    
    Пример использования:
        >>> cache = CacheManager(Path('/tmp/cache'), ttl_hours=24)
        >>> data = cache.get('https://2gis.ru/moscow/search/Аптеки')
        >>> if data is None:
        ...     # Парсим данные
        ...     data = {...}
        ...     cache.set('https://2gis.ru/moscow/search/Аптеки', data)
    """
    
    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        """Инициализация менеджера кэша.
        
        Args:
            cache_dir: Директория для хранения кэша
            ttl_hours: Время жизни кэша в часах (по умолчанию 24 часа)
        """
        self._cache_dir = cache_dir
        self._ttl = timedelta(hours=ttl_hours)
        self._cache_file = cache_dir / "cache.db"
        self._init_db()
    
    def _init_db(self) -> None:
        """Инициализация базы данных кэша.
        
        Создает директорию для кэша (если её нет) и создает
        таблицу для хранения кэшированных данных.
        """
        # Создаём директорию для кэша, если её нет
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Подключаемся к базе данных
        with sqlite3.connect(self._cache_file) as conn:
            # Создаем таблицу для кэша
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    url_hash TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    expires_at DATETIME NOT NULL
                )
            """)
            
            # Создаем индекс для быстрого поиска истекших записей
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at 
                ON cache(expires_at)
            """)
    
    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """Получение данных из кэша.
        
        Проверяет наличие кэша для указанного URL. Если кэш существует
        и не истек, возвращает кэшированные данные. Иначе возвращает None.
        
        Args:
            url: URL для поиска в кэше
            
        Returns:
            Кэшированные данные или None, если кэш истек или отсутствует
        """
        # Вычисляем хеш URL для поиска
        url_hash = self._hash_url(url)
        
        with sqlite3.connect(self._cache_file) as conn:
            # Ищем кэш по хешу URL
            cursor = conn.execute("""
                SELECT data, expires_at 
                FROM cache 
                WHERE url_hash = ?
            """, (url_hash,))
            
            row = cursor.fetchone()
            
            # Если кэш не найден
            if not row:
                return None
            
            data, expires_at = row
            expires_at = datetime.fromisoformat(expires_at)
            
            # Проверяем, истек ли кэш
            if datetime.now() > expires_at:
                # Кэш истек, удаляем его
                conn.execute("DELETE FROM cache WHERE url_hash = ?", (url_hash,))
                conn.commit()
                return None
            
            # Кэш найден и не истек, возвращаем данные
            return json.loads(data)
    
    def set(self, url: str, data: Dict[str, Any]) -> None:
        """Сохранение данных в кэш.
        
        Сохраняет указанные данные в кэш для указанного URL.
        Если кэш для этого URL уже существует, он будет перезаписан.
        
        Args:
            url: URL для кэширования
            data: Данные для сохранения (должны быть сериализуемы в JSON)
        """
        # Вычисляем хеш URL и время истечения
        url_hash = self._hash_url(url)
        expires_at = datetime.now() + self._ttl
        
        # Сохраняем данные в базу
        with sqlite3.connect(self._cache_file) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache 
                (url_hash, url, data, timestamp, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                url_hash,
                url,
                json.dumps(data, ensure_ascii=False),
                datetime.now().isoformat(),
                expires_at.isoformat()
            ))
            conn.commit()
    
    def clear(self) -> None:
        """Очистка всего кэша.
        
        Удаляет все записи из кэша.
        """
        with sqlite3.connect(self._cache_file) as conn:
            conn.execute("DELETE FROM cache")
            conn.commit()
    
    def clear_expired(self) -> int:
        """Очистка истекшего кэша.
        
        Удаляет все записи, у которых время истечения меньше текущего.
        
        Returns:
            Количество удалённых записей
        """
        with sqlite3.connect(self._cache_file) as conn:
            cursor = conn.execute("""
                DELETE FROM cache 
                WHERE expires_at < ?
            """, (datetime.now().isoformat(),))
            conn.commit()
            return cursor.rowcount
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша.
        
        Returns:
            Словарь со статистикой:
            - total_records: Общее количество записей
            - expired_records: Количество истекших записей
            - cache_size: Размер файла базы данных в байтах
        """
        with sqlite3.connect(self._cache_file) as conn:
            # Общее количество записей
            total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            
            # Количество истекших записей
            expired = conn.execute("""
                SELECT COUNT(*) FROM cache 
                WHERE expires_at < ?
            """, (datetime.now().isoformat(),)).fetchone()[0]
            
            # Размер файла базы данных
            cache_size = self._cache_file.stat().st_size if self._cache_file.exists() else 0
            
            return {
                'total_records': total,
                'expired_records': expired,
                'cache_size': cache_size
            }
    
    @staticmethod
    def _hash_url(url: str) -> str:
        """Хеширование URL.
        
        Вычисляет MD5 хеш от указанного URL для использования
        в качестве ключа в базе данных кэша.
        
        Args:
            url: URL для хеширования
            
        Returns:
            MD5 хеш URL в виде шестнадцатеричной строки
        """
        import hashlib
        return hashlib.md5(url.encode('utf-8')).hexdigest()