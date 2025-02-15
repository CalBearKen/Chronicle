import pandas as pd
from sqlalchemy import create_engine, text
import feedparser
from datetime import datetime
import logging
import sys
import os
from os import getenv
from dotenv import load_dotenv
from urllib.parse import urlparse
from typing import Optional
import requests
from requests.exceptions import RequestException

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class FeedProcessor:
    def __init__(self):
        """Initialize database connection"""
        try:
            # Create SQLAlchemy connection string with proper format
            db_url = (
                f"mysql+mysqlconnector://"
                f"{getenv('DB_USER', 'rss_user')}:"
                f"{getenv('DB_PASSWORD', 'rss_password')}@"
                f"{getenv('DB_HOST', 'db')}:3306/"  # Add explicit port
                f"{getenv('DB_NAME', 'rss_feed')}"
            )
            
            logger.info(f"Connecting to database at {getenv('DB_HOST', 'db')}")
            
            # Add connection pooling and retry settings
            self.engine = create_engine(
                db_url,
                pool_pre_ping=True,  # Check connection before using
                pool_recycle=3600,   # Recycle connections after an hour
                connect_args={
                    'connect_timeout': 60  # Wait up to 60 seconds for connection
                }
            )
            
            # Test connection
            with self.engine.connect() as conn:
                logger.info("Database connection successful")
            
            self.chunk_size = int(getenv('CHUNK_SIZE', 1000))
            self.max_summary_length = int(getenv('MAX_SUMMARY_LENGTH', 65535))
            self.feed_timeout = int(getenv('FEED_FETCH_TIMEOUT', 30))
            
        except Exception as e:
            logger.error(f"Database connection error: {type(e).__name__}")
            logger.debug(f"Detailed error: {str(e)}")
            raise

    def validate_feed_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def safe_truncate(self, text: Optional[str], max_length: Optional[int] = None) -> str:
        """Safely truncate text to specified length"""
        if text is None:
            return ''
        max_len = max_length or self.max_summary_length
        return str(text)[:max_len]

    def import_feeds_from_csv(self) -> bool:
        """Import feeds from CSV file if they don't exist in database"""
        try:
            csv_path = os.path.join(os.path.dirname(__file__), 'feeds.csv')
            if not os.path.exists(csv_path):
                logger.error(f"CSV file not found: {csv_path}")
                return False

            # Read feeds from CSV
            df = pd.read_csv(csv_path)
            logger.info(f"Found {len(df)} feeds in CSV file")

            # Add headers for request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/rss+xml, application/xml, application/atom+xml, text/xml;q=0.9, */*;q=0.8'
            }

            # Get feed titles using feedparser
            feed_data = []
            for feed_url in df['feed_url']:
                if not self.validate_feed_url(feed_url):
                    logger.error(f"Invalid feed URL: {feed_url}")
                    continue

                try:
                    logger.info(f"Fetching title for {feed_url}")
                    
                    # Fetch feed content with timeout
                    response = requests.get(feed_url, headers=headers, timeout=self.feed_timeout)
                    response.raise_for_status()
                    feed = feedparser.parse(response.content)
                    
                    title = self.safe_truncate(feed.feed.get('title', feed_url), 255)
                    
                    link = feed.feed.get('link', None)
                    if not link or not self.validate_feed_url(link):
                        link = feed_url.replace('/feed', '')
                    
                    feed_data.append({
                        'title': title,
                        'feed_url': feed_url,
                        'link': self.safe_truncate(link, 255)
                    })
                    logger.info(f"Found title: {title}, link: {link}")
                except Exception as e:
                    logger.error(f"Feed processing error: {type(e).__name__}")
                    logger.debug(f"Detailed error: {str(e)}")
                    feed_data.append({
                        'title': self.safe_truncate(feed_url, 255),
                        'feed_url': feed_url,
                        'link': self.safe_truncate(feed_url.replace('/feed', ''), 255)
                    })

            if not feed_data:
                logger.error("No valid feeds found")
                return False

            # Create DataFrame with titles and links
            feeds_df = pd.DataFrame(feed_data)
            
            # Insert feeds into database in chunks
            feeds_df.to_sql(
                'feeds',
                self.engine,
                if_exists='append',
                index=False,
                method='multi',
                chunksize=self.chunk_size
            )
            logger.info("Imported feeds from CSV to database")
            return True

        except Exception as e:
            logger.error(f"Feed import error: {type(e).__name__}")
            logger.debug(f"Detailed error: {str(e)}")
            return False

    def get_feeds(self) -> pd.DataFrame:
        """Get feeds directly from CSV file"""
        try:
            csv_path = os.path.join(os.path.dirname(__file__), 'feeds.csv')
            if not os.path.exists(csv_path):
                logger.error(f"CSV file not found: {csv_path}")
                return pd.DataFrame()

            # Read feeds from CSV
            df = pd.read_csv(csv_path)
            logger.info(f"Retrieved {len(df)} feeds from CSV file")
            
            # Add an ID column for compatibility with existing code
            df['id'] = range(1, len(df) + 1)
            
            return df[['id', 'feed_url']]  # Return only needed columns
            
        except Exception as e:
            logger.error(f"Error reading feeds CSV: {type(e).__name__}")
            logger.debug(f"Detailed error: {str(e)}")
            return pd.DataFrame()

    def process_feed(self, feed_id: int, feed_url: str) -> pd.DataFrame:
        """Process a single feed and return entries as DataFrame"""
        if not self.validate_feed_url(feed_url):
            logger.error(f"Invalid feed URL: {feed_url}")
            return pd.DataFrame()

        try:
            logger.info(f"Processing feed {feed_id}: {feed_url}")
            
            # Add headers for request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/rss+xml, application/xml, application/atom+xml, text/xml;q=0.9, */*;q=0.8'
            }
            
            try:
                # Fetch feed content with timeout
                response = requests.get(feed_url, headers=headers, timeout=self.feed_timeout)
                response.raise_for_status()
                feed_content = response.content
            except RequestException as e:
                logger.error(f"Failed to fetch feed {feed_url}: {str(e)}")
                return pd.DataFrame()
            
            # Parse feed content
            feed = feedparser.parse(feed_content)
            
            # Debug feed parsing results
            logger.debug(f"Feed status: {feed.get('status', 'unknown')}")
            logger.debug(f"Feed version: {feed.get('version', 'unknown')}")
            logger.debug(f"Feed keys: {feed.keys()}")
            
            if hasattr(feed, 'bozo_exception'):
                logger.error(f"Feed parsing error for {feed_url}: {feed.bozo_exception}")
                return pd.DataFrame()
            
            if not hasattr(feed, 'entries') or not feed.entries:
                logger.warning(f"No entries found in feed: {feed_url}")
                return pd.DataFrame()
            
            logger.info(f"Found {len(feed.entries)} entries in feed {feed_url}")
            
            entries = []
            for i, entry in enumerate(feed.entries):
                try:
                    # Detailed debug logging for first entry
                    if i == 0:
                        logger.debug(f"Sample entry structure for {feed_url}: {entry}")
                        logger.debug(f"Entry keys: {entry.keys()}")
                    
                    # Extract data with fallbacks
                    title = getattr(entry, 'title', None) or ''
                    link = getattr(entry, 'link', None) or ''
                    summary = getattr(entry, 'summary', None) or getattr(entry, 'description', '') or ''
                    author = getattr(entry, 'author', None) or ''
                    entry_id = getattr(entry, 'id', None) or link or ''
                    
                    published = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            published = datetime(*entry.published_parsed[:6])
                        except (TypeError, ValueError) as e:
                            logger.debug(f"Date parsing error for {feed_url}: {e}")
                            # Try alternative date fields
                            for date_field in ['updated_parsed', 'created_parsed']:
                                if hasattr(entry, date_field) and getattr(entry, date_field):
                                    try:
                                        published = datetime(*getattr(entry, date_field)[:6])
                                        break
                                    except (TypeError, ValueError):
                                        continue
                    
                    entry_data = {
                        'feed_id': feed_id,
                        'title': self.safe_truncate(title),
                        'link': self.safe_truncate(link),
                        'published': published,
                        'author': self.safe_truncate(author),
                        'entry_id': self.safe_truncate(entry_id),
                        'summary': self.safe_truncate(summary)
                    }
                    
                    entries.append(entry_data)
                    
                except Exception as e:
                    logger.error(f"Entry processing error in {feed_url}: {type(e).__name__}")
                    logger.debug(f"Detailed error: {str(e)}")
                    continue
            
            if not entries:
                logger.warning(f"No valid entries processed from {feed_url}")
                return pd.DataFrame()
            
            df = pd.DataFrame(entries)
            logger.info(f"Successfully processed {len(df)} entries from feed {feed_id}: {feed_url}")
            return df
            
        except Exception as e:
            logger.error(f"Feed processing error for {feed_url}: {type(e).__name__}")
            logger.debug(f"Detailed error: {str(e)}")
            return pd.DataFrame()

    def save_entries(self, entries_df: pd.DataFrame) -> None:
        """Save entries to database using pandas"""
        if entries_df.empty:
            logger.warning("No entries to save")
            return

        try:
            # Remove duplicates before saving, keeping the latest version
            entries_df = entries_df.drop_duplicates(subset=['link'], keep='last')
            
            # Get existing links
            existing_links = pd.read_sql(
                text("SELECT link FROM entries"),
                self.engine
            )['link'].tolist()
            
            # Filter out entries that already exist
            new_entries = entries_df[~entries_df['link'].isin(existing_links)]
            
            if new_entries.empty:
                logger.info("No new entries to save")
                return
            
            # Save only new entries to database in chunks
            new_entries.to_sql(
                'entries',
                self.engine,
                if_exists='append',
                index=False,
                method='multi',
                chunksize=self.chunk_size
            )
            logger.info(f"Saved {len(new_entries)} new entries to database")
            
            # Log how many duplicates were skipped
            skipped = len(entries_df) - len(new_entries)
            if skipped > 0:
                logger.info(f"Skipped {skipped} existing entries")
            
        except Exception as e:
            logger.error(f"Database error: {type(e).__name__}")
            logger.debug(f"Detailed error: {str(e)}")
            raise

