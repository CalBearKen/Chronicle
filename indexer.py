from typing import List, Dict
import mysql.connector
from datetime import datetime
import json
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

class NewsIndexer:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'db'),
            'user': os.getenv('DB_USER', 'rss_user'),
            'password': os.getenv('DB_PASSWORD', 'rss_password'),
            'database': os.getenv('DB_NAME', 'rss_feed')
        }
        
        # Initialize Qdrant client
        self.qdrant = QdrantClient("qdrant", port=6333)
        
        # Initialize sentence transformer
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Create collection if it doesn't exist
        self.qdrant.recreate_collection(
            collection_name="news_articles",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

    def fetch_articles(self) -> List[Dict]:
        """Fetch articles from MySQL"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    e.id,
                    e.title,
                    e.author as publication,
                    e.link,
                    e.published,
                    e.summary
                FROM entries e
                ORDER BY e.published DESC
            """
            
            cursor.execute(query)
            articles = cursor.fetchall()
            
            # Convert datetime objects to strings
            for article in articles:
                if article['published']:
                    article['published'] = article['published'].isoformat()
            
            return articles
            
        finally:
            cursor.close()
            conn.close()

    def index_articles(self):
        """Index articles in Qdrant"""
        articles = self.fetch_articles()
        print(f"Fetched {len(articles)} articles")
        
        for article in articles:
            # Create text for embedding
            text = f"{article['title']} {article['summary'] or ''}"
            
            # Generate embedding
            embedding = self.encoder.encode(text).tolist()
            
            # Store in Qdrant
            self.qdrant.upsert(
                collection_name="news_articles",
                points=[{
                    "id": article['id'],
                    "vector": embedding,
                    "payload": article
                }]
            )
            
        print("Indexing complete!")

if __name__ == "__main__":
    indexer = NewsIndexer()
    indexer.index_articles() 