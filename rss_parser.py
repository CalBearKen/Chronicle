import feedparser
from datetime import datetime
from typing import Dict, List
import mysql.connector
from mysql.connector import Error

class SubstackRSSParser:
    def __init__(self, url: str, db_config: Dict):
        """
        Initialize the parser with RSS feed URL and database configuration.
        
        Args:
            url: RSS feed URL
            db_config: Dictionary containing MySQL connection parameters
        """
        self.url = url
        self.feed = None
        self.db_config = db_config
        self.connection = None

    def connect_to_db(self):
        """Establish database connection."""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            raise

    def close_db(self):
        """Close database connection."""
        if self.connection and self.connection.is_connected():
            self.connection.close()

    def save_to_db(self, feed_data: Dict):
        """Save parsed feed data to MySQL database."""
        if not self.connection or not self.connection.is_connected():
            self.connect_to_db()

        cursor = self.connection.cursor()
        
        try:
            # Insert feed data
            feed_query = """
                INSERT INTO feeds (title, link, feed_url, description, author)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                link = VALUES(link),
                description = VALUES(description),
                author = VALUES(author)
            """
            feed_values = (
                feed_data['title'],
                feed_data['link'],
                self.url,  # Add the feed_url
                feed_data['description'],
                feed_data['author']
            )
            cursor.execute(feed_query, feed_values)
            
            # Get feed_id either from insert or existing record
            if cursor.lastrowid:
                feed_id = cursor.lastrowid
            else:
                cursor.execute("SELECT id FROM feeds WHERE feed_url = %s", (self.url,))
                feed_id = cursor.fetchone()[0]
            
            # Insert entries
            entry_query = """
                INSERT INTO entries (feed_id, title, link, published, author, entry_id, summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                published = VALUES(published),
                author = VALUES(author),
                summary = VALUES(summary)
            """
            
            for entry in feed_data['entries']:
                entry_values = (
                    feed_id,
                    entry['title'],
                    entry['link'],
                    entry['published'],
                    entry['author'],
                    entry['id'],
                    entry['summary']
                )
                cursor.execute(entry_query, entry_values)
            
            self.connection.commit()
            
        except Error as e:
            print(f"Error saving to database: {e}")
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def parse(self) -> Dict:
        """Parse the RSS feed and return structured data."""
        self.feed = feedparser.parse(self.url)
        
        # Extract feed metadata
        feed_info = {
            'title': self._clean_cdata(self.feed.feed.get('title', '')),
            'link': self.feed.feed.get('link', ''),
            'description': self._clean_cdata(self.feed.feed.get('description', '')),
            'author': self.feed.feed.get('author', ''),
            'entries': self._parse_entries()
        }
        
        return feed_info

    def _parse_entries(self) -> List[Dict]:
        """Parse individual feed entries."""
        entries = []
        
        for entry in self.feed.entries:
            parsed_entry = {
                'title': self._clean_cdata(entry.get('title', '')),
                'link': entry.get('link', ''),
                'published': self._parse_date(entry.get('published', '')),
                'author': entry.get('author', ''),
                'id': entry.get('id', ''),
                'summary': self._clean_cdata(entry.get('summary', '')),
            }
            entries.append(parsed_entry)
            
        return entries

    def _clean_cdata(self, text: str) -> str:
        """Remove CDATA markers and clean text."""
        text = text.replace('<![CDATA[', '').replace(']]>', '')
        return text.strip()

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        try:
            return datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        except ValueError:
            return None

def main():
    # Database configuration
    db_config = {
        'host': 'localhost',
        'user': 'rss_user',
        'password': 'rss_password',
        'database': 'rss_feed'
    }

    # Example usage
    url = "https://api.substack.com/feed/podcast/1810164.rss"
    parser = SubstackRSSParser(url, db_config)
    
    try:
        feed_data = parser.parse()
        parser.save_to_db(feed_data)
        
        # Print feed information
        print(f"Feed Title: {feed_data['title']}")
        print(f"Feed Link: {feed_data['link']}")
        print(f"Feed Author: {feed_data['author']}")
        print("\nRecent entries:")
        
        # Print recent entries
        for entry in feed_data['entries'][:5]:
            print(f"\nTitle: {entry['title']}")
            print(f"Published: {entry['published']}")
            print(f"Link: {entry['link']}")
            print("-" * 50)
            
    finally:
        parser.close_db()

if __name__ == "__main__":
    main() 