"""
CFIRE Artist Memory Store
=========================

基于 SQLite 的虚拟艺人记忆长周期存储与倒排索引检索模块。

提供：
- 结构化存储：长期记忆、时间线事件、粉丝互动、审查复盘
- 中文分词：基于 jieba 的中文关键词提取
- 倒排索引：TF-IDF 加权的关键词检索
- 迁移工具：从 Markdown 档案文件导入数据
- 统一 API：面向 Agent Skill 的检索接口

用法：
    from memory_store import init, search

    # 初始化
    init()

    # 检索
    results = search.search_all("创作过程")
"""

from . import db
from . import search
from . import repository
from . import inverted_index
from . import tokenizer
from . import migration

__all__ = [
    "init",
    "close",
    "search",
    "repository",
    "inverted_index",
    "tokenizer",
    "migration",
    "get_stats",
    "index_record",
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


def index_record(table: str, record_id: int, content: str) -> None:
    """为一条记录手动建立倒排索引"""
    inverted_index.index_record(table, record_id, content)
