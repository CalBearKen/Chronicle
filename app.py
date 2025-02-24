from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import mysql.connector
from typing import Dict, List
import json
from dotenv import load_dotenv
import os
from chatbot import NewsBot

app = Flask(__name__)

# Database configuration
db_config = {
    'host': 'db',
    'user': 'rss_user',
    'password': 'rss_password',
    'database': 'rss_feed'
}

# Initialize chatbot
news_bot = NewsBot()

def get_date_range() -> tuple:
    """Get the earliest and latest dates from entries table."""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                MIN(DATE(published)) as earliest_date,
                MAX(DATE(published)) as latest_date
            FROM entries
        """
        
        cursor.execute(query)
        earliest_date, latest_date = cursor.fetchone()
        
        # If no data exists, use default date range
        if earliest_date is None or latest_date is None:
            today = datetime.now().date()
            earliest_date = today - timedelta(days=30)  # Default to last 30 days
            latest_date = today
            
        return earliest_date, latest_date
        
    except Exception as e:
        print(f"Error getting date range: {e}")
        # Return default date range on error
        today = datetime.now().date()
        return today - timedelta(days=30), today
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def get_summary(date: datetime.date) -> Dict:
    """Get summary for a specific date."""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT *
            FROM daily_summaries
            WHERE summary_date = %s
        """
        
        cursor.execute(query, (date,))
        result = cursor.fetchone()
        
        if result:
            result['publications'] = json.loads(result['publications'])
            result['articles'] = json.loads(result['articles'])
            
        return result
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

@app.route('/')
def index():
    try:
        earliest_date, latest_date = get_date_range()
        return render_template('index.html', 
                             earliest_date=earliest_date.isoformat(),
                             latest_date=latest_date.isoformat())
    except Exception as e:
        print(f"Error in index route: {e}")
        # Provide default dates if something goes wrong
        today = datetime.now().date()
        return render_template('index.html',
                             earliest_date=(today - timedelta(days=30)).isoformat(),
                             latest_date=today.isoformat())

@app.route('/api/summary/<date>')
def get_summary_api(date):
    summary = get_summary(datetime.strptime(date, '%Y-%m-%d').date())
    return jsonify(summary if summary else {})

@app.route('/api/nearest-date/<date>')
def get_nearest_date(date):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        query = """
            SELECT summary_date 
            FROM daily_summaries 
            WHERE summary_date <= %s 
            AND article_count > 0 
            ORDER BY summary_date DESC 
            LIMIT 1
        """
        
        cursor.execute(query, (date,))
        result = cursor.fetchone()
        return jsonify({'nearest_date': result[0].isoformat() if result else None})
        
    except Exception as e:
        print(f"Error finding nearest date: {e}")
        return jsonify({'nearest_date': None})
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

@app.route('/api/articles/<date>')
def get_articles(date):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                e.id,
                e.title,
                e.author as publication,
                e.link,
                e.published,
                e.summary,
                e.author
            FROM entries e
            WHERE DATE(e.published) = %s
            ORDER BY e.published DESC
        """
        
        cursor.execute(query, (date,))
        articles = cursor.fetchall()
        
        return jsonify(articles)
        
    except Exception as e:
        print(f"Error fetching articles: {e}")
        return jsonify([])
        
    finally:
        cursor.close()
        conn.close()

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
        
    try:
        response = news_bot.chat(query)
        if not response:
            return jsonify({'error': 'No response generated'}), 500
        
        return jsonify({'response': response})
    except Exception as e:
        print(f"Chat error: {str(e)}")  # Log the error
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=True) 