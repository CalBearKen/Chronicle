#!/bin/bash
set -e  # Exit on error

echo "=== Starting Chroniclr ==="

# Wait for MySQL to be truly ready
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

# Run Substack scraper
echo "Starting Substack scraper..."
python substack_scraper.py
if [ $? -eq 0 ]; then
    echo "Substack scraper completed successfully!"
else
    echo "Warning: Substack scraper failed!"
    exit 1  # Exit if scraper fails
fi

# Run RSS scraper and wait for it to complete
echo "Starting RSS feed scraper..."
python batch_rss_scraper.py
if [ $? -eq 0 ]; then
    echo "RSS scraper completed successfully!"
else
    echo "Warning: RSS scraper failed!"
    exit 1  # Exit if scraper fails
fi

# Run news summarizer
echo "Generating summaries..."
python news_summarizer.py
if [ $? -eq 0 ]; then
    echo "Summaries generated successfully!"
else
    echo "Warning: Summary generation failed!"
    exit 1  # Exit if summarizer fails
fi

echo "=== Initialization Complete ==="

# Only start Flask after all initialization is done
echo "Starting web server..."
exec python app.py 