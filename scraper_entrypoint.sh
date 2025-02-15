#!/bin/bash
set -e

echo "=== Starting Chroniclr Scraper ==="

# Wait for MySQL to be ready
echo "Waiting for MySQL..."
max_tries=30
count=0
while ! mysqladmin ping -h"db" -u"rss_user" -p"rss_password" --silent; do
    echo "MySQL not ready - waiting..."
    sleep 2
    count=$((count + 1))
    if [ $count -ge $max_tries ]; then
        echo "Error: MySQL did not become ready in time"
        exit 1
    fi
done
echo "MySQL is ready!"

# Initialize database schema
echo "Initializing database schema..."
mysql -h db -u rss_user -prss_password rss_feed < /app/init.sql
echo "Schema initialized!"

# Run RSS scraper
echo "Starting RSS feed scraper..."
python batch_rss_scraper.py
if [ $? -ne 0 ]; then
    echo "RSS scraper failed!"
    exit 1
fi
echo "RSS scraper completed successfully!"

# Index articles
echo "Indexing articles..."
python indexer.py
if [ $? -ne 0 ]; then
    echo "Article indexing failed!"
    exit 1
fi
echo "Article indexing completed successfully!"

echo "=== Scraping Complete ==="
exit 0 