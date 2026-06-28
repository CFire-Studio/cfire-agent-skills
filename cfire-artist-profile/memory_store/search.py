"""
统一检索 API。

提供面向 Agent Skill 的高级检索接口。
当前仅保留近期上下文检索（get_recent_context），用于生成内容时保持连续性。

设计说明：
- Markdown 为权威数据源，本模块仅基于派生索引（timeline_events / memories）做轻量检索。
- 已移除倒排索引 / FTS / 多关键词精确检索等过度工程能力；如未来确有全文检索需求，
  可基于 SQLite FTS5 重新引入，避免 reintroduce 手写分词。
"""

from typing import Dict

from . import repository


def get_recent_context(
    days: int = 7,
    limit: int = 20,
) -> Dict:
    """获取近期上下文：最近事件 + 高重要性长期记忆，用于生成内容时保持连续性。

    Args:
        days: 回溯天数
        limit: 每类条目上限

    Returns:
        dict: recent_events（近期时间线事件）+ important_memories（高重要性长期记忆）
    """
    from datetime import datetime, timedelta

    # 最近 N 天的时间线事件
    recent_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    events = repository.list_timeline_events(
        event_date_from=recent_date,
        limit=limit,
    )

    # 高重要性长期记忆
    important_memories = repository.list_memories(min_importance=3, limit=limit)

    return {
        "recent_events": events,
        "important_memories": important_memories,
        "context_window_days": days,
    }
