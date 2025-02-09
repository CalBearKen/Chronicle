from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import mysql.connector
from typing import Dict, List
import json
from dotenv import load_dotenv
import os
from openai import OpenAI
from textwrap import dedent
import time

class NewsDigest:
    def __init__(self, db_config: Dict, openai_api_key: str = None):
        """Initialize the news digest generator."""
        self.db_config = db_config
        # Initialize OpenAI client
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self.client = OpenAI(api_key=api_key)

    def fetch_date_range(self) -> tuple:
        """Fetch the earliest and latest dates in the database."""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    DATE(MIN(published)) as earliest_date,
                    DATE(MAX(published)) as latest_date
                FROM entries
                WHERE published IS NOT NULL
            """
            
            cursor.execute(query)
            earliest_date, latest_date = cursor.fetchone()
            return earliest_date, latest_date
            
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals() and conn.is_connected():
                conn.close()

    def fetch_entries_for_date(self, date: datetime.date) -> List[Dict]:
        """Fetch entries for a specific date."""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    e.title,
                    e.summary,
                    e.published,
                    e.link,
                    f.title as publication
                FROM entries e
                JOIN feeds f ON e.feed_id = f.id
                WHERE DATE(e.published) = %s
                ORDER BY e.published DESC
            """
            
            cursor.execute(query, (date,))
            entries = cursor.fetchall()
            print(f"Fetched {len(entries)} entries for {date}")
            return entries
            
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals() and conn.is_connected():
                conn.close()

    def format_entries_for_llm(self, entries: List[Dict]) -> str:
        """Format entries into a digestible format for the LLM."""
        formatted_entries = []
        
        for entry in entries:
            formatted_entry = dedent(f"""
                Title: {entry['title']}
                Publication: {entry['publication']}
                Date: {entry['published'].strftime('%Y-%m-%d %H:%M:%S') if entry['published'] else 'Unknown'}
                Summary: {entry['summary'][:500] if entry['summary'] else 'No summary available'}
                Link: {entry['link']}
                ---
            """)
            formatted_entries.append(formatted_entry)
        
        return "\n".join(formatted_entries)

    def generate_summary(self, content: str, style: str = "concise") -> str:
        """Generate a summary using OpenAI's ChatGPT."""
        style_prompts = {
            "concise": """
                Analyze the provided articles and create a concise summary of today's most important news.
                Focus on:
                1. Breaking news and recent developments
                2. Events with immediate impact
                3. Emerging trends and patterns
                4. Local/global significance
                
                Structure as:
                - Lead with the most urgent story
                - Follow with supporting context
                - Highlight key quotes/statistics
                - Mention source publications
                - Keep under 300 words
            """,
            "detailed": """
                Create a comprehensive analysis of today's news landscape. Prioritize:
                1. Time-sensitive developments
                2. Political/economic implications
                3. Public safety concerns
                4. Cultural/social shifts
                
                Structure as:
                1. Executive Summary (3-4 key points)
                2. In-Depth Analysis (per major story)
                3. Expert Perspectives
                4. What to Watch Next
                5. Source Attribution
            """
        }
        
        prompt = dedent(f"""
            You are a breaking news editor working on today's coverage. 
            Focus on current events that are developing right now or have immediate consequences.
            
            {style_prompts.get(style, style_prompts["concise"])}
            
            Guidelines:
            - Prioritize recency and urgency
            - Explain why each story matters now
            - Note conflicting reports/uncertainties
            - Use active voice and present tense
            - Avoid historical context unless critical
            
            Articles to analyze:
            {content}
        """)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a senior news editor with decades of experience in determining news value and crafting compelling summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return f"Error generating summary: {str(e)}"

    def save_to_db(self, summary: str, entries: List[Dict], date: datetime.date):
        """Save the summary to the database."""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Prepare the data
            publications = list(set(e['publication'] for e in entries))
            articles = [{
                'title': e['title'],
                'publication': e['publication'],
                'link': e['link'],
                'published': e['published'].isoformat() if e['published'] else None
            } for e in entries]
            
            # Convert lists to JSON strings
            publications_json = json.dumps(publications)
            articles_json = json.dumps(articles)
            
            # Insert or update the summary
            query = """
                INSERT INTO daily_summaries 
                    (summary_date, summary_text, article_count, publications, articles)
                VALUES 
                    (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    summary_text = VALUES(summary_text),
                    article_count = VALUES(article_count),
                    publications = VALUES(publications),
                    articles = VALUES(articles),
                    generated_at = CURRENT_TIMESTAMP
            """
            
            values = (
                date,
                summary,
                len(entries),
                publications_json,
                articles_json
            )
            
            cursor.execute(query, values)
            conn.commit()
            print(f"Saved summary for {date} to database")
            
        except Exception as e:
            print(f"Error saving to database: {e}")
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals() and conn.is_connected():
                conn.close()

    def process_all_days(self, max_days: int = None):
        """Process and summarize news for all days in the database."""
        earliest_date, latest_date = self.fetch_date_range()
        if not earliest_date or not latest_date:
            print("Could not determine date range")
            return
        
        print(f"Available date range: {earliest_date} to {latest_date}")
        
        if max_days:
            earliest_possible = latest_date - timedelta(days=max_days-1)
            earliest_date = max(earliest_date, earliest_possible)
            print(f"Processing last {max_days} days: {earliest_date} to {latest_date}")
        
        current_date = latest_date
        days_processed = 0
        
        while current_date >= earliest_date:
            days_processed += 1
            print(f"\nProcessing {current_date} ({days_processed} days processed)...")
            
            entries = self.fetch_entries_for_date(current_date)
            
            if entries:
                formatted_content = self.format_entries_for_llm(entries)
                print(f"Generating summary for {current_date} ({len(entries)} articles)...")
                summary = self.generate_summary(formatted_content, style="detailed")
                
                # Save to database
                self.save_to_db(summary, entries, current_date)
                print(f"Completed {current_date}")
            else:
                print(f"No entries found for {current_date}")
            
            current_date -= timedelta(days=1)
            time.sleep(1)  # Rate limiting
        
        print(f"\nProcessed {days_processed} days total")

def main():
    # Load environment variables
    load_dotenv()
    
    # Database configuration
    db_config = {
        'host': 'localhost',
        'user': 'rss_user',
        'password': 'rss_password',
        'database': 'rss_feed'
    }
    
    # Initialize news digest
    digest = NewsDigest(db_config)
    
    # Process all days, starting from most recent
    max_days = None  # Set to a number to limit days processed
    digest.process_all_days(max_days=max_days)

if __name__ == "__main__":
    main() 