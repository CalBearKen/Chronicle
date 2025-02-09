Chroniclr - News Aggregation & Analysis System

=== System Overview ===
A Dockerized application that:
1. Scrapes Substack RSS feeds
2. Stores articles in MySQL
3. Generates AI-powered summaries
4. Produces daily chronicles
5. Provides web interface

=== Prerequisites ===
1. Docker Desktop
2. Python 3.9+
3. Node.js (for PDF conversion)
4. OpenAI API key

=== Setup ===
1. Clone repository
   git clone [your-repo-url]
   cd chroniclr

2. Configure environment
   - Copy .env.template to .env:
     ```
     cp .env.template .env
     ```
   - Update .env with your settings:
     ```
     # Database Configuration
     DB_USER=rss_user
     DB_PASSWORD=rss_password
     DB_HOST=db
     DB_NAME=rss_feed
     
     # Feed Processing
     FEED_FETCH_TIMEOUT=30
     MAX_SUMMARY_LENGTH=65535
     CHUNK_SIZE=1000
     
     # Logging
     LOG_LEVEL=INFO
     
     # OpenAI (if you're using it)
     OPENAI_API_KEY=your_key_here
     ```
   - Update database credentials in docker-compose.yml if needed

3. Start database
   docker-compose up -d

4. Install Python dependencies
   pip install -r requirements.txt

=== Initialization ===
1. Scrape Substack feeds
   python substack_scraper.py

2. Import feeds to database
   python batch_rss_scraper.py

3. Start web interface
   python app.py

=== Regular Usage ===
1. Daily scraping (run via Task Scheduler/cron)
   python batch_rss_scraper.py

2. Generate summaries
   python news_summarizer.py

3. Create chronicle
   python chroniclr.py

4. Access web UI
   http://localhost:5000

=== Optional Features ===
1. Auto-start on boot (Windows):
   - Place shortcut to rss_scraper_startup.bat in Startup folder
   - Update paths in .bat and .ps1 files

2. Convert chronicle to PDF:
   pandoc humanity_fuck_yeah.md -o chronicle.pdf

=== Key Files ===
- docker-compose.yml        # Database config
- init.sql                  # Database schema
- feeds.csv                 # RSS feed list
- app.py                    # Web interface
- batch_rss_scraper.py      # RSS feed processor

=== Customizing RSS Feeds ===
1. Edit feeds.csv to manage RSS feed sources:
   - One feed URL per line
   - Format: feed_url
   - Example:
     ```
     feed_url
     https://example.com/feed
     https://another-site.com/rss
     ```

2. Apply changes:
   - Stop containers: docker-compose down
   - Rebuild: docker-compose build --no-cache
   - Start: docker-compose up

Note: Changes to feeds.csv require container rebuild
to take effect. The scraper imports feeds on first run.

=== Troubleshooting ===
1. Docker issues:
   - Ensure Docker Desktop is running
   - Check container logs: docker logs rss_mysql
   - Access MySQL shell:
     ```
     docker exec -it rss_mysql mysql -u rss_user -prss_password rss_feed
     ```

2. Database connection errors:
   - Verify credentials in db_config
   - Test connection using shell command above
   - Common MySQL commands:
     ```
     SHOW TABLES;                    # List all tables
     SELECT * FROM feeds LIMIT 5;    # View sample feeds
     SELECT * FROM entries LIMIT 5;  # View sample entries
     ```

3. Missing dependencies:
   - pip install -r requirements.txt --force-reinstall

4. API key errors:
   - Confirm OPENAI_API_KEY in .env
   - Check key validity at platform.openai.com

=== Maintenance ===
1. Backup database:
   docker exec rss_mysql mysqldump -u rss_user -prss_password rss_feed > backup.sql

2. Update feeds list:
   - Run substack_scraper.py periodically
   - Re-run batch_rss_scraper.py

3. Clear old data:
   TRUNCATE TABLE entries; TRUNCATE TABLE daily_summaries; 

=== Docker Deployment ===
1. Build containers:
   docker-compose build

2. Start system:
   docker-compose up -d

3. Stop system:
   docker-compose down

4. Update containers:
   docker-compose build --no-cache
   docker-compose down && docker-compose up -d

5. View logs:
   docker-compose logs -f app

Note: MySQL data persists in the 'mysql_data' volume between restarts.
To completely reset the database (WARNING: destroys all data):
   docker-compose down -v

4. Update containers:
   docker-compose build --no-cache
   docker-compose down && docker-compose up -d 