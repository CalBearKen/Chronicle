import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import re
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

class SubstackScraper:
    def __init__(self):
        self.base_url = "https://substack.com"
        self.top_news_url = "https://substack.com/top/news"  # Use absolute URL
        
        # Setup Chrome options
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

    def get_feed_url(self, publication_url: str) -> str:
        """Convert a Substack publication URL to its RSS feed URL."""
        # Remove trailing slash if present
        publication_url = publication_url.rstrip('/')
        
        # Extract the subdomain/path
        match = re.search(r'https?://(?:www\.)?([^/]+)', publication_url)
        if not match:
            return None
            
        subdomain = match.group(1)
        if 'substack.com' in subdomain:
            # Extract publication name from subdomain
            pub_name = subdomain.split('.')[0]
            return f"https://{pub_name}.substack.com/feed"
        else:
            # For custom domains
            return f"{publication_url}/feed"

    def scrape_top_news(self) -> List[Dict]:
        """Scrape the top news publications from Substack."""
        try:
            print(f"Fetching {self.top_news_url}...")
            self.driver.get(self.top_news_url)
            
            # Wait for content to load
            time.sleep(5)  # Give JavaScript time to execute
            
            # Save rendered HTML for debugging
            with open('debug_rendered.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print("\nSaved rendered HTML to debug_rendered.html")
            
            publications = []
            
            # Looking for numbered publications (1. Public, 2. Whitepaper.mx, etc.)
            try:
                print("\nLooking for numbered publications...")
                for i in range(1, 26):  # Top 25 publications
                    try:
                        # Find the publication section
                        publication_xpath = f"//*[contains(text(), '{i}. ')]"
                        pub_elem = self.driver.find_element(By.XPATH, publication_xpath)
                        
                        if pub_elem:
                            print(f"\nProcessing publication #{i}")
                            
                            # Get the parent element that contains all publication info
                            parent = pub_elem.find_element(By.XPATH, "./..")
                            
                            # Extract title (remove the number prefix)
                            title_text = pub_elem.text
                            title = title_text.split('. ', 1)[1] if '. ' in title_text else title_text
                            print(f"Found title: {title}")
                            
                            # Find the Subscribe link which contains the publication URL
                            try:
                                link_elem = parent.find_element(By.LINK_TEXT, "Subscribe")
                                link = link_elem.get_attribute('href')
                                print(f"Found link: {link}")
                            except:
                                # Try finding any link in the section
                                link_elems = parent.find_elements(By.TAG_NAME, "a")
                                link = link_elems[0].get_attribute('href') if link_elems else None
                                print(f"Found alternate link: {link}")
                            
                            if not link:
                                print("No link found, skipping...")
                                continue
                            
                            # Try to get description from the next paragraph
                            description = ""
                            try:
                                desc_elem = parent.find_element(By.TAG_NAME, "p")
                                description = desc_elem.text.strip()
                                print(f"Found description: {description}")
                            except:
                                pass
                            
                            # Generate RSS feed URL
                            feed_url = self.get_feed_url(link)
                            print(f"Generated feed URL: {feed_url}")
                            
                            publications.append({
                                'title': title,
                                'link': link,
                                'feed_url': feed_url,
                                'description': description
                            })
                            print("Successfully added publication")
                            
                    except Exception as e:
                        print(f"Error processing publication #{i}: {e}")
                        continue
                
            except Exception as e:
                print(f"Error finding publications: {e}")
            
            return publications
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            return []
        finally:
            self.driver.quit()

    def save_to_csv(self, publications: List[Dict], filename: str = None):
        """Save the scraped publications to a CSV file."""
        if filename is None:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'substack_feeds_{timestamp}.csv'
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['title', 'link', 'feed_url', 'description'])
                writer.writeheader()
                writer.writerows(publications)
            print(f"Saved {len(publications)} publications to {filename}")
        except Exception as e:
            print(f"Error saving to CSV: {e}")

def main():
    scraper = SubstackScraper()
    publications = scraper.scrape_top_news()
    
    # Print results
    print(f"\nFound {len(publications)} publications:")
    for pub in publications:
        print(f"\nTitle: {pub['title']}")
        print(f"Link: {pub['link']}")
        print(f"Feed URL: {pub['feed_url']}")
        print("-" * 50)
    
    # Save to CSV instead of JSON
    scraper.save_to_csv(publications)

if __name__ == "__main__":
    main() 