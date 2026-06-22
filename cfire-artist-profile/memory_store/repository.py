"""
数据仓库层 (Repository)。

提供对 memories、timeline_events、fan_interactions、reviews 表的 CRUD 操作。
所有写入操作自动触发倒排索引更新。
"""

import json
from typing import List, Optional, Dict

from .db import get_cursor
from . import inverted_index


# ============================================================
# Memories (长期记忆)
# ============================================================

def save_memory(
    category: str,
    content: str,
    importance: int = 1,
    status: str = "confirmed",
    tags: Optional[List[str]] = None,
    source_event_id: Optional[int] = None,
) -> int:
    """保存一条长期记忆，返回新记录的 id"""
    tags_json = json.dumps(tags or [], ensure_ascii=False)
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO memories (category, content, importance, status, tags, source_event_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (category, content, importance, status, tags_json, source_event_id),
        )
        new_id = cur.lastrowid

    inverted_index.index_record("memories", new_id, content)
    return new_id


def update_memory(memory_id: int, **fields) -> bool:
    """更新长期记忆字段"""
    allowed = {"category", "content", "importance", "status", "tags", "source_event_id"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False

    if "tags" in updates and isinstance(updates["tags"], list):
        updates["tags"] = json.dumps(updates["tags"], ensure_ascii=False)

    updates["updated_at"] = "datetime('now', 'localtime')"
    set_clause = ", ".join(f"{k}=?" for k in updates)

    with get_cursor() as cur:
        cur.execute(
            f"UPDATE memories SET {set_clause} WHERE id=?",
            list(updates.values()) + [memory_id],
        )

    # 如果内容变了，重建索引
    if "content" in fields:
        inverted_index.remove_record_index("memories", memory_id)
        inverted_index.index_record("memories", memory_id, fields["content"])

    return True


def get_memory(memory_id: int) -> Optional[Dict]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM memories WHERE id=?", (memory_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return dict(row)


def list_memories(
    category: Optional[str] = None,
    status: Optional[str] = None,
    min_importance: int = 0,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict]:
    conditions = []
    params = []
    if category:
        conditions.append("category=?")
        params.append(category)
    if status:
        conditions.append("status=?")
        params.append(status)
    conditions.append("importance >= ?")
    params.append(min_importance)

    where = " AND ".join(conditions)
    with get_cursor() as cur:
        cur.execute(
            f"SELECT * FROM memories WHERE {where} ORDER BY importance DESC, updated_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
        return [dict(r) for r in cur.fetchall()]


def delete_memory(memory_id: int) -> bool:
    inverted_index.remove_record_index("memories", memory_id)
    with get_cursor() as cur:
        cur.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        return cur.rowcount > 0


# ============================================================
# Timeline Events (时间线)
# ============================================================

def save_timeline_event(
    event_date: str,
    event_type: str,
    content: str,
    mood: str = "",
    extendable_content: str = "",
) -> int:
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO timeline_events
               (event_date, event_type, content, mood, extendable_content)
               VALUES (?, ?, ?, ?, ?)""",
            (event_date, event_type, content, mood, extendable_content),
        )
        new_id = cur.lastrowid

    inverted_index.index_record("timeline_events", new_id, content)
    return new_id


def update_timeline_event(event_id: int, **fields) -> bool:
    allowed = {"event_date", "event_type", "content", "mood", "extendable_content", "promoted_to_memory", "memory_id"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False

    set_clause = ", ".join(f"{k}=?" for k in updates)

    with get_cursor() as cur:
        cur.execute(
            f"UPDATE timeline_events SET {set_clause} WHERE id=?",
            list(updates.values()) + [event_id],
        )

    if "content" in fields:
        inverted_index.remove_record_index("timeline_events", event_id)
        inverted_index.index_record("timeline_events", event_id, fields["content"])

    return True


def get_timeline_event(event_id: int) -> Optional[Dict]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM timeline_events WHERE id=?", (event_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_timeline_events(
    event_date_from: Optional[str] = None,
    event_date_to: Optional[str] = None,
    event_type: Optional[str] = None,
    promoted_to_memory: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict]:
    conditions = []
    params = []
    if event_date_from:
        conditions.append("event_date >= ?")
        params.append(event_date_from)
    if event_date_to:
        conditions.append("event_date <= ?")
        params.append(event_date_to)
    if event_type:
        conditions.append("event_type = ?")
        params.append(event_type)
    if promoted_to_memory is not None:
        conditions.append("promoted_to_memory = ?")
        params.append(promoted_to_memory)

    where = " AND ".join(conditions) if conditions else "1=1"
    with get_cursor() as cur:
        cur.execute(
            f"SELECT * FROM timeline_events WHERE {where} ORDER BY event_date DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
        return [dict(r) for r in cur.fetchall()]


def delete_timeline_event(event_id: int) -> bool:
    inverted_index.remove_record_index("timeline_events", event_id)
    with get_cursor() as cur:
        cur.execute("DELETE FROM timeline_events WHERE id=?", (event_id,))
        return cur.rowcount > 0


def promote_event_to_memory(event_id: int) -> Optional[int]:
    """将时间线事件提炼为长期记忆"""
    event = get_timeline_event(event_id)
    if not event:
        return None

    memory_id = save_memory(
        category="from_timeline",
        content=event["content"],
        importance=3,
        source_event_id=event_id,
    )

    update_timeline_event(event_id, promoted_to_memory=1, memory_id=memory_id)
    return memory_id


# ============================================================
# Fan Interactions (粉丝互动)
# ============================================================

def save_fan_interaction(
    platform: str,
    fan_identifier: str,
    content_summary: str,
    suggested_response: str = "",
    interaction_value: str = "medium",
    relation_boundary: str = "safe",
) -> int:
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO fan_interactions
               (platform, fan_identifier, content_summary, suggested_response, interaction_value, relation_boundary)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (platform, fan_identifier, content_summary, suggested_response, interaction_value, relation_boundary),
        )
        new_id = cur.lastrowid

    inverted_index.index_record("fan_interactions", new_id, content_summary)
    return new_id


def list_fan_interactions(platform: Optional[str] = None, days: int = 7, limit: int = 50) -> List[Dict]:
    conditions = ["created_at >= datetime('now', 'localtime', ?)"]
    params = [f"-{days} days", limit]
    if platform:
        conditions.append("platform = ?")
        params.insert(1, platform)

    where = " AND ".join(conditions)
    with get_cursor() as cur:
        cur.execute(f"SELECT * FROM fan_interactions WHERE {where} ORDER BY created_at DESC LIMIT ?", params)
        return [dict(r) for r in cur.fetchall()]


# ============================================================
# Reviews (审查与复盘)
# ============================================================

def save_review(
    review_type: str,
    content_summary: str,
    result: str = "",
    lessons: str = "",
    action_items: Optional[List[str]] = None,
) -> int:
    action_json = json.dumps(action_items or [], ensure_ascii=False)
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO reviews (review_type, content_summary, result, lessons, action_items)
               VALUES (?, ?, ?, ?, ?)""",
            (review_type, content_summary, result, lessons, action_json),
        )
        new_id = cur.lastrowid

    search_text = f"{content_summary} {result} {lessons}"
    inverted_index.index_record("reviews", new_id, search_text)
    return new_id


def list_reviews(review_type: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict]:
    if review_type:
        with get_cursor() as cur:
            cur.execute(
                "SELECT * FROM reviews WHERE review_type=? ORDER BY reviewed_at DESC LIMIT ? OFFSET ?",
                (review_type, limit, offset),
            )
            return [dict(r) for r in cur.fetchall()]
    else:
        with get_cursor() as cur:
            cur.execute("SELECT * FROM reviews ORDER BY reviewed_at DESC LIMIT ? OFFSET ?", (limit, offset))
            return [dict(r) for r in cur.fetchall()]


# ============================================================
# 统计信息
# ============================================================

def get_stats() -> Dict:
    """获取数据库统计信息"""
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM memories WHERE status != 'deprecated'")
        memory_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM timeline_events")
        timeline_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM fan_interactions")
        fan_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM reviews")
        review_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT keyword) FROM inverted_index")
        keyword_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM inverted_index")
        index_count = cur.fetchone()[0]

    return {
        "memories": memory_count,
        "timeline_events": timeline_count,
        "fan_interactions": fan_count,
        "reviews": review_count,
        "unique_keywords": keyword_count,
        "total_index_entries": index_count,
    }
