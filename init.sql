CREATE DATABASE IF NOT EXISTS rss_feed;
USE rss_feed;

DROP TABLE IF EXISTS entries;  -- Drop table to remove old constraints

CREATE TABLE IF NOT EXISTS entries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    feed_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    link VARCHAR(255) NOT NULL UNIQUE,
    published DATETIME,
    author VARCHAR(255),
    entry_id VARCHAR(255),
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_feed_id (feed_id),
    INDEX idx_published (published)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS daily_summaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    summary_date DATE NOT NULL,
    summary_text TEXT NOT NULL,
    article_count INT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    publications JSON,
    articles JSON,
    UNIQUE KEY unique_date (summary_date)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; 