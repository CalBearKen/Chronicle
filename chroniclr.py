from datetime import datetime, timedelta
import mysql.connector
from typing import List, Dict
from openai import OpenAI
from textwrap import dedent
import os
from dotenv import load_dotenv
import httpx

class ChronicleGenerator:
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            # Use updated httpx configuration
            http_client=httpx.Client(
                transport=httpx.HTTPTransport(retries=3)
            )
        )
        self.book = []
        
    def fetch_dates(self) -> List[datetime.date]:
        """Get dates from the last 2 days"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT DATE(published) 
                FROM entries 
                WHERE published >= DATE_SUB(CURDATE(), INTERVAL 2 DAY)
                ORDER BY DATE(published) DESC
            """)
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

    def get_daily_chaos(self, date: datetime.date) -> str:
        """Get formatted entries for a date"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT e.title, e.summary, f.title as publication
                FROM entries e
                JOIN feeds f ON e.feed_id = f.id
                WHERE DATE(e.published) = %s
            """, (date,))
            return "\n".join(
                f"{row['publication']} reports: {row['title']} - {row['summary'][:200]}"
                for row in cursor.fetchall()
            )
        finally:
            cursor.close()
            conn.close()

    def generate_page(self, date: datetime.date, content: str) -> str:
        """Generate a Mark Twain-style satirical commentary"""
        prompt = dedent(f"""
            You're a 19th century humorist observing modern absurdities. Create commentary that:
            1. Begins with a homespun proverb with ironic twist
            2. Uses folksy analogies to expose modern folly
            3. Employs deadpan delivery of outrageous facts
            4. Concludes with wry, paradoxical wisdom
            
            Structure:
            📜 Title: [Humorous faux-proverb]
            
            🧐 Observation: 
            "It has been reported that..." [Folksy setup of most absurd news item]
            
            🤠 Tall Tales: 
            - [News item 1] → "Reminds me of the time..." [Rural analogy]
            - [News item 2] → "Much like that fella who..." [Frontier comparison]
            
            🧙♂️ Moral: 
            [Seemingly wise advice that's actually absurd]
            
            Material for contemplation:
            {content}
        """)
        
        full_response = []
        print(f"Generating page for {date}:")
        
        stream = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You're Mark Twain reincarnated as a modern columnist. Blend folksy wisdom, ironic understatement, and deadpan delivery."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500,
            stream=True
        )
        
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                print(delta, end='', flush=True)
                full_response.append(delta)
        
        print(f"\n\nTokens used: {chunk.usage.total_tokens if chunk.usage else 'Unknown'}\n")
        return ''.join(full_response)

    def compile_book(self):
        """Generate the complete dark chronicle"""
        dates = self.fetch_dates()
        if not dates:
            print("No recent news found in the last 48 hours")
            return
        
        self.book.append(f"# 48-Hour Disaster Report\n*{min(dates)} to {max(dates)}*\n")
        
        for date in dates:
            content = self.get_daily_chaos(date)
            if not content:
                continue
                
            page = self.generate_page(date, content)
            self.book.append(f"\n\n## {date}\n{'='*30}\n{page}\n{'▄'*50}")
        
        with open("humanity_fuck_yeah.md", "w", encoding="utf-8") as f:
            f.write("\n".join(self.book))

def main():
    load_dotenv()
    db_config = {
        'host': 'localhost',
        'user': 'rss_user',
        'password': 'rss_password',
        'database': 'rss_feed'
    }
    
    chronicler = ChronicleGenerator(db_config)
    chronicler.compile_book()
    print("Dark chronicle complete. Enjoy the existential dread!")

if __name__ == "__main__":
    main() 