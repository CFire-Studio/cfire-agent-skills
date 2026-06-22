"""
数据迁移工具。

将 reference/ 目录中的 Markdown 表格数据迁移到 SQLite 数据库。
迁移是增量的——已存在的记录不会重复导入。
"""

import os
import sys
import json
from typing import Optional

# 添加父路径以导入 memory_store
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory_store import db, repository


def migrate_memory_md() -> int:
    """从 MEMORY.md 迁移长期记忆。"""
    memory_md_path = os.path.join(
        os.path.dirname(__file__), "..", "reference", "MEMORY.md"
    )
    if not os.path.exists(memory_md_path):
        print(f"[migration] MEMORY.md not found at {memory_md_path}")
        return 0

    with open(memory_md_path, "r", encoding="utf-8") as f:
        content = f.read()

    count = 0
    current_category = "general"

    for line in content.split("\n"):
        line = line.strip()

        # 检测分类标题
        if line.startswith("## "):
            title = line[3:].strip()
            category_map = {
                "艺人长期事实": "basic_facts",
                "内容经验": "content_experience",
                "活动经验": "activity_experience",
                "记忆写入标准": "writing_criteria",
                "禁止写入": "forbidden",
            }
            for key, val in category_map.items():
                if key in title:
                    current_category = val
                    break

        # 解析列表项 "- xxx"
        elif line.startswith("- "):
            item = line[2:].strip()
            if any(
                skip in item
                for skip in [
                    "API Key",
                    "账号密码",
                    "待记录",
                    "待同步",
                ]
            ):
                continue

            # 跳过标题/说明性文本
            if item.startswith("##") or item.startswith("|"):
                continue

            repository.save_memory(
                category=current_category,
                content=item,
                importance=3 if current_category == "basic_facts" else 1,
                status="confirmed",
            )
            count += 1

    print(f"[migration] Migrated {count} items from MEMORY.md")
    return count


def migrate_timeline_md() -> int:
    """从 TIMELINE.md 迁移时间线事件。"""
    timeline_md_path = os.path.join(
        os.path.dirname(__file__), "..", "reference", "TIMELINE.md"
    )
    if not os.path.exists(timeline_md_path):
        print(f"[migration] TIMELINE.md not found at {timeline_md_path}")
        return 0

    with open(timeline_md_path, "r", encoding="utf-8") as f:
        content = f.read()

    count = 0
    in_table = False

    for line in content.split("\n"):
        line = line.strip()

        # 检测表格
        if line.startswith("| 日期 ") and "事件" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line and not line.startswith("|"):
            in_table = False
            continue

        if in_table and line.startswith("|") and not line.startswith("| 日期") and not line.startswith("|---"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) < 3:
                continue

            event_date = parts[0]
            event_type = parts[1] if len(parts) > 1 else "未知"
            event_content = parts[2] if len(parts) > 2 else ""
            mood = parts[3] if len(parts) > 3 else ""
            extendable = parts[4] if len(parts) > 4 else ""

            repository.save_timeline_event(
                event_date=event_date,
                event_type=event_type,
                content=event_content,
                mood=mood,
                extendable_content=extendable,
            )
            count += 1

    print(f"[migration] Migrated {count} items from TIMELINE.md")
    return count


def migrate_all(force: bool = False) -> dict:
    """执行全量迁移。

    Args:
        force: 是否清空数据库后重新迁移
    """
    db.init_db()

    if force:
        from .db import get_cursor
        with get_cursor() as cur:
            cur.execute("DELETE FROM inverted_index")
            cur.execute("DELETE FROM keyword_doc_count")
            cur.execute("DELETE FROM memories")
            cur.execute("DELETE FROM timeline_events")
            cur.execute("DELETE FROM fan_interactions")
            cur.execute("DELETE FROM reviews")
        print("[migration] Database cleared")

    results = {
        "memories": migrate_memory_md(),
        "timeline": migrate_timeline_md(),
    }

    stats = repository.get_stats()
    results["stats"] = stats

    return results


if __name__ == "__main__":
    result = migrate_all(force="--force" in sys.argv)
    print(json.dumps(result, indent=2, ensure_ascii=False))
