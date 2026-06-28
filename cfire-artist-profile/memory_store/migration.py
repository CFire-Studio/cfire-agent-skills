"""
数据迁移工具。

将 reference/MEMORY.md 中的长期记忆同步到 SQLite 数据库。
迁移是增量的——已存在的记录不会重复导入。

数据源约定：MEMORY.md 为权威源，本模块将其内容同步到 memories 表作为派生索引。
注：时间线事件（timeline_events）由 cfire-artist-daily 技能保存日记/内容策划时
直接写入，不走本迁移流程；TIMELINE.md 已废弃。
"""

import os
import sys
import json

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


def migrate_all(force: bool = False) -> dict:
    """执行全量迁移。

    Args:
        force: 是否清空数据库后重新迁移
    """
    db.init_db()

    if force:
        from .db import get_cursor
        with get_cursor() as cur:
            cur.execute("DELETE FROM memories")
            cur.execute("DELETE FROM timeline_events")
        print("[migration] Database cleared")

    results = {
        "memories": migrate_memory_md(),
    }

    stats = repository.get_stats()
    results["stats"] = stats

    return results


if __name__ == "__main__":
    result = migrate_all(force="--force" in sys.argv)
    print(json.dumps(result, indent=2, ensure_ascii=False))