def main():
    logger.info("=== Starting RSS Feed Processor ===")
    
    try:
        processor = FeedProcessor()
        feeds_df = processor.get_feeds()
        
        if feeds_df.empty:
            logger.warning("No feeds found in database")
            return
        
        all_entries = []
        total_size = 0
        
        # Process feeds and save in chunks
        for _, row in feeds_df.iterrows():
            entries_df = processor.process_feed(row['id'], row['feed_url'])
            if not entries_df.empty:
                all_entries.append(entries_df)
                total_size += len(entries_df)
                
                # Save in chunks to manage memory
                if total_size >= processor.chunk_size:
                    combined_chunk = pd.concat(all_entries, ignore_index=True)
                    processor.save_entries(combined_chunk)
                    all_entries = []
                    total_size = 0
        
        # Save any remaining entries
        if all_entries:
            combined_entries = pd.concat(all_entries, ignore_index=True)
            processor.save_entries(combined_entries)
            
            # Print summary
            logger.info("\n=== Processing Summary ===")
            logger.info(f"Total feeds processed: {len(feeds_df)}")
            logger.info(f"Total entries saved: {len(combined_entries)}")
            logger.info(f"Entries per feed: {len(combined_entries)/len(feeds_df):.1f}")
            logger.info("========================")
        else:
            logger.warning("No entries collected from any feed")
        
    except Exception as e:
        logger.error(f"Process error: {type(e).__name__}")
        logger.debug(f"Detailed error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 