-- ============================================================
-- CFIRE Artist Memory Store Schema
-- 基于 SQLite 的艺人记忆长周期存储与倒排索引检索
-- ============================================================

-- 长期记忆（对应 MEMORY.md）
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

-- 时间线事件（对应 TIMELINE.md）
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

-- 粉丝互动记录（对应 FAN_CONTEXT.cache.md）
CREATE TABLE IF NOT EXISTS fan_interactions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    platform            TEXT    NOT NULL,
    fan_identifier      TEXT    NOT NULL,                    -- 脱敏标识
    content_summary     TEXT    NOT NULL,
    suggested_response  TEXT    DEFAULT '',
    interaction_value   TEXT    DEFAULT 'medium',            -- high / medium / low
    relation_boundary   TEXT    DEFAULT 'safe',              -- safe / cautious
    sync_status         TEXT    DEFAULT 'local',             -- local / synced
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 发布审查与复盘（对应 REVIEW.md）
CREATE TABLE IF NOT EXISTS reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    review_type     TEXT    NOT NULL,                         -- pre_publish / post_mortem
    content_summary TEXT    NOT NULL,
    result          TEXT    DEFAULT '',
    lessons         TEXT    DEFAULT '',
    action_items    TEXT    DEFAULT '[]',
    reviewed_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ============================================================
-- 倒排索引表
-- ============================================================

-- FTS5 全文搜索虚拟表 (英文/通用)
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    content,
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

-- 倒排索引主表 (支持中文分词)
CREATE TABLE IF NOT EXISTS inverted_index (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword         TEXT    NOT NULL,                        -- 分词后的关键词
    source_table    TEXT    NOT NULL,                        -- memories / timeline_events / fan_interactions / reviews
    source_id       INTEGER NOT NULL,                        -- 对应表中的记录 id
    tf              REAL    NOT NULL DEFAULT 0,              -- 词频 (Term Frequency)
    idf             REAL    NOT NULL DEFAULT 0,              -- 逆文档频率 (Inverse Document Frequency)
    tfidf           REAL    NOT NULL DEFAULT 0,              -- TF-IDF 权重
    positions       TEXT    DEFAULT '[]',                    -- JSON: 关键词在原文中的位置列表
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 关键词-文档映射的高速缓存
CREATE TABLE IF NOT EXISTS keyword_doc_count (
    keyword     TEXT PRIMARY KEY,
    doc_count   INTEGER NOT NULL DEFAULT 1
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_inverted_keyword ON inverted_index(keyword);
CREATE INDEX IF NOT EXISTS idx_inverted_source ON inverted_index(source_table, source_id);
CREATE INDEX IF NOT EXISTS idx_inverted_tfidf ON inverted_index(tfidf DESC);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
CREATE INDEX IF NOT EXISTS idx_timeline_date ON timeline_events(event_date);
CREATE INDEX IF NOT EXISTS idx_timeline_type ON timeline_events(event_type);
CREATE INDEX IF NOT EXISTS idx_fan_platform ON fan_interactions(platform);
CREATE INDEX IF NOT EXISTS idx_fan_date ON fan_interactions(created_at);
CREATE INDEX IF NOT EXISTS idx_reviews_type ON reviews(review_type);

-- 搜索日志 (可选)
CREATE TABLE IF NOT EXISTS search_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text      TEXT    NOT NULL,
    source_tables   TEXT    DEFAULT '["memories","timeline_events"]',
    result_count    INTEGER NOT NULL DEFAULT 0,
    searched_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
