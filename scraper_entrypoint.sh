#!/bin/bash
set -e

echo "=== Starting Chroniclr Scraper ==="

# Wait for MySQL to be ready
echo "Waiting for MySQL..."
until mysqladmin ping -h"db" -u"rss_user" -p"rss_password" --silent; do
    echo "MySQL not ready - waiting..."
    sleep 2
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

echo "=== Scraping Complete ==="
exit 0 