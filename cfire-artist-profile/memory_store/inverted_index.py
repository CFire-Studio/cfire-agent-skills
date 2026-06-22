"""
倒排索引构建与检索。

维护 inverted_index 表和 keyword_doc_count 表，
提供基于 TF-IDF 加权的中文关键词检索。

核心流程：
1. 新增/更新记录 → 分词 → 计算 TF → 更新倒排表 → 重算 IDF
2. 查询 → 分词 → 从倒排表按 TF-IDF 排序返回结果
"""

import json
from typing import List, Dict, Optional, Tuple

from . import tokenizer
from .db import get_cursor


def _get_total_docs_in_table(table: str) -> int:
    """获取某表中已索引的文档总数"""
    with get_cursor() as cur:
        if table == "memories":
            cur.execute("SELECT COUNT(*) FROM memories WHERE status != 'deprecated'")
        elif table == "timeline_events":
            cur.execute("SELECT COUNT(*) FROM timeline_events")
        elif table == "fan_interactions":
            cur.execute("SELECT COUNT(*) FROM fan_interactions")
        elif table == "reviews":
            cur.execute("SELECT COUNT(*) FROM reviews")
        else:
            return 0
        row = cur.fetchone()
        return row[0] if row else 0


def _get_total_docs_all() -> int:
    """获取所有表的文档总数"""
    return (
        _get_total_docs_in_table("memories")
        + _get_total_docs_in_table("timeline_events")
        + _get_total_docs_in_table("fan_interactions")
        + _get_total_docs_in_table("reviews")
    )


