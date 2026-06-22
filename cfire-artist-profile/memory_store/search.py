"""
统一检索 API。

提供面向 Agent Skill 的高级检索接口，整合倒排索引关键词检索和结构化字段过滤。
"""

from typing import List, Optional, Dict

from . import inverted_index
from . import repository


def search_memories(
    query: str,
    category: Optional[str] = None,
    min_importance: int = 0,
    limit: int = 20,
) -> List[Dict]:
    """搜索长期记忆。

    先通过倒排索引检索，再用 category/importance 过滤。
    """
    results = inverted_index.search_aggregated(
        query,
        source_tables=["memories"],
        limit=limit * 2,
    )

    filtered = []
    for r in results:
        memory = repository.get_memory(r["source_id"])
        if memory is None or memory.get("status") == "deprecated":
            continue
        if category and memory.get("category") != category:
            continue
        if min_importance > 0 and memory.get("importance", 0) < min_importance:
            continue
        filtered.append({**r, "record": memory})

    return filtered[:limit]


def search_timeline(
    query: str,
    event_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
) -> List[Dict]:
    """搜索时间线事件。"""
    results = inverted_index.search_aggregated(
        query,
        source_tables=["timeline_events"],
        limit=limit * 2,
    )

    filtered = []
    for r in results:
        event = repository.get_timeline_event(r["source_id"])
        if event is None:
            continue
        if event_type and event.get("event_type") != event_type:
            continue
        if date_from and event.get("event_date", "") < date_from:
            continue
        if date_to and event.get("event_date", "") > date_to:
            continue
        filtered.append({**r, "record": event})

    return filtered[:limit]


def search_all(
    query: str,
    limit: int = 20,
    include_memories: bool = True,
    include_timeline: bool = True,
    include_fan: bool = False,
    include_reviews: bool = False,
) -> Dict[str, List[Dict]]:
    """跨表联合检索。"""
    tables = []
    if include_memories:
        tables.append("memories")
    if include_timeline:
        tables.append("timeline_events")
    if include_fan:
        tables.append("fan_interactions")
    if include_reviews:
        tables.append("reviews")

    results = inverted_index.search_aggregated(
        query,
        source_tables=tables,
        limit=limit * 3,
    )

    # 按源表分组
    grouped: Dict[str, List[Dict]] = {t: [] for t in tables}
    for r in results:
        grouped.setdefault(r["source_table"], []).append(r)

    # 裁剪到 limit
    return {k: v[:limit] for k, v in grouped.items()}


def search_by_keywords(
    keywords: List[str],
    source_tables: Optional[List[str]] = None,
    match_all: bool = False,
    limit: int = 20,
) -> List[Dict]:
    """精确关键词检索。

    Args:
        keywords: 关键词列表
        source_tables: 限定搜索表
        match_all: True 时所有关键词都必须匹配（AND），False 时任一匹配即可（OR）
        limit: 返回上限
    """
    if not keywords:
        return []

    if source_tables is None:
        source_tables = ["memories", "timeline_events", "fan_interactions", "reviews"]

    from .db import get_cursor

    placeholders = ",".join("?" for _ in keywords)
    table_placeholders = ",".join("?" for _ in source_tables)

    with get_cursor() as cur:
        sql = f"""SELECT source_table, source_id, keyword, tfidf
                  FROM inverted_index
                  WHERE keyword IN ({placeholders})
                    AND source_table IN ({table_placeholders})
                  ORDER BY tfidf DESC"""

        cur.execute(sql, keywords + source_tables)
        rows = cur.fetchall()

    # 按 (source_table, source_id) 聚合
    from collections import defaultdict
    grouped = defaultdict(lambda: {"keywords": set(), "score": 0.0})
    for row in rows:
        key = (row["source_table"], row["source_id"])
        grouped[key]["keywords"].add(row["keyword"])
        grouped[key]["score"] += row["tfidf"]

    results = []
    for (table, sid), data in grouped.items():
        if match_all and len(data["keywords"]) < len(keywords):
            continue
        results.append({
            "source_table": table,
            "source_id": sid,
            "score": round(data["score"], 4),
            "matched_keywords": sorted(data["keywords"]),
            "match_count": len(data["keywords"]),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def get_recent_context(
    days: int = 7,
    limit: int = 20,
) -> Dict:
    """获取近期上下文：最近事件 + 相关记忆，用于生成内容时保持连续性。"""
    from datetime import datetime, timedelta

    # 最近 N 天的时间线事件
    recent_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    events = repository.list_timeline_events(
        event_date_from=recent_date,
        limit=limit,
    )

    # 最近粉丝互动
    interactions = repository.list_fan_interactions(days=days, limit=limit)

    # 高重要性长期记忆
    important_memories = repository.list_memories(min_importance=3, limit=limit)

    return {
        "recent_events": events,
        "recent_interactions": interactions,
        "important_memories": important_memories,
        "context_window_days": days,
    }


# ============================================================
# 日志
# ============================================================

def log_search(query: str, result_count: int, source_tables: Optional[List[str]] = None) -> None:
    """记录搜索日志"""
    import json
    from .db import get_cursor

    tables_json = json.dumps(source_tables or ["all"], ensure_ascii=False)
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO search_log (query_text, source_tables, result_count) VALUES (?, ?, ?)",
            (query, tables_json, result_count),
        )
