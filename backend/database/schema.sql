-- entertainment-column-system database schema

-- Articles table: stores collected articles from note (no full content, only preview)
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,                -- note article ID
    title TEXT NOT NULL,                -- article title
    url TEXT NOT NULL UNIQUE,           -- article URL
    thumbnail TEXT,                     -- thumbnail image URL
    published_at DATETIME NOT NULL,     -- publication date
    author TEXT NOT NULL,               -- author name
    content_preview TEXT,               -- article preview text (short)
    category TEXT NOT NULL,             -- category (entertainment)
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- collection timestamp
    is_evaluated BOOLEAN DEFAULT FALSE, -- evaluation flag
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for articles table
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at);
CREATE INDEX IF NOT EXISTS idx_articles_is_evaluated ON articles(is_evaluated);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);

-- Evaluations table: stores AI evaluation results
CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT NOT NULL,           -- foreign key to articles.id
    quality_score INTEGER NOT NULL,    -- writing quality score (0-40)
    originality_score INTEGER NOT NULL, -- originality score (0-30)
    entertainment_score INTEGER NOT NULL, -- entertainment score (0-30)
    total_score INTEGER NOT NULL,      -- total score (0-100)
    ai_summary TEXT NOT NULL,           -- AI-generated summary
    evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);

-- Indexes for evaluations table
CREATE INDEX IF NOT EXISTS idx_evaluations_total_score ON evaluations(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_evaluations_evaluated_at ON evaluations(evaluated_at);
CREATE INDEX IF NOT EXISTS idx_evaluations_article_id ON evaluations(article_id);

-- Twitter posts table: stores X/Twitter post history
CREATE TABLE IF NOT EXISTS twitter_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id TEXT,                      -- X/Twitter post ID
    content TEXT NOT NULL,              -- post content
    posted_at DATETIME,                 -- post timestamp
    status TEXT DEFAULT 'pending',     -- status: pending/posted/failed
    error_message TEXT,                 -- error message if failed
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for twitter_posts table
CREATE INDEX IF NOT EXISTS idx_twitter_posts_status ON twitter_posts(status);
CREATE INDEX IF NOT EXISTS idx_twitter_posts_posted_at ON twitter_posts(posted_at);

-- System log table: stores system operation logs
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,                -- log level: INFO, WARNING, ERROR
    message TEXT NOT NULL,              -- log message
    component TEXT,                     -- system component
    details TEXT,                       -- additional details (JSON)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index for system_logs table
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);