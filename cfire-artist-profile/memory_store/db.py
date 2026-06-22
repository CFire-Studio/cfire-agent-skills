"""
数据库连接管理与初始化。

提供 SQLite 数据库的单例连接，确保整个 memory_store 模块共享同一个连接。
所有数据库文件存储在 memory_store/ 目录内，不依赖外部服务。
"""

import os
import sqlite3
import threading
from contextlib import contextmanager

# 数据库文件路径：相对于 memory_store/ 目录
_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")
_DB_PATH = os.path.join(os.path.dirname(__file__), "artist_memory.db")

_local = threading.local()


def _get_connection() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(_DB_PATH)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db() -> None:
    """初始化数据库，执行 schema.sql 建表。幂等操作，重复调用安全。"""
    conn = _get_connection()
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()


def close_db() -> None:
    """关闭当前线程的数据库连接。"""
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None


@contextmanager
def get_cursor():
    """获取数据库游标的上下文管理器，自动提交/回滚。"""
    conn = _get_connection()
    try:
        yield conn.cursor()
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def get_db_path() -> str:
    """返回当前使用的数据库文件路径。"""
    return _DB_PATH
