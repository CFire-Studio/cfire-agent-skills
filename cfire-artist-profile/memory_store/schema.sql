-- ============================================================
-- CFIRE Artist Memory Store Schema
-- 基于 SQLite 的艺人记忆派生索引（Markdown 为权威数据源）
-- ============================================================
-- 设计原则：
--   Markdown 文件（MEMORY.md、diary/*.md、content_draft/*.md）为权威数据源，
--   本数据库仅作为派生索引，用于近期上下文检索（get_recent_context）。
--   不承载倒排索引 / FTS，不复刻 Markdown 的全部内容。
-- ============================================================

-- 长期记忆（派生自 MEMORY.md，由 migration 模块同步）
CREATE TABLE IF NOT EXISTS memories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category        TEXT    NOT NULL DEFAULT 'general',   -- 分类：basic_facts, content_experience, activity_experience, etc.
    content         TEXT    NOT NULL,                     -- 记忆内容
    importance      INTEGER NOT NULL DEFAULT 1,           -- 重要性 1-10
    status          TEXT    NOT NULL DEFAULT 'confirmed', -- confirmed / pending / deprecated
    tags            TEXT    DEFAULT '[]',                 -- JSON array of tags
    source_event_id INTEGER,                              -- 关联的 timeline_event id
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (source_event_id) REFERENCES timeline_events(id) ON DELETE SET NULL
);

-- 时间线事件（派生自 diary/*.md 与 content_draft/*.md，由 daily 技能保存时同步写入）
CREATE TABLE IF NOT EXISTS timeline_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date          TEXT    NOT NULL,                    -- YYYY-MM-DD
    event_type          TEXT    NOT NULL,                    -- 日常/创作/活动/直播/复盘/粉丝互动/作品/争议/初始化
    content             TEXT    NOT NULL,                    -- 事件描述
    mood                TEXT    DEFAULT '',                  -- 情绪标签
    extendable_content  TEXT    DEFAULT '',                  -- 可延展内容方向
    promoted_to_memory  INTEGER DEFAULT 0,                   -- 0/1 是否已提炼为长期记忆
    memory_id           INTEGER,                             -- 关联 memories.id
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE SET NULL
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
CREATE INDEX IF NOT EXISTS idx_timeline_date ON timeline_events(event_date);
CREATE INDEX IF NOT EXISTS idx_timeline_type ON timeline_events(event_type);