def index_record(table: str, record_id: int, content: str) -> None:
    """为一条记录建立倒排索引。

    Args:
        table: 表名 (memories/timeline_events/fan_interactions/reviews)
        record_id: 记录主键
        content: 要索引的文本内容
    """
    keywords_with_pos = tokenizer.extract_keywords_with_positions(content)

    if not keywords_with_pos:
        return

    total_docs = _get_total_docs_all()

    with get_cursor() as cur:
        # 删除该记录的旧索引
        cur.execute(
            "DELETE FROM inverted_index WHERE source_table=? AND source_id=?",
            (table, record_id),
        )

        for keyword, tf, positions in keywords_with_pos:
            # 更新或插入 doc_count
            cur.execute(
                "INSERT INTO keyword_doc_count(keyword, doc_count) VALUES (?, 1) "
                "ON CONFLICT(keyword) DO UPDATE SET doc_count = doc_count + 1",
                (keyword,),
            )
            cur.execute("SELECT doc_count FROM keyword_doc_count WHERE keyword=?", (keyword,))
            doc_count = cur.fetchone()[0]

            idf = tokenizer.compute_idf(keyword, total_docs, doc_count)
            tfidf = tf * idf

            cur.execute(
                """INSERT INTO inverted_index
                   (keyword, source_table, source_id, tf, idf, tfidf, positions)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (keyword, table, record_id, tf, idf, tfidf, json.dumps(positions)),
            )


def remove_record_index(table: str, record_id: int) -> None:
    """删除一条记录的所有索引项"""
    with get_cursor() as cur:
        # 减少 doc_count
        cur.execute(
            "SELECT keyword FROM inverted_index WHERE source_table=? AND source_id=?",
            (table, record_id),
        )
        keywords = [r[0] for r in cur.fetchall()]
        for keyword in keywords:
            cur.execute(
                "UPDATE keyword_doc_count SET doc_count = MAX(0, doc_count - 1) WHERE keyword=?",
                (keyword,),
            )

        cur.execute(
            "DELETE FROM inverted_index WHERE source_table=? AND source_id=?",
            (table, record_id),
        )


def rebuild_all_idf() -> None:
    """重建所有索引项的 IDF 值。在大量增删后调用以保持权重准确。"""
    total_docs = _get_total_docs_all()

    with get_cursor() as cur:
        cur.execute("SELECT DISTINCT keyword FROM inverted_index")
        keywords = [r[0] for r in cur.fetchall()]

        for keyword in keywords:
            cur.execute("SELECT doc_count FROM keyword_doc_count WHERE keyword=?", (keyword,))
            row = cur.fetchone()
            if row is None:
                continue
            doc_count = row[0]
            new_idf = tokenizer.compute_idf(keyword, total_docs, doc_count)

            cur.execute(
                "UPDATE inverted_index SET idf=?, tfidf=tf*? WHERE keyword=?",
                (new_idf, new_idf, keyword),
            )


def search(
    query: str,
    source_tables: Optional[List[str]] = None,
    limit: int = 20,
    min_tfidf: float = 0.0,
) -> List[Dict]:
    """基于倒排索引的关键词检索。

    Args:
        query: 查询文本
        source_tables: 限定搜索的表，默认所有表
        limit: 返回结果数上限
        min_tfidf: 最低 TF-IDF 阈值

    Returns:
        按 TF-IDF 降序排列的结果列表，每条包含:
        - source_table, source_id, keyword, tf, idf, tfidf, positions, content
    """
    if not query or not query.strip():
        return []

    keywords = tokenizer.tokenize(query)
    if not keywords:
        return []

    if source_tables is None:
        source_tables = ["memories", "timeline_events", "fan_interactions", "reviews"]

    placeholders = ",".join("?" for _ in keywords)
    table_placeholders = ",".join("?" for _ in source_tables)

    content_map = {
        "memories": _fetch_memory_contents,
        "timeline_events": _fetch_timeline_contents,
        "fan_interactions": _fetch_fan_contents,
        "reviews": _fetch_review_contents,
    }

    # 批量加载所需内容
    table_contents: Dict[str, Dict[int, str]] = {}
    for t in source_tables:
        if t in content_map:
            table_contents[t] = content_map[t]()

    with get_cursor() as cur:
        sql = f"""SELECT keyword, source_table, source_id, tf, idf, tfidf, positions
                  FROM inverted_index
                  WHERE keyword IN ({placeholders})
                    AND source_table IN ({table_placeholders})
                    AND tfidf >= ?
                  ORDER BY tfidf DESC
                  LIMIT ?"""

        params = keywords + source_tables + [min_tfidf, limit]
        cur.execute(sql, params)
        rows = cur.fetchall()

    results = []
    for row in rows:
        content = table_contents.get(row["source_table"], {}).get(row["source_id"], "")
        results.append({
            "source_table": row["source_table"],
            "source_id": row["source_id"],
            "keyword": row["keyword"],
            "tf": round(row["tf"], 4),
            "idf": round(row["idf"], 4),
            "tfidf": round(row["tfidf"], 4),
            "positions": json.loads(row["positions"]) if row["positions"] else [],
            "content": content,
        })

    return results


def search_aggregated(
    query: str,
    source_tables: Optional[List[str]] = None,
    limit: int = 20,
    min_tfidf: float = 0.0,
) -> List[Dict]:
    """聚合检索：按 source_table + source_id 合并多个关键词匹配，计算综合得分。"""
    raw = search(query, source_tables, limit * 3, min_tfidf)

    # 按 (source_table, source_id) 聚合
    grouped: Dict[Tuple[str, int], List[Dict]] = {}
    for item in raw:
        key = (item["source_table"], item["source_id"])
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(item)

    aggregated = []
    for (table, sid), matches in grouped.items():
        score = sum(m["tfidf"] for m in matches)
        matched_keywords = list(set(m["keyword"] for m in matches))
        aggregated.append({
            "source_table": table,
            "source_id": sid,
            "score": round(score, 4),
            "matched_keywords": matched_keywords,
            "match_count": len(matched_keywords),
            "content": matches[0]["content"],
            "details": matches,
        })

    aggregated.sort(key=lambda x: x["score"], reverse=True)
    return aggregated[:limit]


def _fetch_memory_contents() -> Dict[int, str]:
    with get_cursor() as cur:
        cur.execute("SELECT id, content FROM memories WHERE status != 'deprecated'")
        return {r[0]: r[1] for r in cur.fetchall()}


def _fetch_timeline_contents() -> Dict[int, str]:
    with get_cursor() as cur:
        cur.execute("SELECT id, content FROM timeline_events")
        return {r[0]: r[1] for r in cur.fetchall()}


def _fetch_fan_contents() -> Dict[int, str]:
    with get_cursor() as cur:
        cur.execute("SELECT id, content_summary FROM fan_interactions")
        return {r[0]: r[1] for r in cur.fetchall()}


def _fetch_review_contents() -> Dict[int, str]:
    with get_cursor() as cur:
        cur.execute("SELECT id, content_summary FROM reviews")
        return {r[0]: r[1] for r in cur.fetchall()}
