"""
CFIRE Artist Memory Store
=========================

基于 SQLite 的虚拟艺人记忆派生索引模块。

设计原则：Markdown 文件为权威数据源，本模块仅提供派生索引与近期上下文检索。
- memories 表：派生自 reference/MEMORY.md（由 migration 同步）
- timeline_events 表：派生自 cfire-artist-daily 的日记/内容策划 Markdown 文件
  （由 daily 技能保存时同步写入）

提供：
- 结构化存储：长期记忆、时间线事件
- 迁移工具：从 MEMORY.md 同步到数据库
- 近期上下文检索：get_recent_context()
- 统一 API：面向 Agent Skill 的检索接口

用法：
    from memory_store import init, search

    # 初始化
    init()

    # 获取近期上下文
    context = search.get_recent_context(days=7)
"""

from . import db
from . import search
from . import repository
from . import migration

__all__ = [
    "init",
    "close",
    "search",
    "repository",
    "migration",
    "get_stats",
]


def init() -> None:
    """初始化 memory_store：建表 + 从 Markdown 迁移数据（如需要）。"""
    db.init_db()
    # 检查是否需要首次迁移
    stats = repository.get_stats()
    if stats["memories"] == 0 and stats["timeline_events"] == 0:
        print("[memory_store] 首次初始化，开始从 Markdown 迁移数据...")
        migration.migrate_all()


def close() -> None:
    """关闭数据库连接。"""
    db.close_db()


def get_stats() -> dict:
    """获取存储统计信息"""
    return repository.get_stats()
